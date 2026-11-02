"""CLI do pipeline: `malpipe --help`."""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from malpipe.config import get_settings
from malpipe.sources import jikan, kaggle, mal_api, manami
from malpipe.warehouse import JIKAN_ENTITIES, Warehouse

app = typer.Typer(help="Pipeline de dados do MyAnimeList → DuckDB (bronze).", no_args_is_help=True)
console = Console()


@app.callback()
def _setup(verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(message)s",
        handlers=[RichHandler(console=console, show_path=False, rich_tracebacks=True)],
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)


def _wh() -> Warehouse:
    return Warehouse(get_settings().duckdb_path)


def _parse_years(spec: str) -> range:
    if "-" in spec:
        start, end = spec.split("-", 1)
        return range(int(start), int(end) + 1)
    return range(int(spec), int(spec) + 1)


@app.command()
def init() -> None:
    """Cria o arquivo DuckDB e os schemas bronze/meta."""
    wh = _wh()
    console.print(f"[green]ok[/] warehouse em {wh.path}")
    wh.close()


@app.command()
def discover(
    ranking: Annotated[bool, typer.Option(help="Descobrir IDs pelo ranking geral.")] = True,
    seasons: Annotated[str | None, typer.Option(help="Faixa de anos, ex.: 1990-2026.")] = None,
    max_pages: Annotated[int | None, typer.Option(help="Limite de páginas do ranking (500 IDs cada).")] = None,
) -> None:
    """Descobre IDs de anime via MAL API (ranking e/ou temporadas)."""
    settings = get_settings()
    wh = _wh()
    with wh.run("discover") as run, mal_api.build_client(settings) as client:
        if ranking:
            mal_api.discover_ranking(client, wh, run, max_pages=max_pages)
        if seasons:
            mal_api.discover_seasons(client, wh, run, _parse_years(seasons))
        console.print(f"[green]{run.rows_written}[/] IDs descobertos")
    wh.close()


@app.command("mal-details")
def mal_details(
    limit: Annotated[int | None, typer.Option(help="Máximo de IDs nesta execução.")] = None,
    retry_not_found: Annotated[bool, typer.Option(help="Tentar de novo IDs que deram 404.")] = False,
) -> None:
    """Extrai o detalhe completo dos IDs pendentes (novos ou mais velhos que REFRESH_DAYS)."""
    settings = get_settings()
    wh = _wh()
    ids = wh.pending_ids("bronze.mal_anime", settings.refresh_days, wh.known_mal_ids_sql(), retry_not_found, limit)
    console.print(f"{len(ids)} IDs pendentes (~{len(ids) / settings.mal_rps / 3600:.1f} h a {settings.mal_rps} req/s)")
    if ids:
        with wh.run("mal-details") as run, mal_api.build_client(settings) as client:
            stats = mal_api.fetch_details(client, wh, run, ids)
            run.notes = f"status: {stats}"
    wh.close()


@app.command("jikan")
def jikan_cmd(
    entity: Annotated[str, typer.Argument(help=f"{' | '.join(JIKAN_ENTITIES)} | all")] = "all",
    limit: Annotated[int | None, typer.Option()] = None,
) -> None:
    """Enriquece via Jikan os animes que já têm detalhe do MAL."""
    settings = get_settings()
    wh = _wh()
    entities = JIKAN_ENTITIES if entity == "all" else (entity,)
    with jikan.build_client(settings) as client:
        for ent in entities:
            ids = wh.pending_ids(
                f"bronze.jikan_{ent}", settings.refresh_days * 4, wh.fetched_mal_ids_sql(), limit=limit
            )
            console.print(f"jikan {ent}: {len(ids)} pendentes")
            if ids:
                with wh.run(f"jikan-{ent}") as run:
                    run.notes = f"status: {jikan.fetch_entity(client, wh, run, ent, ids)}"
    wh.close()


@app.command("manami")
def manami_cmd(
    file: Annotated[Path | None, typer.Option(help="Arquivo já baixado (.json ou .json.zst).")] = None,
) -> None:
    """Baixa e carrega o anime-offline-database (idempotente por snapshot semanal)."""
    settings = get_settings()
    wh = _wh()
    with wh.run("manami") as run:
        path = file or manami.download(
            settings.manami_url, settings.data_dir / "raw" / f"manami-{date.today():%Y%m%d}.json.zst"
        )
        manami.load(wh, run, path)
        console.print(run.notes)
    wh.close()


@app.command("kaggle")
def kaggle_cmd(
    csv: Annotated[Path, typer.Argument(help="Caminho do animelist.csv")],
    sample_users: Annotated[int | None, typer.Option(help="Carregar só N usuários (dev local).")] = None,
) -> None:
    """Carrega as interações usuário × anime do Kaggle (hernan4444)."""
    wh = _wh()
    with wh.run("kaggle") as run:
        n = kaggle.load_animelist(wh, run, csv, sample_users)
        console.print(f"[green]{n:,}[/] linhas carregadas")
    wh.close()


@app.command("my-list")
def my_list(username: Annotated[str | None, typer.Option(help="Default: MAL_USERNAME do .env")] = None) -> None:
    """Extrai a sua lista pública do MAL (para o painel 'Meu perfil vs MAL')."""
    settings = get_settings()
    username = username or settings.mal_username
    if not username:
        from malpipe.config import ENV_FILE

        hint = "" if ENV_FILE.exists() else f" (arquivo não encontrado: {ENV_FILE})"
        raise typer.BadParameter(f"informe --username ou MAL_USERNAME no .env{hint}")
    wh = _wh()
    with wh.run("my-list") as run, mal_api.build_client(settings) as client:
        n = mal_api.fetch_user_list(client, wh, run, username)
        console.print(f"[green]{n}[/] itens na lista de {username}")
    wh.close()


@app.command()
def incremental(
    seasons: Annotated[str, typer.Option(help="Temporadas recentes a varrer.")] = f"{date.today().year - 1}-"
    f"{date.today().year + 1}",
    detail_limit: Annotated[int | None, typer.Option()] = None,
) -> None:
    """Rotina semanal: manami → temporadas recentes → detalhes pendentes → Jikan → minha lista."""
    settings = get_settings()
    manami_cmd(None)
    wh = _wh()
    with wh.run("discover-incremental") as run, mal_api.build_client(settings) as client:
        mal_api.discover_seasons(client, wh, run, _parse_years(seasons))
    wh.close()
    mal_details(limit=detail_limit, retry_not_found=False)
    jikan_cmd("all", limit=detail_limit)
    if settings.mal_username:
        my_list(None)


@app.command()
def sample(
    n_anime: Annotated[int, typer.Option()] = 400,
    n_users: Annotated[int, typer.Option()] = 1500,
    seed: Annotated[int, typer.Option()] = 42,
    reset: Annotated[bool, typer.Option(help="Apaga o bronze antes de gerar.")] = True,
) -> None:
    """Gera dados SINTÉTICOS no formato das APIs (demo/CI, sem credenciais)."""
    from malpipe.sample_data import generate

    wh = _wh()
    if reset:
        for table, _ in wh.table_counts():
            if table.startswith("bronze."):
                wh.con.execute(f"DELETE FROM {table}")
    with wh.run("sample") as run:
        counts = generate(wh, run, n_anime=n_anime, n_users=n_users, seed=seed)
    table = Table("tabela bronze", "linhas", title="Dados sintéticos gerados")
    for k, v in counts.items():
        table.add_row(k, f"{v:,}")
    console.print(table)
    wh.close()


@app.command()
def recommend(
    username: Annotated[str | None, typer.Option(help="Usuário cuja lista recebe recomendações.")] = None,
    k: Annotated[int, typer.Option(help="Top-K para avaliação e recomendação.")] = 10,
    max_users: Annotated[
        int | None, typer.Option(help="Amostra de usuários para treinar mais rápido (base completa: ~300 mil).")
    ] = None,
) -> None:
    """Treina e avalia os recomendadores e grava resultados no schema `ml` do DuckDB."""
    from malpipe.recsys.pipeline import run as run_recsys

    settings = get_settings()
    run_recsys(
        settings.duckdb_path,
        username=username or settings.mal_username,
        k=k,
        max_users=max_users,
        console=console,
    )


@app.command(
    "dbt",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def dbt_cmd(ctx: typer.Context) -> None:
    """Roda o dbt (ex.: `malpipe dbt build`) apontando para o MESMO banco do .env."""
    import os
    import subprocess

    from malpipe.config import PROJECT_ROOT

    settings = get_settings()
    env = os.environ | {"DUCKDB_PATH": str(settings.duckdb_path), "DBT_PROFILES_DIR": str(PROJECT_ROOT / "dbt")}
    console.print(f"dbt → {settings.duckdb_path}")
    code = subprocess.call(["dbt", *(ctx.args or ["build"])], cwd=PROJECT_ROOT / "dbt", env=env)
    raise typer.Exit(code)


DEFAULT_EXPORTS = (
    "analytics.mart_studio_performance",
    "analytics.mart_score_inflation",
    "analytics.mart_hidden_gems",
    "analytics.mart_franchise_summary",
    "analytics.mart_polarizing_anime",
    "analytics.mart_season_trends",
    "analytics.mart_my_profile_vs_mal",
    "core.fct_my_list",
    "ml.recommendations_for_user",
)


@app.command()
def export(
    tables: Annotated[list[str] | None, typer.Argument(help="schema.tabela; padrão: principais marts.")] = None,
    out: Annotated[Path, typer.Option(help="Pasta de destino dos CSVs.")] = Path("exports"),
) -> None:
    """Exporta tabelas do warehouse para CSV (para Excel, Power BI ou compartilhar)."""
    import duckdb

    settings = get_settings()
    out.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(settings.duckdb_path), read_only=True)
    for table in tables or DEFAULT_EXPORTS:
        target = out / f"{table.replace('.', '__')}.csv"
        try:
            con.execute(f"COPY (SELECT * FROM {table}) TO '{target.as_posix()}' (HEADER, DELIMITER ',')")
            n = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            console.print(f"[green]ok[/] {table} → {target} ({n:,} linhas)")
        except duckdb.Error as exc:
            console.print(f"[yellow]pulado[/] {table}: {exc.__class__.__name__}")
    con.close()


@app.command()
def status() -> None:
    """Contagem por tabela, últimas execuções e fila pendente."""
    settings = get_settings()
    wh = _wh()
    t = Table("tabela", "linhas", title=f"Warehouse: {wh.path}")
    for name, n in wh.table_counts():
        t.add_row(name, f"{n:,}")
    console.print(t)

    runs = wh.con.execute(
        "SELECT command, started_at, status, rows_written, notes FROM meta.runs ORDER BY started_at DESC LIMIT 8"
    ).fetchall()
    r = Table("comando", "início", "status", "linhas", "notas", title="Últimas execuções")
    for cmd, started, st, rows, notes in runs:
        r.add_row(cmd, f"{started:%Y-%m-%d %H:%M}", st, f"{rows:,}", (notes or "")[:60])
    console.print(r)

    pending = len(wh.pending_ids("bronze.mal_anime", settings.refresh_days, wh.known_mal_ids_sql()))
    ok = wh.con.execute("SELECT count(DISTINCT mal_id) FROM bronze.mal_anime WHERE http_status = 200").fetchone()[0]
    mine = wh.con.execute(
        """SELECT count(DISTINCT l.id), count(DISTINCT a.mal_id) FROM (
               SELECT TRY_CAST(payload->>'$.node.id' AS INTEGER) AS id FROM bronze.mal_user_animelist) l
           LEFT JOIN bronze.mal_anime a ON a.mal_id = l.id AND a.http_status = 200"""
    ).fetchone()
    console.print(f"Animes com detalhe do MAL: [bold]{ok:,}[/] · pendentes: [bold]{pending:,}[/]")
    console.print(f"Sua lista: [bold]{mine[0]:,}[/] animes, [bold]{mine[1]:,}[/] já com detalhe")
    wh.close()


def main() -> None:
    """Ponto de entrada: erros esperados viram mensagem clara, sem traceback."""
    from malpipe.http import HostUnreachableError

    try:
        app()
    except HostUnreachableError as exc:
        console.print(f"[bold red]Host inacessível[/] — {exc}")
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()

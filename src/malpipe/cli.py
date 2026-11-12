"""CLI do pipeline: `malpipe --help`."""

from __future__ import annotations

import logging
import os
from datetime import date
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from malpipe.config import get_settings
from malpipe.sources import anilist, jikan, kaggle, kitsu, mal_api, manami
from malpipe.warehouse import JIKAN_ENTITIES, Warehouse

log = logging.getLogger("malpipe")

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


# ============================================================================ ecossistema
def _run_manga(settings, wh: Warehouse, limit: int | None, rediscover: bool) -> str:
    with mal_api.build_client(settings) as client:
        with wh.lock:
            has_ids = wh.con.execute("SELECT count(*) FROM bronze.mal_manga_discovery").fetchone()[0]
        if rediscover or not has_ids:
            with wh.run("manga-discover") as run:
                for ranking_type in ("all", "bypopularity"):
                    mal_api.discover_ranking(client, wh, run, ranking_type=ranking_type, kind="manga")
        ids = wh.pending_ids("bronze.mal_manga", settings.refresh_days * 4, wh.known_manga_ids_sql(), limit=limit)
        log.info("mangá: %s pendentes (~%.1f h)", len(ids), len(ids) / settings.mal_rps / 3600)
        if not ids:
            return "nada pendente"
        with wh.run("manga-details") as run:
            stats = mal_api.fetch_details(client, wh, run, ids, kind="manga")
            run.notes = f"status: {stats}"
        return f"{len(ids):,} mangás · {stats}"


def _warn_if_few_anime_details(wh: Warehouse) -> None:
    """AniList e Kitsu só enriquecem animes que já têm detalhe do MAL — avisa se a base está rala."""
    with wh.lock:
        fetched, known = wh.con.execute(
            f"SELECT (SELECT count(*) FROM ({wh.fetched_mal_ids_sql()})), "
            f"(SELECT count(*) FROM ({wh.known_mal_ids_sql()}))"
        ).fetchone()
    if known and fetched < 0.5 * known:
        log.warning(
            "só %s de %s animes conhecidos têm detalhe do MAL neste banco (%s) — AniList e Kitsu ficam "
            "limitados a eles. Rode `malpipe mal-details` antes, ou `malpipe merge <outro.duckdb>` se a "
            "carga completa estiver em outro arquivo.",
            f"{fetched:,}",
            f"{known:,}",
            wh.path,
        )


def _run_anilist_relations(settings, wh: Warehouse, limit: int | None) -> str:
    ids = wh.pending_ids("bronze.anilist_relations", settings.refresh_days * 4, wh.fetched_mal_ids_sql(), limit=limit)
    batches = -(-len(ids) // anilist.RELATIONS_BATCH)
    log.info("anilist relações: %s animes pendentes (%s lotes, ~%.0f min)", len(ids), batches,
             batches / settings.anilist_rps / 60)  # fmt: skip
    if not ids:
        return "nada pendente"
    with wh.run("anilist-relations") as run, anilist.build_client(settings) as client:
        stats = anilist.fetch_relations_all(client, wh, run, ids)
        run.notes = f"status: {stats}"
    return f"{len(ids):,} animes · {stats}"


def _run_anilist(settings, wh: Warehouse, limit: int | None) -> str:
    _warn_if_few_anime_details(wh)
    # mesmo host e mesmo limite: as relações (rápidas, em lote) vêm antes, na mesma thread
    rel = _run_anilist_relations(settings, wh, limit)
    ids = wh.pending_ids("bronze.anilist_media", settings.refresh_days * 4, wh.fetched_mal_ids_sql(), limit=limit)
    log.info("anilist: %s animes pendentes (~%.1f h)", len(ids), len(ids) / settings.anilist_rps / 3600)
    if not ids:
        return f"relações: {rel} · elenco/staff: nada pendente"
    with wh.run("anilist") as run, anilist.build_client(settings) as client:
        stats = anilist.fetch_all(client, wh, run, ids, max_pages=settings.anilist_max_pages)
        run.notes = f"status: {stats}"
    return f"relações: {rel} · elenco/staff: {len(ids):,} animes · {stats}"


def _run_kitsu(settings, wh: Warehouse, limit: int | None) -> str:
    targets = wh.kitsu_candidates()
    done = wh.done_ids("bronze.kitsu_episodes", settings.refresh_days * 4)
    todo = {m: k for m, k in sorted(targets.items()) if m not in done}
    if limit:
        todo = dict(list(todo.items())[:limit])
    log.info("kitsu: %s animes pendentes (~%.1f h)", len(todo), len(todo) * 1.5 / settings.kitsu_rps / 3600)
    if not todo:
        return "nada pendente"
    with wh.run("kitsu-episodes") as run, kitsu.build_client(settings) as client:
        stats = kitsu.fetch_all(client, wh, run, todo)
        run.notes = f"status: {stats}"
    return f"{len(todo):,} animes · {stats}"


@app.command("manga")
def manga_cmd(
    limit: Annotated[int | None, typer.Option(help="Máximo de mangás nesta execução.")] = None,
    rediscover: Annotated[bool, typer.Option(help="Varrer o ranking de novo atrás de títulos novos.")] = False,
) -> None:
    """Catálogo de mangás pela MAL API oficial (descoberta pelo ranking + detalhe de cada um)."""
    wh = _wh()
    console.print(_run_manga(get_settings(), wh, limit, rediscover))
    wh.close()


@app.command("anilist")
def anilist_cmd(limit: Annotated[int | None, typer.Option()] = None) -> None:
    """Personagens, dubladores, staff, estúdios e pessoas pela AniList (por ID do MAL)."""
    wh = _wh()
    console.print(_run_anilist(get_settings(), wh, limit))
    wh.close()


@app.command("anilist-relations")
def anilist_relations_cmd(limit: Annotated[int | None, typer.Option()] = None) -> None:
    """Só as relações dos animes na AniList (obra de origem → ligação mangá × anime), em lote (~20 min)."""
    wh = _wh()
    console.print(_run_anilist_relations(get_settings(), wh, limit))
    wh.close()


@app.command("kitsu")
def kitsu_cmd(limit: Annotated[int | None, typer.Option()] = None) -> None:
    """Episódios (título, número, data, duração) pelo Kitsu."""
    wh = _wh()
    console.print(_run_kitsu(get_settings(), wh, limit))
    wh.close()


@app.command("check-sources")
def check_sources() -> None:
    """Testa se cada fonte responde a partir da sua rede (1 requisição em cada)."""
    import time

    import httpx

    settings = get_settings()
    checks = [
        ("MAL API (anime)", "GET", f"{settings.mal_base_url}/anime/1?fields=id",
         {"X-MAL-CLIENT-ID": settings.mal_client_id or ""}, None),
        ("MAL API (mangá)", "GET", f"{settings.mal_base_url}/manga/2?fields=id",
         {"X-MAL-CLIENT-ID": settings.mal_client_id or ""}, None),
        ("AniList", "POST", settings.anilist_url, {"Content-Type": "application/json"},
         {"query": "{ Media(idMal: 1, type: ANIME) { id idMal } }"}),
        ("Kitsu", "GET", f"{settings.kitsu_base_url}/anime/1/episodes?page[limit]=1", {}, None),
        ("Jikan", "GET", f"{settings.jikan_base_url}/anime/1", {}, None),
        ("manami (GitHub)", "HEAD", settings.manami_url, {}, None),
    ]  # fmt: skip
    t = Table("fonte", "resultado", "tempo")
    for name, method, url, headers, body in checks:
        started = time.monotonic()
        try:
            r = httpx.request(method, url, headers=headers | {"User-Agent": settings.user_agent}, json=body,
                              timeout=10, follow_redirects=True)  # fmt: skip
            ok = r.status_code < 400
            res = f"[{'green' if ok else 'red'}]HTTP {r.status_code}[/]"
        except httpx.HTTPError as exc:
            res = f"[red]{type(exc).__name__}[/]"
        t.add_row(name, res, f"{time.monotonic() - started:.1f}s")
    console.print(t)


@app.command()
def ecosystem(
    only: Annotated[
        list[str] | None, typer.Option(help="Rodar só estas fontes: manga, anilist, kitsu (repita a opção).")
    ] = None,
    limit: Annotated[int | None, typer.Option(help="Limite por fonte (teste rápido).")] = None,
) -> None:
    """Carga do ecossistema completo, com as fontes rodando EM PARALELO (hosts diferentes):

    mangás (MAL API) · personagens/dubladores/staff/estúdios/pessoas (AniList) · episódios (Kitsu).
    Cada fonte tem checkpoint próprio: se algo cair, rode de novo que continua de onde parou.
    """
    from concurrent.futures import ThreadPoolExecutor

    settings = get_settings()
    wh = _wh()
    tasks = {
        "manga": lambda: _run_manga(settings, wh, limit, rediscover=False),
        "anilist": lambda: _run_anilist(settings, wh, limit),
        "kitsu": lambda: _run_kitsu(settings, wh, limit),
    }
    chosen = {k: v for k, v in tasks.items() if not only or k in only}
    console.print(f"Iniciando em paralelo: {', '.join(chosen)}. Pode deixar rodando; Ctrl+C interrompe com segurança.")
    results: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=len(chosen)) as pool:
        futures = {name: pool.submit(fn) for name, fn in chosen.items()}
        for name, fut in futures.items():
            try:
                results[name] = f"[green]ok[/] {fut.result()}"
            except Exception as exc:  # uma fonte falhar não derruba as outras
                results[name] = f"[red]falhou[/] {type(exc).__name__}: {str(exc)[:200]}"
    t = Table("fonte", "resultado", title="Carga do ecossistema")
    for name, res in results.items():
        t.add_row(name, res)
    console.print(t)
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


@app.command()
def publish(
    include_bronze: Annotated[
        bool, typer.Option(help="Incluir o bronze (JSON cru). Sem ele a cópia fica bem menor.")
    ] = False,
) -> None:
    """Gera a cópia de consulta do banco (REPORTS_DB_PATH) para usar no DBeaver/Power BI.

    A cópia é um arquivo DuckDB independente: pode ficar aberta no DBeaver sem travar a ingestão
    nem o dbt. Rode de novo após cada build para atualizar.
    """
    import shutil
    import time

    import duckdb

    settings = get_settings()
    src, dst = settings.duckdb_path, settings.reports_db_path
    if src.resolve() == dst.resolve():
        raise typer.BadParameter("REPORTS_DB_PATH precisa ser diferente de DUCKDB_PATH")
    tmp = dst.with_suffix(".tmp.duckdb")
    tmp.unlink(missing_ok=True)
    started = time.monotonic()

    con = duckdb.connect(str(tmp))
    # cópia grande (dezenas de tabelas, algumas com 100k+ linhas): sem ordem de inserção e com o mesmo
    # limite de memória do dbt — o DuckDB derrama para disco em vez de falhar
    con.execute("SET preserve_insertion_order = false")
    con.execute(f"SET memory_limit = '{os.getenv('DUCKDB_MEMORY_LIMIT', '4GB')}'")
    con.execute(f"ATTACH '{src.as_posix()}' AS src (READ_ONLY)")
    schemas = [
        r[0]
        for r in con.execute(
            "SELECT DISTINCT schema_name FROM duckdb_schemas() WHERE database_name = 'src' "
            "AND schema_name NOT IN ('information_schema', 'pg_catalog', 'main')"
        ).fetchall()
    ]
    if not include_bronze:
        schemas = [s for s in schemas if s != "bronze"]
    copied = 0
    for schema in sorted(schemas):
        con.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
        objects = con.execute(
            "SELECT table_name, table_type FROM information_schema.tables "
            "WHERE table_catalog = 'src' AND table_schema = ?",
            [schema],
        ).fetchall()
        for name, _kind in objects:
            # colunas técnicas (`_payload`, listas `_genres`…) ficam de fora: não servem para relatório e
            # são as mais pesadas
            cols = [
                r[0]
                for r in con.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_catalog = 'src' "
                    "AND table_schema = ? AND table_name = ? ORDER BY ordinal_position",
                    [schema, name],
                ).fetchall()
                if not r[0].startswith("_")
            ]
            col_list = ", ".join(f'"{c}"' for c in cols)
            # views viram tabelas: a cópia não depende de nada do banco original
            con.execute(
                f'CREATE OR REPLACE TABLE "{schema}"."{name}" AS SELECT {col_list} FROM src."{schema}"."{name}"'
            )
            copied += 1
        console.print(f"  {schema}: {len(objects)} objetos")
    con.execute("DETACH src")
    con.close()

    try:
        dst.unlink(missing_ok=True)
    except PermissionError as exc:
        tmp.unlink(missing_ok=True)
        raise typer.BadParameter(
            f"{dst} está em uso (DBeaver aberto?). Desconecte no DBeaver e rode `malpipe publish` de novo."
        ) from exc
    shutil.move(str(tmp), str(dst))
    size = dst.stat().st_size / 1e6
    console.print(
        f"[green]ok[/] {copied} tabelas em {dst} ({size:.0f} MB, {time.monotonic() - started:.0f}s). "
        "Conecte o DBeaver a este arquivo."
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


@app.command("site")
def site(
    out: Annotated[Path | None, typer.Option(help="Pasta de saída dos JSON (padrão: site/data do projeto).")] = None,
    username: Annotated[str | None, typer.Option(help="Lista usada na seção do recomendador.")] = None,
) -> None:
    """Atualiza os dados do painel público (site/data/*.json) a partir das marts. Depois: commit e push."""
    from malpipe.config import PROJECT_ROOT
    from malpipe.site import build_site_data

    settings = get_settings()
    target = out or PROJECT_ROOT / "site" / "data"
    counts = build_site_data(settings.duckdb_path, target, username or settings.mal_username)
    t = Table("conjunto", "linhas", title=f"Painel público → {target}")
    for name, n in counts.items():
        t.add_row(name, f"{n:,}", style="yellow" if n == 0 else None)
    console.print(t)
    if any(n == 0 for n in counts.values()):
        console.print("[yellow]Conjuntos vazios aparecem como 'sem dados' no painel — rode o build antes.[/]")
    console.print("Prévia local: [bold]python -m http.server -d site 8000[/] → http://localhost:8000")


@app.command("merge")
def merge(
    origem: Annotated[Path, typer.Argument(help="Outro arquivo .duckdb cujo bronze será copiado para o banco atual.")],
) -> None:
    """Junta o bronze de outro banco a este (sem duplicar execuções). Depois rode o build."""
    wh = _wh()
    console.print(f"Copiando de [bold]{origem}[/] para [bold]{wh.path}[/]…")
    copied = wh.merge_from(origem)
    t = Table("tabela", "linhas copiadas", title="Merge")
    for name, n in copied:
        t.add_row(name, f"{n:,}")
    console.print(t)
    wh.close()
    console.print("Pronto. Rode [bold]malpipe status[/] e depois o build.")


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

    eco = Table("fonte", "concluídos", "pendentes", title="Ecossistema")
    # mesma janela de atualização que cada comando usa (mangá/AniList/Kitsu: 4× REFRESH_DAYS)
    window = settings.refresh_days * 4
    targets = [
        ("mangá (MAL)", "bronze.mal_manga", wh.known_manga_ids_sql()),
        ("AniList (elenco/staff)", "bronze.anilist_media", wh.fetched_mal_ids_sql()),
        ("AniList (relações)", "bronze.anilist_relations", wh.fetched_mal_ids_sql()),
    ]
    for label, table, known in targets:
        done = len(wh.done_ids(table, window))
        eco.add_row(label, f"{done:,}", f"{len(wh.pending_ids(table, window, known)):,}")
    kitsu_done = wh.done_ids("bronze.kitsu_episodes", settings.refresh_days * 4)
    kitsu_todo = sum(1 for m in wh.kitsu_candidates() if m not in kitsu_done)
    eco.add_row("Kitsu (episódios)", f"{len(kitsu_done):,}", f"{kitsu_todo:,}")
    console.print(eco)
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

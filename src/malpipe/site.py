"""Exporta os dados do painel público (GitHub Pages) a partir das marts.

`malpipe site` grava um JSON por conjunto de dados em `site/data/`. A página `site/index.html` lê esses
arquivos e desenha os gráficos no navegador; o workflow `pages.yml` publica a pasta `site/` a cada push.

Só entram números agregados (contagens, médias, rankings curtos) — nunca a base bruta das APIs, cujos
termos não permitem redistribuição.
"""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from pathlib import Path

import duckdb

# A base de episódios do Kitsu tem pouca cobertura a partir de 2020 (ver README, achado 10).
EPISODES_LAST_RELIABLE_YEAR = 2019
SCORES_FIRST_YEAR = 1995  # antes disso há poucos títulos por ano
ORIGIN_FIRST_YEAR = 2011
ORIGIN_MIN_SCORED_PER_SEASON = 50
MIN_ADAPTATIONS = 30
MIN_STUDIO_TITLES = 100
TOP_STUDIOS = 10
TOP_VOICE_ACTORS = 10
TOP_UNADAPTED = 8
TOP_RECOMMENDATIONS = 20
RECSYS_MIN_MEMBERS = 5000  # mesmo corte do recomendador de conteúdo (catálogo de candidatos)

DATASETS: dict[str, str] = {
    "panorama": """
        SELECT * FROM (VALUES
            ('animes',     (SELECT count(*) FROM core.dim_anime)),
            ('mangas',     (SELECT count(*) FROM core.dim_manga)),
            ('dubladores', (SELECT count(*) FROM analytics.mart_voice_actor_ranking)),
            ('episodios',  (SELECT coalesce(sum(episodes_aired), 0) FROM analytics.mart_episode_trends))
        ) AS t(metrica, valor)
    """,
    "notas_por_ano": f"""
        SELECT season_year AS ano, num_titles AS titulos, round(avg_score, 3) AS nota_media,
               round(p10_score, 3) AS p10, round(p90_score, 3) AS p90
        FROM analytics.mart_score_inflation
        WHERE season_year BETWEEN {SCORES_FIRST_YEAR} AND year(current_date)
        ORDER BY ano
    """,
    "origem_por_ano": f"""
        SELECT season_year AS ano,
               round(avg(share_original), 3)    AS original,
               round(avg(share_manga), 3)       AS manga,
               round(avg(share_light_novel), 3) AS light_novel,
               round(avg(share_sequels), 3)     AS sequencias
        FROM analytics.mart_season_trends
        WHERE num_scored >= {ORIGIN_MIN_SCORED_PER_SEASON} AND season_year >= {ORIGIN_FIRST_YEAR}
        GROUP BY season_year
        ORDER BY ano
    """,
    "adaptacao_resumo": """
        SELECT count(*)                                              AS adaptacoes,
               count(DISTINCT manga_id)                              AS obras,
               round(avg((anime_minus_manga > 0)::int), 3)           AS pct_anime_melhor,
               round(median(anime_minus_manga), 2)                   AS diferenca_mediana,
               round(avg((abs(anime_minus_manga) <= 0.25)::int), 3)  AS pct_empate
        FROM analytics.mart_adaptation_scores
        WHERE num_source_works = 1
    """,
    "adaptacao_por_origem": f"""
        SELECT CASE source_type WHEN 'manga' THEN 'Mangá' WHEN 'light_novel' THEN 'Light novel'
                    WHEN 'manhwa' THEN 'Manhwa' WHEN 'manhua' THEN 'Manhua' ELSE source_type END AS origem,
               count(*)                                     AS adaptacoes,
               round(median(anime_minus_manga), 2)          AS diferenca_mediana,
               round(avg((anime_minus_manga > 0)::int), 3)  AS pct_anime_melhor
        FROM analytics.mart_adaptation_scores
        WHERE num_source_works = 1
        GROUP BY source_type
        HAVING count(*) >= {MIN_ADAPTATIONS}
        ORDER BY adaptacoes DESC
    """,
    "adaptacao_por_estudio": f"""
        SELECT main_studio_name AS estudio, count(*) AS adaptacoes, round(avg(anime_minus_manga), 3) AS diferenca_media
        FROM analytics.mart_adaptation_scores
        WHERE num_source_works = 1 AND main_studio_name IS NOT NULL
        GROUP BY main_studio_name
        HAVING count(*) >= {MIN_ADAPTATIONS}
        ORDER BY diferenca_media DESC
    """,
    "estudios": f"""
        SELECT studio_name AS estudio, num_titles AS titulos, median_score AS nota_mediana,
               total_members AS membros, best_title AS melhor_titulo
        FROM analytics.mart_studio_performance
        WHERE num_titles >= {MIN_STUDIO_TITLES}
        ORDER BY median_score DESC, num_titles DESC
        LIMIT {TOP_STUDIOS}
    """,
    "dubladores": f"""
        SELECT person_name AS dublador, person_name_native AS nome_japones, num_anime AS animes,
               num_characters AS personagens, num_main_roles AS protagonistas,
               most_famous_character AS personagem_mais_querido
        FROM analytics.mart_voice_actor_ranking
        WHERE voice_language = 'Japanese'
        ORDER BY num_characters DESC, num_anime DESC
        LIMIT {TOP_VOICE_ACTORS}
    """,
    "episodios": f"""
        SELECT aired_year AS ano, episodes_aired AS episodios, avg_length_min AS duracao_media_min
        FROM analytics.mart_episode_trends
        WHERE aired_year BETWEEN 1975 AND {EPISODES_LAST_RELIABLE_YEAR}
        ORDER BY ano
    """,
    "sem_anime": f"""
        SELECT g.popularity_rank_unadapted AS posicao,
               coalesce(nullif(m.title_english, ''), g.title) AS obra,
               g.start_year AS inicio,
               regexp_replace(g.authors_label, ' \\([^)]*\\)', '', 'g') AS autor,
               g.mean_score AS nota,
               g.num_list_users AS leitores
        FROM analytics.mart_manga_adaptation_gap g
        JOIN core.dim_manga m USING (manga_id)
        ORDER BY g.popularity_rank_unadapted
        LIMIT {TOP_UNADAPTED}
    """,
}


def _recommendations(con: duckdb.DuckDBPyConnection, username: str) -> tuple[list[dict], list[dict]]:
    if not _exists(con, "ml", "recommendations_for_user"):
        return [], []
    recs = con.execute(
        f"""
        SELECT rank AS posicao, title AS titulo, because_you_liked AS porque_gostou_de,
               CASE WHEN already_in_plan_to_watch THEN 'sim' ELSE 'não' END AS ja_na_fila
        FROM ml.recommendations_for_user
        WHERE username = ?
        ORDER BY rank
        LIMIT {TOP_RECOMMENDATIONS}
        """,
        [username],
    ).fetchall()
    cols = ["posicao", "titulo", "porque_gostou_de", "ja_na_fila"]
    rows = [dict(zip(cols, r, strict=True)) for r in recs]
    queue = con.execute(
        "SELECT count(*) FROM core.fct_my_list WHERE username = ? AND list_status = 'plan_to_watch'", [username]
    ).fetchone()[0]
    has_size = any(
        c == "catalog_size"
        for (c,) in con.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'ml' AND table_name = 'recommendations_for_user'"
        ).fetchall()
    )
    if has_size:
        catalog = con.execute(
            "SELECT max(catalog_size) FROM ml.recommendations_for_user WHERE username = ?", [username]
        ).fetchone()[0]
    else:  # tabela gerada antes da coluna existir: mesmo critério do recomendador
        catalog = con.execute(
            """
            SELECT count(*) FROM core.dim_anime a
            LEFT JOIN core.fct_my_list m ON m.mal_id = a.mal_id AND m.username = ?
            WHERE a.media_type IN ('tv', 'movie', 'ona', 'ova') AND (a.num_list_users >= ? OR m.mal_id IS NOT NULL)
            """,
            [username, RECSYS_MIN_MEMBERS],
        ).fetchone()[0]
    base = [{"lista": username, "fila_quero_assistir": queue, "catalogo_candidatos": catalog}] if rows else []
    return rows, base


def _exists(con: duckdb.DuckDBPyConnection, schema: str, table: str) -> bool:
    return bool(
        con.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema = ? AND table_name = ?",
            [schema, table],
        ).fetchone()[0]
    )


def _clean(value):
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if hasattr(value, "item"):  # numpy / decimal escalares
        return value.item()
    if isinstance(value, int | float | str | bool) or value is None:
        return value
    return float(value) if hasattr(value, "__float__") else str(value)


def build_site_data(duckdb_path: Path, out_dir: Path, username: str | None) -> dict[str, int]:
    """Grava `<out_dir>/<conjunto>.json` (lista de linhas) e `meta.json`. Devolve linhas por conjunto."""
    out_dir.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(duckdb_path), read_only=True)
    counts: dict[str, int] = {}
    try:
        for name, sql in DATASETS.items():
            cur = con.execute(sql)
            cols = [d[0] for d in cur.description]
            rows = [{c: _clean(v) for c, v in zip(cols, r, strict=True)} for r in cur.fetchall()]
            _write(out_dir / f"{name}.json", rows)
            counts[name] = len(rows)
        recs, base = _recommendations(con, username) if username else ([], [])
        _write(out_dir / "recomendacoes.json", recs)
        _write(out_dir / "recomendador_base.json", base)
        counts["recomendacoes"], counts["recomendador_base"] = len(recs), len(base)
    finally:
        con.close()
    meta = {"generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "username": username, "rows": counts}
    _write(out_dir / "meta.json", meta)
    return counts


def _write(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

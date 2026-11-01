from __future__ import annotations

from datetime import timedelta

from malpipe.warehouse import utcnow


def _insert(wh, mal_id: int, status: int, days_ago: int) -> None:
    wh.insert_rows(
        "bronze.mal_anime",
        ("mal_id", "http_status", "payload", "error", "extracted_at", "run_id"),
        [(mal_id, status, '{"id": 1}' if status == 200 else None, None, utcnow() - timedelta(days=days_ago), "r")],
    )


def test_pending_ids_checkpoint_rules(wh):
    candidates = "SELECT * FROM (VALUES (1), (2), (3), (4), (5)) t(mal_id)"
    _insert(wh, 1, 200, days_ago=1)  # fresco → fora
    _insert(wh, 2, 200, days_ago=30)  # velho → volta pra fila
    _insert(wh, 3, 404, days_ago=30)  # não existe → fora (por padrão)
    _insert(wh, 4, 429, days_ago=1)  # falha transitória → volta pra fila
    # 5 nunca foi extraído → na fila

    assert wh.pending_ids("bronze.mal_anime", 7, candidates) == [2, 4, 5]
    assert wh.pending_ids("bronze.mal_anime", 7, candidates, retry_not_found=True) == [2, 3, 4, 5]
    assert wh.pending_ids("bronze.mal_anime", 7, candidates, limit=1) == [2]


def test_known_ids_include_manami_mal_sources(wh):
    wh.insert_rows(
        "bronze.manami_anime",
        ("payload", "dataset_date", "extracted_at", "run_id"),
        [('{"sources": ["https://anilist.co/anime/9", "https://myanimelist.net/anime/42"]}', None, utcnow(), "r")],
    )
    wh.insert_rows(
        "bronze.mal_anime_discovery", ("mal_id", "discovered_via", "extracted_at", "run_id"),
        [(7, "ranking:all", utcnow(), "r")],
    )  # fmt: skip
    ids = sorted(r[0] for r in wh.con.execute(wh.known_mal_ids_sql()).fetchall())
    assert ids == [7, 42]

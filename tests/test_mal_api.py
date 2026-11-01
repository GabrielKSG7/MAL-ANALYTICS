from __future__ import annotations

import json

import httpx
import respx

from malpipe.sources import mal_api
from tests.conftest import anime_payload

BASE = "https://api.test/v2"


@respx.mock
def test_discover_ranking_follows_paging_next(wh, make_client):
    respx.get(f"{BASE}/anime/ranking", params={"offset": "500"}).mock(
        return_value=httpx.Response(200, json={"data": [{"node": {"id": 3}}], "paging": {}})
    )
    respx.get(f"{BASE}/anime/ranking").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [{"node": {"id": 1}}, {"node": {"id": 2}}],
                "paging": {"next": f"{BASE}/anime/ranking?offset=500&limit=500&ranking_type=all"},
            },
        )
    )
    with wh.run("test") as run:
        n = mal_api.discover_ranking(make_client(), wh, run)
    assert n == 3
    ids = [r[0] for r in wh.con.execute("SELECT mal_id FROM bronze.mal_anime_discovery ORDER BY 1").fetchall()]
    assert ids == [1, 2, 3]


@respx.mock
def test_fetch_details_records_success_and_404(wh, make_client):
    respx.get(f"{BASE}/anime/1").mock(return_value=httpx.Response(200, json=anime_payload(1)))
    respx.get(f"{BASE}/anime/2").mock(return_value=httpx.Response(404, json={"error": "not_found"}))
    with wh.run("test") as run:
        stats = mal_api.fetch_details(make_client(), wh, run, [1, 2], flush_every=1)
    assert stats == {200: 1, 404: 1}
    rows = wh.con.execute("SELECT mal_id, http_status, payload FROM bronze.mal_anime ORDER BY 1").fetchall()
    assert rows[0][1] == 200 and json.loads(rows[0][2])["title"] == "Anime 1"
    assert rows[1][1] == 404 and rows[1][2] is None
    run_row = wh.con.execute("SELECT status, rows_written FROM meta.runs").fetchone()
    assert run_row == ("success", 2)


@respx.mock
def test_fetch_user_list_paginates(wh, make_client):
    item = {"node": {"id": 5, "title": "X"}, "list_status": {"status": "completed", "score": 9}}
    respx.get(f"{BASE}/users/gabriel/animelist").mock(
        return_value=httpx.Response(200, json={"data": [item, item | {"node": {"id": 6}}], "paging": {}})
    )
    with wh.run("test") as run:
        assert mal_api.fetch_user_list(make_client(), wh, run, "gabriel") == 2


def test_build_client_requires_client_id(monkeypatch):
    from malpipe.config import Settings

    settings = Settings(mal_client_id=None)
    try:
        mal_api.build_client(settings)
    except RuntimeError as exc:
        assert "MAL_CLIENT_ID" in str(exc)
    else:
        raise AssertionError("deveria exigir MAL_CLIENT_ID")


def test_failed_run_is_recorded(wh):
    try:
        with wh.run("explode"):
            raise ValueError("falhou")
    except ValueError:
        pass
    status, notes = wh.con.execute("SELECT status, notes FROM meta.runs").fetchone()
    assert status == "failed" and "falhou" in notes

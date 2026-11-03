from __future__ import annotations

import json

import httpx
import pytest
import respx

from malpipe.sources import anilist, kitsu, mal_api

ANILIST = "https://graphql.anilist.co"
KITSU = "https://kitsu.test/api/edge"


def _person(pid: int, lang: str = "Japanese") -> dict:
    return {"id": pid, "name": {"full": f"P{pid}", "native": None}, "languageV2": lang, "gender": None,
            "favourites": 1, "primaryOccupations": [], "homeTown": None, "yearsActive": [],
            "dateOfBirth": {"year": None, "month": None, "day": None},
            "dateOfDeath": {"year": None, "month": None, "day": None},
            "image": {"medium": None}, "siteUrl": None}  # fmt: skip


def _char_edge(cid: int) -> dict:
    return {"role": "MAIN", "node": {"id": cid, "name": {"full": f"C{cid}", "native": None}},
            "voiceActorRoles": [{"roleNotes": None, "dubGroup": None, "voiceActor": _person(cid + 1000)}]}  # fmt: skip


def anilist_responder(pages_chars: int, pages_staff: int):
    """Simula a AniList: devolve a página pedida de personagens/staff e o hasNextPage correspondente."""

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        v = body["variables"]
        if v["idMal"] == 404:
            return httpx.Response(404, json={"data": {"Media": None}, "errors": [{"message": "Not Found."}]})
        page = v["page"]
        media = {"id": 9000 + v["idMal"], "idMal": v["idMal"]}
        if v["withMeta"]:
            media |= {"title": {"romaji": "X"}, "studios": {"edges": []}, "tags": []}
        if v["withChars"]:
            media["characters"] = {"pageInfo": {"hasNextPage": page < pages_chars},
                                   "edges": [_char_edge(page * 10 + i) for i in range(2)]}  # fmt: skip
        if v["withStaff"]:
            media["staff"] = {"pageInfo": {"hasNextPage": page < pages_staff},
                              "edges": [{"role": "Director", "node": _person(500 + page)}]}  # fmt: skip
        return httpx.Response(200, json={"data": {"Media": media}})

    return handler


@respx.mock
def test_anilist_merges_all_pages_and_respects_page_cap(wh, make_client):
    route = respx.post(ANILIST).mock(side_effect=anilist_responder(pages_chars=3, pages_staff=1))
    client = make_client(base_url=ANILIST)
    with wh.run("anilist") as run:
        stats = anilist.fetch_all(client, wh, run, [1, 404], max_pages=2)
    assert stats == {200: 1, 404: 1}
    payload = json.loads(wh.con.execute("SELECT payload FROM bronze.anilist_media WHERE mal_id = 1").fetchone()[0])
    assert len(payload["characters"]) == 4  # 2 páginas (limite) × 2
    assert len(payload["staff"]) == 1  # staff só tinha 1 página
    assert payload["truncated"] is True  # sobrou a 3ª página de personagens
    assert route.call_count == 3  # 1ª página + 1 extra para id 1, e 1 chamada para o 404


@respx.mock
def test_anilist_graphql_error_is_not_saved_as_success_and_stops_after_3(wh, make_client):
    respx.post(ANILIST).mock(
        return_value=httpx.Response(200, json={"data": None, "errors": [{"message": "Cannot query field"}]})
    )
    with pytest.raises(RuntimeError, match="rejeitou a consulta"), wh.run("anilist") as run:
        anilist.fetch_all(make_client(base_url=ANILIST), wh, run, [1, 2, 3, 4, 5], max_pages=2)
    rows = wh.con.execute("SELECT http_status, payload FROM bronze.anilist_media").fetchall()
    assert rows and all(status == 400 and payload is None for status, payload in rows)


@respx.mock
def test_kitsu_follows_next_links(wh, make_client):
    page1 = {"data": [{"id": "1", "attributes": {"number": 1, "canonicalTitle": "A"}}],
             "links": {"next": f"{KITSU}/anime/7/episodes?page%5Boffset%5D=20"}}  # fmt: skip
    page2 = {"data": [{"id": "2", "attributes": {"number": 2, "canonicalTitle": "B"}}], "links": {}}
    respx.get(url__regex=rf"{KITSU}/anime/7/episodes.*offset%5D=20").mock(return_value=httpx.Response(200, json=page2))
    respx.get(url__regex=rf"{KITSU}/anime/7/episodes.*").mock(return_value=httpx.Response(200, json=page1))
    with wh.run("kitsu") as run:
        kitsu.fetch_all(make_client(base_url=KITSU), wh, run, {70: 7})
    mal_id, kitsu_id, payload = wh.con.execute("SELECT mal_id, kitsu_id, payload FROM bronze.kitsu_episodes").fetchone()
    eps = json.loads(payload)
    assert (mal_id, kitsu_id) == (70, 7)
    assert [e["number"] for e in eps] == [1, 2]


@respx.mock
def test_manga_discovery_and_details_use_manga_tables(wh, make_client):
    base = "https://api.test/v2"
    respx.get(f"{base}/manga/ranking").mock(
        return_value=httpx.Response(200, json={"data": [{"node": {"id": 2}}, {"node": {"id": 13}}], "paging": {}})
    )
    respx.get(f"{base}/manga/2").mock(return_value=httpx.Response(200, json={"id": 2, "title": "Berserk"}))
    respx.get(f"{base}/manga/13").mock(return_value=httpx.Response(404, json={"error": "not_found"}))
    client = make_client(base_url=base)
    with wh.run("manga") as run:
        assert mal_api.discover_ranking(client, wh, run, kind="manga") == 2
        ids = wh.pending_ids("bronze.mal_manga", 28, wh.known_manga_ids_sql())
        assert ids == [2, 13]
        assert mal_api.fetch_details(client, wh, run, ids, kind="manga") == {200: 1, 404: 1}
    assert wh.pending_ids("bronze.mal_manga", 28, wh.known_manga_ids_sql()) == []
    assert wh.con.execute("SELECT count(*) FROM bronze.mal_anime").fetchone()[0] == 0


def test_kitsu_candidates_only_series_with_mapping(wh):
    from malpipe.warehouse import utcnow

    manami = [
        {"sources": ["https://myanimelist.net/anime/1", "https://kitsu.app/anime/11"]},
        {"sources": ["https://myanimelist.net/anime/2", "https://kitsu.app/anime/22"]},
        {"sources": ["https://myanimelist.net/anime/3"]},
    ]
    wh.insert_rows("bronze.manami_anime", ("payload", "dataset_date", "extracted_at", "run_id"),
                   [(json.dumps(m), None, utcnow(), "r") for m in manami])  # fmt: skip
    wh.insert_rows(
        "bronze.mal_anime", ("mal_id", "http_status", "payload", "error", "extracted_at", "run_id"),
        [(1, 200, '{"media_type": "tv"}', None, utcnow(), "r"),
         (2, 200, '{"media_type": "movie"}', None, utcnow(), "r"),
         (3, 200, '{"media_type": "tv"}', None, utcnow(), "r")],
    )  # fmt: skip
    assert wh.kitsu_candidates() == {1: 11}


def test_merge_copies_bronze_once_and_tolerates_older_schema(tmp_path, wh):
    from malpipe.warehouse import Warehouse, utcnow

    other = Warehouse(tmp_path / "old.duckdb")
    with other.run("mal-details") as run:
        other.insert_rows("bronze.mal_anime", ("mal_id", "http_status", "payload", "error", "extracted_at", "run_id"),
                          [(i, 200, f'{{"id": {i}}}', None, utcnow(), run.run_id) for i in range(1, 4)])  # fmt: skip
    # banco "antigo": sem as tabelas do ecossistema
    other.con.execute("DROP TABLE bronze.anilist_media")
    other.close()

    with wh.run("manga") as run:
        wh.insert_rows("bronze.mal_manga", ("mal_id", "http_status", "payload", "error", "extracted_at", "run_id"),
                       [(9, 200, "{}", None, utcnow(), run.run_id)])  # fmt: skip

    first = dict(wh.merge_from(tmp_path / "old.duckdb"))
    assert first["bronze.mal_anime"] == 3 and first["meta.runs"] == 1
    assert dict(wh.merge_from(tmp_path / "old.duckdb"))["bronze.mal_anime"] == 0  # idempotente
    assert wh.con.execute("SELECT count(*) FROM bronze.mal_anime").fetchone()[0] == 3
    assert wh.con.execute("SELECT count(*) FROM bronze.mal_manga").fetchone()[0] == 1  # o que já havia continua
    with pytest.raises(ValueError):
        wh.merge_from(wh.path)

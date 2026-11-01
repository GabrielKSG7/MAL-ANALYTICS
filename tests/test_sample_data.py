from __future__ import annotations

import json

from malpipe.sample_data import generate, score_distribution


def test_sample_is_deterministic(tmp_path):
    from malpipe.warehouse import Warehouse

    counts = []
    for name in ("a", "b"):
        wh = Warehouse(tmp_path / f"{name}.duckdb")
        with wh.run("sample") as run:
            counts.append(generate(wh, run, n_anime=40, n_users=50, seed=7))
        titles = wh.con.execute("SELECT payload->>'$.title' FROM bronze.mal_anime ORDER BY mal_id LIMIT 5").fetchall()
        counts.append(titles)
        wh.close()
    assert counts[0] == counts[2] and counts[1] == counts[3]


def test_sample_payload_matches_api_contract(wh):
    with wh.run("sample") as run:
        generate(wh, run, n_anime=20, n_users=10)
    sql = "SELECT payload FROM bronze.mal_anime WHERE http_status = 200 LIMIT 1"
    payload = json.loads(wh.con.execute(sql).fetchone()[0])
    for key in ("id", "title", "mean", "num_list_users", "genres", "studios", "start_season", "statistics"):
        assert key in payload
    # a API real manda os contadores como string — o staging precisa lidar com isso
    assert isinstance(payload["statistics"]["status"]["completed"], str)


def test_score_distribution_shape():
    dist = score_distribution(8.0, polarization=0.0, total_votes=10_000)
    assert len(dist) == 10
    assert abs(sum(d["percentage"] for d in dist) - 100) < 1.5
    assert max(dist, key=lambda d: d["votes"])["score"] == 8

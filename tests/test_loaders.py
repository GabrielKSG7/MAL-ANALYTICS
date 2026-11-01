from __future__ import annotations

import json

import zstandard

from malpipe.sources import kaggle, manami


def _manami_file(tmp_path, last_update="2026-10-01"):
    data = {
        "lastUpdate": last_update,
        "data": [
            {"sources": ["https://myanimelist.net/anime/1"], "title": "A", "tags": ["x"]},
            {"sources": ["https://anilist.co/anime/2"], "title": "B", "tags": []},
        ],
    }
    path = tmp_path / "aod.json.zst"
    path.write_bytes(zstandard.ZstdCompressor().compress(json.dumps(data).encode()))
    return path


def test_manami_load_is_idempotent_per_snapshot(wh, tmp_path):
    path = _manami_file(tmp_path)
    with wh.run("manami") as run:
        assert manami.load(wh, run, path) == 2
    with wh.run("manami") as run:
        assert manami.load(wh, run, path) == 0  # mesmo snapshot → nada a fazer
    assert wh.con.execute("SELECT count(*) FROM bronze.manami_anime").fetchone()[0] == 2


def test_manami_reads_plain_json(tmp_path):
    path = tmp_path / "aod.json"
    path.write_text(json.dumps({"data": []}))
    assert manami.read_dataset(path) == {"data": []}


def test_kaggle_load_with_user_sampling(wh, tmp_path):
    csv = tmp_path / "animelist.csv"
    rows = ["user_id,anime_id,score,watching_status,watched_episodes"]
    for user in range(10):
        for anime in range(3):
            rows.append(f"{user},{100 + anime},{(user + anime) % 11},2,12")
    csv.write_text("\n".join(rows))

    with wh.run("kaggle") as run:
        assert kaggle.load_animelist(wh, run, csv, sample_users=4) == 12
    # recarregar o mesmo arquivo substitui (não duplica)
    with wh.run("kaggle") as run:
        assert kaggle.load_animelist(wh, run, csv) == 30
    assert wh.con.execute("SELECT count(*) FROM bronze.kaggle_animelist").fetchone()[0] == 30


def test_kaggle_rejects_wrong_columns(wh, tmp_path):
    csv = tmp_path / "bad.csv"
    csv.write_text("a,b\n1,2\n")
    with wh.run("kaggle") as run:
        try:
            kaggle.load_animelist(wh, run, csv)
        except ValueError as exc:
            assert "colunas" in str(exc)
        else:
            raise AssertionError("deveria rejeitar CSV sem as colunas esperadas")


def test_manami_detects_zstd_by_magic_bytes_not_extension(tmp_path):
    path = tmp_path / "download.bin"  # extensão "errada"
    path.write_bytes(zstandard.ZstdCompressor().compress(b'{"data": [1]}'))
    assert manami.read_dataset(path) == {"data": [1]}


def test_dotenv_with_bom_is_read(tmp_path, monkeypatch):
    from dotenv import dotenv_values

    env = tmp_path / ".env"
    env.write_bytes("﻿MAL_USERNAME=gabu\nMAL_RPS=1.0\n".encode())
    assert dotenv_values(env, encoding="utf-8-sig")["MAL_USERNAME"] == "gabu"


def test_relative_duckdb_path_resolves_from_project_root(monkeypatch):
    from malpipe.config import PROJECT_ROOT, Settings

    monkeypatch.setenv("DUCKDB_PATH", "data/x.duckdb")
    assert Settings().duckdb_path == (PROJECT_ROOT / "data" / "x.duckdb").resolve()
    monkeypatch.setenv("DUCKDB_PATH", "/abs/y.duckdb")
    assert str(Settings().duckdb_path).replace("\\", "/").endswith("/abs/y.duckdb")

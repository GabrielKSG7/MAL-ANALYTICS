from __future__ import annotations

import pytest

from malpipe.http import PoliteClient
from malpipe.warehouse import Warehouse


@pytest.fixture
def wh(tmp_path):
    w = Warehouse(tmp_path / "test.duckdb")
    yield w
    w.close()


@pytest.fixture
def sleeps():
    """Registra os 'sleeps' em vez de dormir de verdade."""
    return []


@pytest.fixture
def make_client(sleeps):
    def _make(base_url: str = "https://api.test/v2", rps: float = 100.0, **kwargs) -> PoliteClient:
        return PoliteClient(base_url=base_url, rps=rps, sleep=sleeps.append, backoff_base=1.5, **kwargs)

    return _make


def anime_payload(mal_id: int, **overrides) -> dict:
    """Payload mínimo no formato da MAL API v2 (com os contadores de status como string, como a API real)."""
    payload = {
        "id": mal_id,
        "title": f"Anime {mal_id}",
        "mean": 8.1,
        "rank": 10,
        "popularity": 20,
        "num_list_users": 1000,
        "num_scoring_users": 600,
        "media_type": "tv",
        "status": "finished_airing",
        "start_date": "2020-04",
        "start_season": {"year": 2020, "season": "spring"},
        "genres": [{"id": 1, "name": "Action"}],
        "studios": [{"id": 9, "name": "Studio X"}],
        "statistics": {
            "status": {"watching": "10", "completed": "500", "on_hold": "5", "dropped": "20", "plan_to_watch": "100"}
        },  # fmt: skip
    }
    payload.update(overrides)
    return payload

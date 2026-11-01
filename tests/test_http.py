from __future__ import annotations

import httpx
import pytest
import respx

from malpipe.http import RateLimiter


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0
        self.slept: list[float] = []

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


def test_rate_limiter_enforces_min_interval():
    clock = FakeClock()
    limiter = RateLimiter(rps=2.0, clock=clock.time, sleep=clock.sleep)  # 0.5 s entre chamadas
    limiter.wait()  # primeira chamada não espera
    clock.now += 0.1
    limiter.wait()
    assert clock.slept == [pytest.approx(0.4)]
    clock.now += 1.0  # já passou do intervalo
    limiter.wait()
    assert len(clock.slept) == 1


def test_rate_limiter_rejects_invalid_rps():
    with pytest.raises(ValueError):
        RateLimiter(rps=0)


@respx.mock
def test_retries_on_429_respecting_retry_after(make_client, sleeps):
    route = respx.get("https://api.test/v2/anime/1").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "7"}),
            httpx.Response(200, json={"id": 1}),
        ]
    )
    result = make_client().get("/anime/1")
    assert result.ok and result.payload == {"id": 1}
    assert route.call_count == 2
    assert 7.0 in sleeps  # usou o Retry-After e não o backoff


@respx.mock
def test_404_is_definitive_and_not_retried(make_client):
    route = respx.get("https://api.test/v2/anime/999").mock(
        return_value=httpx.Response(404, json={"error": "not_found"})
    )
    result = make_client().get("/anime/999")
    assert not result.ok
    assert result.status_code == 404
    assert route.call_count == 1


@respx.mock
def test_gives_up_after_max_retries(make_client):
    route = respx.get("https://api.test/v2/x").mock(return_value=httpx.Response(503))
    result = make_client(max_retries=2).get("/x")
    assert result.status_code == 503
    assert "falhou" in result.error
    assert route.call_count == 3


@respx.mock
def test_network_error_is_retried(make_client):
    respx.get("https://api.test/v2/y").mock(
        side_effect=[httpx.ConnectError("boom"), httpx.Response(200, json={"ok": True})]
    )
    assert make_client().get("/y").payload == {"ok": True}


@respx.mock
def test_circuit_breaker_stops_run_and_keeps_progress(wh, make_client):
    import pytest

    from malpipe.http import HostUnreachableError
    from malpipe.sources import jikan

    route = respx.get(url__regex=r"https://api.test/v4/anime/\d+/statistics").mock(
        side_effect=httpx.ConnectTimeout("timeout")
    )
    client = make_client(base_url="https://api.test/v4")
    with pytest.raises(HostUnreachableError), wh.run("jikan") as run:
        jikan.fetch_entity(client, wh, run, "statistics", list(range(1, 50)))
    # parou no 3º ID (disjuntor), com 1 tentativa + 2 retries de rede cada
    assert route.call_count == 9
    rows = wh.con.execute("SELECT count(*), max(http_status) FROM bronze.jikan_statistics").fetchone()
    assert rows == (3, 0)  # falhas gravadas: voltam para a fila na próxima execução
    assert wh.con.execute("SELECT status FROM meta.runs").fetchone()[0] == "failed"

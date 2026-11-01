"""Cliente HTTP educado: rate limit, retry com backoff exponencial e respeito a Retry-After."""

from __future__ import annotations

import logging
import random
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

import httpx

log = logging.getLogger(__name__)

RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class RateLimiter:
    """Garante um intervalo mínimo entre requisições (1 / rps).

    Simples e previsível: para um crawler single-thread de longa duração isso é melhor
    do que um token bucket com rajadas, que tende a disparar 429 no início.
    """

    def __init__(
        self,
        rps: float,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if rps <= 0:
            raise ValueError("rps deve ser > 0")
        self.min_interval = 1.0 / rps
        self._clock = clock
        self._sleep = sleep
        self._last: float | None = None
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            now = self._clock()
            if self._last is not None:
                elapsed = now - self._last
                if elapsed < self.min_interval:
                    self._sleep(self.min_interval - elapsed)
                    now = self._clock()
            self._last = now


@dataclass
class FetchResult:
    url: str
    status_code: int
    payload: dict | None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300 and self.payload is not None


def _retry_after_seconds(response: httpx.Response) -> float | None:
    value = response.headers.get("Retry-After")
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        return None


class PoliteClient:
    """Wrapper de httpx.Client com rate limit e retry.

    Retorna FetchResult em vez de levantar exceção para 4xx "definitivos" (ex.: 404 de um
    ID que não existe), porque no crawl por ID isso é esperado e precisa ser registrado
    no checkpoint para não ser tentado de novo a cada execução.
    """

    def __init__(
        self,
        base_url: str,
        rps: float,
        headers: dict[str, str] | None = None,
        timeout: float = 30.0,
        max_retries: int = 5,
        backoff_base: float = 2.0,
        backoff_cap: float = 120.0,
        sleep: Callable[[float], None] = time.sleep,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.limiter = RateLimiter(rps, sleep=sleep)
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.backoff_cap = backoff_cap
        self._sleep = sleep
        self._client = httpx.Client(
            base_url=base_url,
            headers=headers or {},
            timeout=timeout,
            follow_redirects=True,
            transport=transport,
        )

    def _backoff(self, attempt: int) -> float:
        delay = min(self.backoff_cap, self.backoff_base**attempt)
        return delay + random.uniform(0, delay * 0.1)  # jitter

    def get(self, url: str, params: dict | None = None) -> FetchResult:
        last_error: str | None = None
        last_status = 0
        for attempt in range(self.max_retries + 1):
            self.limiter.wait()
            try:
                response = self._client.get(url, params=params)
            except httpx.TransportError as exc:
                last_error, last_status = f"{type(exc).__name__}: {exc}", 0
                delay = self._backoff(attempt)
                log.warning("erro de rede em %s (%s); nova tentativa em %.1fs", url, exc, delay)
                self._sleep(delay)
                continue

            last_status = response.status_code
            if response.status_code in RETRYABLE_STATUS:
                delay = _retry_after_seconds(response) or self._backoff(attempt)
                last_error = f"HTTP {response.status_code}"
                log.warning("%s em %s; nova tentativa em %.1fs", last_error, url, delay)
                self._sleep(delay)
                continue

            if response.is_success:
                try:
                    return FetchResult(str(response.url), response.status_code, response.json())
                except ValueError as exc:
                    return FetchResult(str(response.url), response.status_code, None, f"JSON inválido: {exc}")

            # 4xx não-retentável (404, 400, 403): resultado definitivo.
            return FetchResult(str(response.url), response.status_code, None, response.text[:500])

        return FetchResult(url, last_status, None, f"esgotou {self.max_retries} retries: {last_error}")

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> PoliteClient:
        return self

    def __exit__(self, *exc) -> None:
        self.close()

"""Conector do anime-offline-database (manami-project).

Repositório: https://github.com/manami-project/anime-offline-database
Licença dos dados: ODbL v1.0 + DbCL v1.0 — exige atribuição e share-alike se você
redistribuir uma base derivada. Para uso pessoal/consulta local não há restrição prática.

Um JSON (comprimido em zstd) atualizado semanalmente com ~40 mil animes, metadados
básicos, tags e — o mais valioso — referências cruzadas entre MAL, AniList, Kitsu, AniDB etc.
Usamos como: (1) universo de IDs do MAL para o crawl; (2) tags temáticas; (3) ponte entre sites.
"""

from __future__ import annotations

import io
import json
import logging
from datetime import date
from pathlib import Path

import httpx
import zstandard

from malpipe.warehouse import RunContext, Warehouse, to_json, utcnow

log = logging.getLogger(__name__)


def download(url: str, dest: Path, timeout: float = 120.0) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with httpx.stream("GET", url, follow_redirects=True, timeout=timeout) as r:
        r.raise_for_status()
        with dest.open("wb") as fh:
            for chunk in r.iter_bytes():
                fh.write(chunk)
    log.info("manami baixado em %s (%.1f MB)", dest, dest.stat().st_size / 1e6)
    return dest


ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"


def read_dataset(path: Path) -> dict:
    """Lê o dataset em JSON puro ou comprimido com zstd (detectado pelos magic bytes, não pela extensão)."""
    raw = path.read_bytes()
    if raw[:4] == ZSTD_MAGIC:
        with zstandard.ZstdDecompressor().stream_reader(io.BytesIO(raw)) as reader:
            raw = reader.read()
    return json.loads(raw)


def load(wh: Warehouse, run: RunContext, path: Path, batch_size: int = 5000) -> int:
    dataset = read_dataset(path)
    last_update = dataset.get("lastUpdate")
    dataset_date = date.fromisoformat(last_update) if last_update else None

    # Idempotência: o mesmo snapshot semanal não é carregado duas vezes.
    if (
        dataset_date
        and wh.con.execute(
            "SELECT count(*) FROM bronze.manami_anime WHERE dataset_date = ?", [dataset_date]
        ).fetchone()[0]
    ):
        log.info("snapshot manami de %s já carregado; nada a fazer", dataset_date)
        run.notes = f"skip: snapshot {dataset_date} já existe"
        return 0

    extracted_at = utcnow()
    entries = dataset.get("data", [])
    columns = ("payload", "dataset_date", "extracted_at", "run_id")
    written = 0
    for start in range(0, len(entries), batch_size):
        chunk = entries[start : start + batch_size]
        written += wh.insert_rows(
            "bronze.manami_anime",
            columns,
            [(to_json(e), dataset_date, extracted_at, run.run_id) for e in chunk],
        )
    run.add(written)
    run.notes = f"snapshot {dataset_date}: {written} entradas"
    log.info("manami: %s entradas carregadas (snapshot %s)", written, dataset_date)
    return written

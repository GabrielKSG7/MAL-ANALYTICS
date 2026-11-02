"""Roda todas as consultas de sql/consultas_dbeaver.sql contra um banco (usado no CI).

python scripts/check_sql.py data/mal_reports.duckdb
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]


def statements(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    body = "\n".join(line for line in lines if not line.strip().startswith("--"))
    return [s.strip() for s in body.split(";") if s.strip()]


def main(db: str) -> int:
    con = duckdb.connect(db, read_only=True)
    failures = 0
    stmts = statements(ROOT / "sql" / "consultas_dbeaver.sql")
    for i, sql in enumerate(stmts, start=1):
        try:
            con.execute(sql).fetchall()
        except duckdb.Error as exc:
            failures += 1
            print(f"[{i}] FALHOU: {exc}\n{sql[:300]}\n")
    print(f"{len(stmts) - failures}/{len(stmts)} consultas ok")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))

"""Confere o painel público: todo conjunto citado na página existe em data/ e é uma lista de linhas.

Uso: python scripts/check_site.py <pasta do site> [pasta de dados]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def main() -> int:
    site = Path(sys.argv[1] if len(sys.argv) > 1 else "site")
    data_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else site / "data"
    html = (site / "index.html").read_text(encoding="utf-8")
    calcs = set(re.findall(r"dash\.calc\('([\w-]+)'", html))
    sources = {s for attr in re.findall(r'data-source="([^"]+)"', html) for s in attr.split()}
    for inputs in re.findall(r"inputs:\s*\[([^\]]*)\]", html):
        sources |= set(re.findall(r"'([\w-]+)'", inputs))
    datasets = sorted(sources - calcs)
    problems = []
    for name in datasets:
        path = data_dir / f"{name}.json"
        if not path.exists():
            problems.append(f"falta {path}")
            continue
        rows = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(rows, list):
            problems.append(f"{path} não é uma lista de linhas")
    for asset in re.findall(r'(?:src|href)="(assets/[^"]+)"', html):
        if not (site / asset).exists():
            problems.append(f"falta {site / asset}")
    if not (data_dir / "meta.json").exists():
        problems.append(f"falta {data_dir / 'meta.json'}")
    for p in problems:
        print("ERRO:", p)
    print(f"{len(datasets)} conjuntos e {len(calcs)} cálculos conferidos em {data_dir}" if not problems else "")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

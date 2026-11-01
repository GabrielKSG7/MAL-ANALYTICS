"""Gera docs/data-dictionary.md a partir dos artefatos do dbt (manifest + catalog).

    cd dbt && dbt docs generate && cd .. && python scripts/gen_data_dictionary.py

Assim o dicionário nunca fica desatualizado em relação aos modelos e às descrições do YAML.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "dbt" / "target"
OUT = ROOT / "docs" / "data-dictionary.md"
LAYERS = ["staging", "intermediate", "core", "analytics", "snapshots"]


def main() -> None:
    manifest = json.loads((TARGET / "manifest.json").read_text())
    catalog = json.loads((TARGET / "catalog.json").read_text())
    tests_by_model: dict[str, list[str]] = {}
    for node in manifest["nodes"].values():
        if node["resource_type"] == "test":
            for dep in node["depends_on"]["nodes"]:
                name = node.get("test_metadata", {}).get("name") or node["name"]
                col = node.get("column_name")
                tests_by_model.setdefault(dep, []).append(f"{name}({col})" if col else name)

    lines = [
        "# Dicionário de dados",
        "",
        "> Gerado automaticamente por `scripts/gen_data_dictionary.py` a partir do manifest/catalog do dbt.",
        "",
    ]
    models = [
        n for n in manifest["nodes"].values() if n["resource_type"] in ("model", "snapshot") and n["schema"] in LAYERS
    ]
    for layer in LAYERS:
        layer_models = sorted((m for m in models if m["schema"] == layer), key=lambda m: m["name"])
        if not layer_models:
            continue
        lines += [f"## {layer}", ""]
        for m in layer_models:
            cat = catalog["nodes"].get(m["unique_id"], {})
            mat = m["config"].get("materialized", "snapshot")
            lines += [f"### `{layer}.{m['name']}` · {mat}", ""]
            desc = (m.get("description") or "").strip()
            if desc.startswith("{{"):
                desc = ""
            if desc:
                lines += [desc, ""]
            tests = sorted(set(tests_by_model.get(m["unique_id"], [])))
            if tests:
                lines += [f"Testes: {', '.join(f'`{t}`' for t in tests)}", ""]
            cols = cat.get("columns", {})
            if cols:
                lines += ["| coluna | tipo | descrição |", "|---|---|---|"]
                for col in sorted(cols.values(), key=lambda c: c["index"]):
                    doc = (m["columns"].get(col["name"], {}) or {}).get("description", "").replace("\n", " ")
                    lines.append(f"| `{col['name']}` | {col['type']} | {doc} |")
                lines.append("")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"escrito {OUT} ({len(models)} modelos)")


if __name__ == "__main__":
    main()

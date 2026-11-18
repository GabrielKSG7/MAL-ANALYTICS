"""Gera docs/lineage.md (diagramas Mermaid) a partir do manifest do dbt.

Uso: (cd dbt && dbt parse) && python scripts/gen_lineage.py

O staging é agrupado por sistema de origem (um nó por fonte); intermediate, core e analytics
aparecem modelo a modelo, até as exposures (dashboard, painel público, recomendador).
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "dbt" / "target" / "manifest.json"
OUT = ROOT / "docs" / "lineage.md"

SYSTEM_LABEL = {
    "mal": "MyAnimeList API",
    "anilist": "AniList GraphQL",
    "kitsu": "Kitsu",
    "jikan": "Jikan",
    "manami": "anime-offline-database",
    "kaggle": "Kaggle (interações)",
}


def layer_of(node: dict) -> tuple[str, str | None]:
    parts = node["original_file_path"].split("/")  # models/<layer>/[<sub>/]<file>.sql
    if parts[1] == "staging":
        return "staging", parts[2]
    if parts[1] == "intermediate":
        return "intermediate", None
    return parts[2], None  # marts/core | marts/analytics


def main() -> None:
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    models = {k: v for k, v in m["nodes"].items() if v["resource_type"] == "model"}
    node_id: dict[str, str] = {}  # unique_id -> id no diagrama
    groups: dict[str, list[str]] = defaultdict(list)
    staging_count: dict[str, int] = defaultdict(int)

    for uid, n in models.items():
        layer, system = layer_of(n)
        if layer == "staging":
            node_id[uid] = f"stg_{system}"
            staging_count[system] += 1
        else:
            node_id[uid] = n["name"]
            groups[layer].append(n["name"])
    for uid, src in m["sources"].items():
        system = src["name"].split("_")[0]  # mal_anime, anilist_media, kitsu_episodes...
        node_id[uid] = f"src_{system}"

    edges: set[tuple[str, str]] = set()
    for uid, n in list(models.items()) + list(m["exposures"].items()):
        target = node_id.get(uid) or f"exp_{n['name']}"
        for dep in n["depends_on"]["nodes"]:
            if dep in node_id and node_id[dep] != target:
                edges.add((node_id[dep], target))

    systems = sorted(staging_count)
    lines = ["flowchart LR"]
    lines.append('  subgraph Fontes["Fontes (bronze)"]')
    lines += [f'    src_{s}[("{SYSTEM_LABEL.get(s, s)}")]' for s in systems]
    lines.append("  end")
    lines.append('  subgraph Staging["Staging · views tipadas"]')
    lines += [f'    stg_{s}["{s} · {staging_count[s]} modelos"]' for s in systems]
    lines.append("  end")
    for layer, title in [("intermediate", "Intermediate"), ("core", "Core · dimensões e fatos"),
                         ("analytics", "Analytics · marts por pergunta")]:  # fmt: skip
        lines.append(f'  subgraph {layer.capitalize()}["{title}"]')
        lines += [f"    {name}" for name in sorted(groups[layer])]
        lines.append("  end")
    lines.append('  subgraph Entregas["Exposures"]')
    for e in sorted(m["exposures"].values(), key=lambda e: e["name"]):
        lines.append(f'    exp_{e["name"]}{{{{"{e.get("label") or e["name"]}"}}}}')
    lines.append("  end")
    lines += [f"  {a} --> {b}" for a, b in sorted(edges)]

    overview = ["flowchart LR"]
    overview += [f'  src_{s}[("{SYSTEM_LABEL.get(s, s)}")] --> stg["Staging · {sum(staging_count.values())} modelos"]'
                 for s in systems]  # fmt: skip
    overview += [
        f'  stg --> int["Intermediate · {len(groups["intermediate"])}"]',
        f'  int --> core["Core · {len(groups["core"])}"]',
        "  stg --> core",
        f'  core --> an["Analytics · {len(groups["analytics"])}"]',
        '  core --> rec{{"Recomendador (Python)"}}',
        '  an --> dash{{"Dashboard Streamlit"}}',
        '  an --> site{{"Painel público (GitHub Pages)"}}',
        '  an --> dbeaver{{"Cópia de consulta (DBeaver)"}}',
    ]

    OUT.write_text(
        "# Lineage\n\n"
        "> Gerado por `scripts/gen_lineage.py` a partir do manifest do dbt — não edite à mão.\n"
        "> Para o lineage interativo, modelo a modelo: `make dbt-docs`.\n\n"
        "## Visão geral\n\n```mermaid\n" + "\n".join(overview) + "\n```\n\n"
        "## Modelo a modelo\n\nStaging agrupado por fonte; da camada intermediate em diante, cada nó é um modelo.\n\n"
        "```mermaid\n" + "\n".join(lines) + "\n```\n",
        encoding="utf-8",
    )
    print(f"escrito {OUT} ({len(models)} modelos, {len(edges)} ligações)")


if __name__ == "__main__":
    main()

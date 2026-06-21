"""Generate public bibliography documentation from the literature source registry."""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Any

from glutenix.calibration.literature import DEFAULT_SOURCE_REGISTRY, load_literature_sources


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "docs" / "generated" / "bibliography.md"


def _format_authors(authors: list[str]) -> str:
    if len(authors) == 1:
        return authors[0]
    return ", ".join(authors[:-1]) + f" and {authors[-1]}"


def render_bibliography(sources: dict[str, dict[str, Any]]) -> str:
    by_domain: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for source in sources.values():
        by_domain[str(source["domain"])].append(source)

    lines = [
        "<!-- generated-start: bibliography -->",
        "# Literature Bibliography",
        "",
        "This file is generated from `data/literature/sources.json`. Do not edit it by hand.",
        "",
    ]

    for domain in sorted(by_domain):
        lines.extend([f"## {domain}", ""])
        for source in sorted(by_domain[domain], key=lambda item: (int(item["year"]), str(item["id"]))):
            authors = _format_authors([str(author) for author in source["authors"]])
            citation = f"{authors} ({source['year']}). {source['title']}."
            if source.get("venue"):
                citation += f" {source['venue']}."
            lines.append(f"- `[{source['id']}]` {citation}")
            if source.get("doi"):
                lines.append(f"  - DOI: `{source['doi']}`")
            if source.get("pmcid"):
                lines.append(f"  - PMCID: `{source['pmcid']}`")
            if source.get("url"):
                lines.append(f"  - URL: {source['url']}")
            lines.append(f"  - Records: {source['record_count']}")
            if source.get("notes"):
                lines.append(f"  - Notes: {source['notes']}")
            lines.append("")

    lines.append("<!-- generated-end: bibliography -->")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCE_REGISTRY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true", help="Fail if the generated bibliography is stale.")
    args = parser.parse_args()

    rendered = render_bibliography(load_literature_sources(args.sources))
    if args.check:
        current = args.output.read_text(encoding="utf-8") if args.output.exists() else ""
        if current != rendered:
            print("Generated bibliography is stale. Run:")
            print("  uv run python scripts/generate_bibliography.py")
            return 1
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"Updated {args.output.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

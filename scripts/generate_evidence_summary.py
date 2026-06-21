"""Generate evidence summaries from structured literature datasets."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from glutenix.calibration.literature import (
    DEFAULT_BREAD_DATASET,
    DEFAULT_PASTA_DATASET,
    DEFAULT_SOURCE_REGISTRY,
    load_literature_sources,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "docs" / "generated" / "evidence-summary.md"
EVIDENCE_MAP = PROJECT_ROOT / "docs" / "evidence-map.md"
EVIDENCE_START = "<!-- generated-start: evidence-domain-coverage -->"
EVIDENCE_END = "<!-- generated-end: evidence-domain-coverage -->"

DOMAIN_LABELS = {
    "pasta_cooking": "Pasta cooking",
    "bread_baking": "Bread baking",
}
DOMAIN_CONFIDENCE = {
    "pasta_cooking": ("`calibrated`", "Medium-high", "Add more dried/fresh pasta systems and texture data"),
    "bread_baking": ("`literature-informed`", "Medium-low", "Add more hydrocolloid/protein/fiber bread records"),
}
METRIC_LABELS = {
    "cooking_loss_pct": "Cooking loss",
    "water_absorption_pct": "water uptake",
    "swelling_index": "swelling",
    "specific_volume_cm3_g": "Specific volume",
    "crumb_hardness_n": "crumb hardness",
    "porosity_pct": "porosity",
}
STATIC_DOMAIN_ROWS = [
    "| Pizza baking | `heuristic` | 0 | 0 | Process fit, crust/core targets, blend targets | Low | Add pizza or flatbread dataset after bread |",
    "| Sweet leavened doughs | `heuristic` | 0 | 0 | Volume/process/blend targets | Low | Extract enriched dough literature later |",
    "| Shortcrust/frolla | `heuristic` | 0 | 0 | Low-volume process fit, fat/starch balance | Low | Add biscuit/shortcrust texture papers later |",
    "| Biscuits/cookies | `heuristic` | 0 | 0 | Low expansion, crispness proxies | Low | Add biscuit/cookie texture papers later |",
    "| Flavor | `heuristic` | 0 | 0 | Flavor profile proxy | Low | Needs sensory panel literature or internal tests |",
    "| Nutrition | `literature-informed` | Seed data | Mixed source values | Macro estimates | Medium for approximate labels | Needs source-level ingredient provenance |",
]


def _dataset_paths() -> dict[str, Path]:
    return {
        "pasta_cooking": DEFAULT_PASTA_DATASET,
        "bread_baking": DEFAULT_BREAD_DATASET,
    }


def load_dataset_summary() -> dict[str, dict[str, Any]]:
    sources = load_literature_sources(DEFAULT_SOURCE_REGISTRY)
    source_domains = {source_id: source["domain"] for source_id, source in sources.items()}
    summary: dict[str, dict[str, Any]] = {}

    for domain, path in _dataset_paths().items():
        records = []
        metrics: Counter[str] = Counter()
        ingredients: Counter[str] = Counter()
        process_fields: Counter[str] = Counter()
        source_counts: Counter[str] = Counter()

        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                source_id = record["source_id"]
                if source_domains[source_id] != domain:
                    raise ValueError(f"source_id {source_id!r} belongs to {source_domains[source_id]!r}, not {domain!r}")
                records.append(record)
                metrics.update(record.get("measured", {}).keys())
                ingredients.update(record.get("mapped_formula", {}).keys())
                process_fields.update(record.get("process", {}).keys())
                source_counts[source_id] += 1

        summary[domain] = {
            "record_count": len(records),
            "source_count": len(source_counts),
            "metrics": dict(sorted(metrics.items())),
            "ingredients": dict(sorted(ingredients.items())),
            "process_fields": dict(sorted(process_fields.items())),
            "source_counts": dict(sorted(source_counts.items())),
        }
    return summary


def _main_metrics(domain: str, metrics: dict[str, int]) -> str:
    preferred = {
        "pasta_cooking": ["cooking_loss_pct", "water_absorption_pct", "swelling_index"],
        "bread_baking": ["specific_volume_cm3_g", "crumb_hardness_n", "porosity_pct"],
    }[domain]
    return ", ".join(METRIC_LABELS[metric] for metric in preferred if metric in metrics)


def render_evidence_map_block(summary: dict[str, dict[str, Any]]) -> str:
    lines = [
        EVIDENCE_START,
        "| Domain | Current Evidence | Records | Sources | Main Metrics | Current Confidence | Next Priority |",
        "|---|---:|---:|---:|---|---|---|",
    ]
    for domain in ("pasta_cooking", "bread_baking"):
        data = summary[domain]
        evidence, confidence, priority = DOMAIN_CONFIDENCE[domain]
        lines.append(
            "| "
            f"{DOMAIN_LABELS[domain]} | {evidence} | {data['record_count']} | {data['source_count']} | "
            f"{_main_metrics(domain, data['metrics'])} | {confidence} | {priority} |"
        )
    lines.extend(STATIC_DOMAIN_ROWS)
    lines.append(EVIDENCE_END)
    return "\n".join(lines)


def render_generated_summary(summary: dict[str, dict[str, Any]]) -> str:
    lines = [
        "<!-- generated-start: evidence-summary -->",
        "# Generated Evidence Summary",
        "",
        "This file is generated from `data/literature/sources.json` and `data/literature/*.jsonl`. Do not edit it by hand.",
        "",
        "## Domain Summary",
        "",
        "| Domain | Records | Sources | Metrics | Ingredients | Process Fields |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for domain, data in sorted(summary.items()):
        lines.append(
            f"| `{domain}` | {data['record_count']} | {data['source_count']} | "
            f"{len(data['metrics'])} | {len(data['ingredients'])} | {len(data['process_fields'])} |"
        )

    lines.extend(["", "## Metric Coverage", ""])
    for domain, data in sorted(summary.items()):
        lines.extend([f"### {domain}", "", "| Metric | Records |", "|---|---:|"])
        for metric, count in data["metrics"].items():
            lines.append(f"| `{metric}` | {count} |")
        lines.append("")

    lines.extend(["## Source Counts", ""])
    for domain, data in sorted(summary.items()):
        lines.extend([f"### {domain}", "", "| Source ID | Records |", "|---|---:|"])
        for source_id, count in data["source_counts"].items():
            lines.append(f"| `{source_id}` | {count} |")
        lines.append("")

    lines.append("<!-- generated-end: evidence-summary -->")
    return "\n".join(lines) + "\n"


def _replace_block(document: str, start: str, end: str, replacement: str) -> str:
    start_index = document.find(start)
    end_index = document.find(end)
    if start_index == -1 or end_index == -1 or end_index < start_index:
        raise ValueError(f"Could not find generated block markers: {start} / {end}")
    end_index += len(end)
    return document[:start_index] + replacement + document[end_index:]


def planned_outputs() -> dict[Path, str]:
    summary = load_dataset_summary()
    evidence_map = EVIDENCE_MAP.read_text(encoding="utf-8")
    return {
        DEFAULT_OUTPUT: render_generated_summary(summary),
        EVIDENCE_MAP: _replace_block(
            evidence_map,
            EVIDENCE_START,
            EVIDENCE_END,
            render_evidence_map_block(summary),
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if generated evidence docs are stale.")
    args = parser.parse_args()

    outputs = planned_outputs()
    if args.check:
        stale = [path for path, rendered in outputs.items() if not path.exists() or path.read_text(encoding="utf-8") != rendered]
        if stale:
            print("Generated evidence docs are stale. Run:")
            print("  uv run python scripts/generate_evidence_summary.py")
            for path in stale:
                print(f"  stale: {path.relative_to(PROJECT_ROOT)}")
            return 1
        return 0

    for path, rendered in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")
        print(f"Updated {path.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

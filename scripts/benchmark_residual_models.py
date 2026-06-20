"""Run and report ML residual model benchmarks for heuristic simulators.

Produces diagnostic tables comparing heuristic-only accuracy against
ridge + RandomForest residual corrections under leave-one-source-out CV.

Usage:
    uv run python scripts/benchmark_residual_models.py [--check]
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from glutenix.db.base import Base
from glutenix.db.seed import _seed_applications, _seed_ingredients
from glutenix.ml.residual import (
    BenchmarkResult,
    benchmark_bread,
    benchmark_pasta,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = PROJECT_ROOT / "docs" / "ml-residual-benchmark.md"

REPORT_START = "<!-- generated-start: ml-residual-benchmark -->"
REPORT_END = "<!-- generated-end: ml-residual-benchmark -->"


def _seeded_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    _seed_ingredients(session)
    _seed_applications(session)
    session.commit()
    return session


def _improvement_label(imp: float | None) -> str:
    if imp is None:
        return "—"
    if imp > 0:
        return f"**+{imp:.1f}%**"
    if imp < 0:
        return f"{imp:.1f}%"
    return "0.0%"


def _format_metrics(m: Any) -> str:
    if m is None:
        return "—"
    return f"MAE={m.mae:.4f}, RMSE={m.rmse:.4f}, R²={m.r2:.4f}, bias={m.bias:+.4f}"


def _metric_row(
    domain: str, metric: str, result: BenchmarkResult | None
) -> str | None:
    if result is None:
        return None
    row = (
        f"| {domain} | `{metric}` | {result.n_records} | {result.n_sources} | "
        f"{result.heuristic_overall.mae:.4f} | "
    )
    if result.ridge_overall:
        row += (
            f"{result.ridge_overall.mae:.4f} | "
            f"{_improvement_label(result.ridge_improvement_pct)} | "
        )
    else:
        row += "— | — | "
    if result.rf_overall:
        row += (
            f"{result.rf_overall.mae:.4f} | "
            f"{_improvement_label(result.rf_improvement_pct)} |"
        )
    else:
        row += "— | — |"
    return row


def _fold_rows(result: BenchmarkResult) -> list[list[str]]:
    """Build per-fold table rows."""
    rows: list[list[str]] = []
    for fold in result.source_folds:
        rows.append([
            f"`{fold.source}`",
            str(fold.n_train),
            str(fold.n_test),
            _format_metric_cell(fold.heuristic_metrics),
            _format_metric_cell(fold.ridge_metrics),
            _format_metric_cell(fold.rf_metrics),
        ])
    return rows


def _format_metric_cell(m: Any) -> str:
    if m is None:
        return "—"
    return f"MAE={m.mae:.4f}"


def _render_report(bread_results: list[BenchmarkResult], pasta_results: list[BenchmarkResult]) -> str:
    """Build full markdown report between markers."""
    lines: list[str] = [
        REPORT_START,
        "# ML Residual Model Benchmark Report",
        "",
        f"Date: {date.today().isoformat()}",
        "",
        "## Summary",
        "",
        "Classical ML models (ridge, RandomForest) trained on heuristic simulator residuals. "
        "All metrics use **leave-one-source-out cross-validation** to estimate "
        "generalization to unseen literature sources.",
        "",
        "| Domain | Metric | Records | Sources | Heuristic MAE | Ridge MAE | Ridge Δ | RF MAE | RF Δ |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for br in bread_results:
        row = _metric_row("bread", br.metric, br)
        if row:
            lines.append(row)
    for pr in pasta_results:
        row = _metric_row("pasta", pr.metric, pr)
        if row:
            lines.append(row)

    lines.append("")
    lines.append("## Bread: Specific Volume")
    _append_metric_detail(lines, _find_result(bread_results, "specific_volume_cm3_g"))

    lines.append("## Bread: Crumb Hardness")
    _append_metric_detail(lines, _find_result(bread_results, "crumb_hardness_n"))

    lines.append("## Bread: Porosity")
    _append_metric_detail(lines, _find_result(bread_results, "porosity_pct"))

    lines.append("## Pasta: Cooking Loss")
    _append_metric_detail(lines, _find_result(pasta_results, "cooking_loss_pct"))

    lines.append("## Limitations")
    lines.append("")
    lines.append("- Ridge and RandomForest residual correction is **diagnostic only**.")
    lines.append("- Leave-one-source-out CV is a strong generalization test; small source counts limit model capacity.")
    lines.append("- Feature vectors include blend composition + process parameters, not all possible confounders.")
    lines.append("- No DL model is tested; scoped out until more records exist.")
    lines.append("- These results inform the decision whether to integrate ML residual correction into production simulation.")
    lines.append("- If integrated, correction must be gated by coverage/confidence to avoid extrapolation failure.")
    lines.append("")

    lines.append(REPORT_END)
    return "\n".join(lines)


def _append_metric_detail(lines: list[str], result: BenchmarkResult | None) -> None:
    if result is None:
        lines.extend(["", "No records available.", ""])
        return

    lines.extend([
        "",
        f"**Records**: {result.n_records} &nbsp; **Sources**: {result.n_sources}",
        "",
        "| Stage | MAE | RMSE | R² | Bias |",
        "|---|---:|---:|---:|---:|",
        f"| Heuristic only | {result.heuristic_overall.mae:.4f} | {result.heuristic_overall.rmse:.4f} | {result.heuristic_overall.r2:.4f} | {result.heuristic_overall.bias:+.4f} |",
    ])
    if result.ridge_overall:
        lines.append(
            f"| + Ridge residual | {result.ridge_overall.mae:.4f} | {result.ridge_overall.rmse:.4f} | {result.ridge_overall.r2:.4f} | {result.ridge_overall.bias:+.4f} |"
        )
    if result.rf_overall:
        lines.append(
            f"| + RF residual | {result.rf_overall.mae:.4f} | {result.rf_overall.rmse:.4f} | {result.rf_overall.r2:.4f} | {result.rf_overall.bias:+.4f} |"
        )
    lines.append("")

    # Per-fold breakdown
    fold_rows = _fold_rows(result)
    lines.extend([
        "**Leave-one-source-out folds**:",
        "",
        "| Held-out source | Train | Test | Heuristic | +Ridge | +RF |",
        "|---|---:|---:|:---|---:|:---:|",
    ])
    for fr in fold_rows:
        lines.append("| " + " | ".join(fr) + " |")
    lines.append("")


def _find_result(results: list[BenchmarkResult], metric: str) -> BenchmarkResult | None:
    for r in results:
        if r.metric == metric:
            return r
    return None


def run_benchmarks() -> tuple[list[BenchmarkResult], list[BenchmarkResult]]:
    session = _seeded_session()
    try:
        bread_results = benchmark_bread(session)
        pasta_results = benchmark_pasta(session)
    finally:
        session.close()
    return bread_results, pasta_results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if report is stale.")
    args = parser.parse_args()

    bread_results, pasta_results = run_benchmarks()

    # Print console summary
    print("=" * 72)
    print("ML Residual Model Benchmark")
    print("=" * 72)
    for br in bread_results + pasta_results:
        domain_metric = f"{br.domain}/{br.metric}"
        print(f"\n{domain_metric} ({br.n_records} records, {br.n_sources} sources)")
        print(f"  Heuristic:   {_format_metrics(br.heuristic_overall)}")
        if br.ridge_overall:
            print(f"  +Ridge:      {_format_metrics(br.ridge_overall)}  ({_improvement_label(br.ridge_improvement_pct)} MAE)")
        if br.rf_overall:
            print(f"  +RF:         {_format_metrics(br.rf_overall)}  ({_improvement_label(br.rf_improvement_pct)} MAE)")

    # Render markdown
    report = _render_report(bread_results, pasta_results)

    if args.check:
        if REPORT_PATH.exists():
            current = REPORT_PATH.read_text(encoding="utf-8")
            if current == report:
                print("\nReport is up to date.")
                return 0
        print("\nReport is stale. Run without --check to update.")
        return 1

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"\nReport written to {REPORT_PATH.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

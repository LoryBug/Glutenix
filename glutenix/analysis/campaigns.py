from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

from glutenix.cli import (
    APPLICATION_PRESETS,
    APPLICATION_PRESET_PROCESS_BOUNDS,
    IngredientBound,
    ProcessBounds,
    rank_application_candidates,
)


SPEC_VERSION = "digital-campaigns-v1"


@dataclass(frozen=True)
class SweepAxis:
    name: str
    values: tuple[str, ...]
    control_status: str
    notes: str


@dataclass(frozen=True)
class CampaignVariant:
    label: str
    family: str
    preset: str
    seed: int
    process_bounds: ProcessBounds
    sweep_values: dict[str, str]
    bounds: tuple[IngredientBound, ...] | None = None
    n_blend_samples: int = 80
    n_process_samples: int = 16
    top: int = 8
    notes: str = ""


@dataclass(frozen=True)
class CampaignSpec:
    slug: str
    title: str
    application: str
    sweep_axes: tuple[SweepAxis, ...]
    variants: tuple[CampaignVariant, ...]
    gap_notes: tuple[str, ...]
    output_requirements: tuple[str, ...]


def campaign_specs(*, sample_mode: str = "default") -> dict[str, CampaignSpec]:
    if sample_mode not in {"default", "dry-run"}:
        raise ValueError("sample_mode must be 'default' or 'dry-run'")
    samples = (12, 5, 3) if sample_mode == "dry-run" else (80, 16, 8)
    return {
        "bread": _bread_campaign(*samples),
        "pasta": _pasta_campaign(*samples),
        "pizza": _pizza_campaign(*samples),
    }


def planned_campaign_outputs(
    *,
    output_dir: Path,
    report_date: str | None = None,
    campaign: str = "all",
    sample_mode: str = "default",
) -> dict[Path, str]:
    specs = campaign_specs(sample_mode=sample_mode)
    selected = specs.values() if campaign == "all" else [specs[campaign]]
    date_text = report_date or date.today().isoformat()
    return {
        output_dir / f"{spec.slug}-{date_text}.md": render_campaign_report(spec, report_date=date_text)
        for spec in selected
    }


def render_campaign_report(spec: CampaignSpec, *, report_date: str | None = None) -> str:
    date_text = report_date or date.today().isoformat()
    rows = _run_campaign_rows(spec)
    confidence_counts = Counter(_confidence_summary(row) for row in rows)
    risk_counts = Counter(flag for row in rows for flag in _risk_flags(row))
    coverage_fractions = [
        row["coverage_diagnostics"]["coverage_fraction"]
        for row in rows
        if row.get("coverage_diagnostics") is not None
    ]
    families = _family_summaries(rows)
    robust = [family for family in families if family["robust"]]

    lines = [
        f"# {spec.title} Campaign ({date_text})",
        "",
        "This is a reproducible digital screening report. It is not experimental validation and it is not a recipe instruction.",
        "",
        "## Reproducibility",
        "",
        f"- Specification format: `{SPEC_VERSION}` Python dataclasses in `glutenix.analysis.campaigns`.",
        f"- Re-run command: `uv run python scripts/run_digital_campaigns.py --campaign {spec.slug} --date {date_text}`",
        f"- Application: `{spec.application}`",
        f"- Candidate rows analyzed: {len(rows)}",
        "- Ranking path: existing application-aware optimizer; candidates are grouped into formulation families for interpretation.",
        "",
        "## Campaign Parameters",
        "",
        "| Axis | Values | Control Status | Notes |",
        "|---|---|---|---|",
    ]
    for axis in spec.sweep_axes:
        lines.append(
            f"| `{axis.name}` | {', '.join(axis.values)} | `{axis.control_status}` | {axis.notes} |"
        )

    lines.extend([
        "",
        "## Variant Runs",
        "",
        "| Variant | Family | Preset | Seed | Blend Samples | Process Samples | Top N | Process Bounds | Sweep Values |",
        "|---|---|---|---:|---:|---:|---:|---|---|",
    ])
    for variant in spec.variants:
        lines.append(
            "| "
            f"{variant.label} | {variant.family} | `{variant.preset}` | {variant.seed} | "
            f"{variant.n_blend_samples} | {variant.n_process_samples} | {variant.top} | "
            f"{_format_process_bounds(variant.process_bounds)} | {_format_mapping(variant.sweep_values)} |"
        )

    lines.extend([
        "",
        "## Robust Formulation Families",
        "",
        "Families are marked as robust only when the top sampled candidates are comparatively stable: mean score >= 0.55, score standard deviation <= 0.12, and OOD fraction <= 0.35. This is a screening stability rule, not a quality claim.",
        "",
    ])
    if robust:
        lines.extend([
            "| Family | Variants | Candidates | Mean Score | Score Range | Dominant Confidence | OOD Fraction | Mean Water Absorption | Mean Hydrocolloid | Interpretation |",
            "|---|---|---:|---:|---|---|---:|---:|---|",
        ])
        for family in robust:
            lines.append(_family_table_row(family))
    else:
        lines.append("No robust formulation families were identified under the screening stability rule.")

    lines.extend([
        "",
        "## Risk Pattern Analysis",
        "",
        "| Risk Signal | Count |",
        "|---|---:|",
    ])
    if risk_counts:
        for flag, count in risk_counts.most_common(12):
            lines.append(f"| {flag} | {count} |")
    else:
        lines.append("| No structured risk flags among retained candidates | 0 |")

    lines.extend([
        "",
        "## Coverage Diagnostics",
        "",
        "| Confidence Summary | Candidates | Share |",
        "|---|---:|---:|",
    ])
    total = max(1, len(rows))
    for label, count in sorted(confidence_counts.items()):
        lines.append(f"| `{label}` | {count} | {count / total:.1%} |")
    if coverage_fractions:
        lines.extend([
            "",
            f"Pizza V1 audit-boundary coverage fraction: mean {mean(coverage_fractions):.2f}, range {min(coverage_fractions):.2f}-{max(coverage_fractions):.2f}.",
        ])

    lines.extend([
        "",
        "## Gap Notes",
        "",
    ])
    for note in spec.gap_notes:
        lines.append(f"- {note}")

    lines.extend([
        "",
        "## Supporting Candidate Patterns",
        "",
        "| Variant | Rank | Score | Confidence | Water Absorption | Hydrocolloid | Main Ingredients |",
        "|---|---:|---:|---|---:|---:|---|",
    ])
    for row in rows[: min(18, len(rows))]:
        ingredients = _top_ingredients(row["proportions"])
        properties = row["properties"]
        lines.append(
            "| "
            f"{row['variant']} | {row['rank']} | {row['score']:.4f} | `{_confidence_summary(row)}` | "
            f"{properties.get('water_absorption', 0.0):.3f} | "
            f"{properties.get('hydrocolloid_pct', 0.0):.4f} | {ingredients} |"
        )

    lines.extend([
        "",
        "## Output Requirements Check",
        "",
    ])
    for requirement in spec.output_requirements:
        lines.append(f"- {requirement}")

    return "\n".join(lines) + "\n"


def _run_campaign_rows(spec: CampaignSpec) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for variant in spec.variants:
        bounds = list(variant.bounds or tuple(APPLICATION_PRESETS[variant.preset]))
        result = rank_application_candidates(
            application=spec.application,
            bounds=bounds,
            n_blend_samples=variant.n_blend_samples,
            n_process_samples=variant.n_process_samples,
            top=variant.top,
            seed=variant.seed,
            process_bounds=variant.process_bounds,
        )
        for candidate in result.candidates:
            data = candidate.model_dump()
            data["campaign"] = spec.slug
            data["variant"] = variant.label
            data["family"] = variant.family
            data["preset"] = variant.preset
            rows.append(data)
    rows.sort(key=lambda row: (row["campaign"], row["variant"], row["rank"]))
    return rows


def _family_summaries(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["family"]].append(row)

    summaries = []
    for family, items in sorted(grouped.items()):
        scores = [row["score"] for row in items]
        confidence = Counter(_confidence_summary(row) for row in items)
        ood_fraction = confidence.get("ood_extrapolation", 0) / len(items)
        score_std = pstdev(scores) if len(scores) > 1 else 0.0
        mean_score = mean(scores)
        robust = mean_score >= 0.55 and score_std <= 0.12 and ood_fraction <= 0.35
        summaries.append({
            "family": family,
            "variants": sorted({row["variant"] for row in items}),
            "candidate_count": len(items),
            "mean_score": mean_score,
            "score_min": min(scores),
            "score_max": max(scores),
            "score_std": score_std,
            "dominant_confidence": confidence.most_common(1)[0][0],
            "ood_fraction": ood_fraction,
            "mean_water_absorption": mean(row["properties"].get("water_absorption", 0.0) for row in items),
            "mean_hydrocolloid": mean(row["properties"].get("hydrocolloid_pct", 0.0) for row in items),
            "robust": robust,
        })
    return summaries


def _family_table_row(family: dict[str, Any]) -> str:
    interpretation = "Stable digital family for follow-up interpretation; still requires physical testing."
    return (
        "| "
        f"{family['family']} | {', '.join(family['variants'])} | {family['candidate_count']} | "
        f"{family['mean_score']:.3f} | {family['score_min']:.3f}-{family['score_max']:.3f} | "
        f"`{family['dominant_confidence']}` | {family['ood_fraction']:.1%} | "
        f"{family['mean_water_absorption']:.3f} | {family['mean_hydrocolloid']:.4f} | {interpretation} |"
    )


def _confidence_summary(row: dict[str, Any]) -> str:
    return row["model_confidence"].get("confidence_summary", "unknown")


def _risk_flags(row: dict[str, Any]) -> list[str]:
    flags = list(row["model_confidence"].get("risk_flags", []))
    coverage = row.get("coverage_diagnostics")
    if coverage:
        flags.extend(coverage.get("risk_flags", []))
    return flags


def _format_process_bounds(bounds: ProcessBounds) -> str:
    values = {
        "ferm_temp_c": bounds.fermentation_temp_c,
        "ferm_min": bounds.fermentation_duration_min,
        "bake_temp_c": bounds.baking_temp_c,
        "bake_min": bounds.baking_duration_min,
    }
    return _format_mapping({key: f"{lo:g}-{hi:g}" for key, (lo, hi) in values.items()})


def _format_mapping(values: dict[str, str]) -> str:
    return "; ".join(f"`{key}`={value}" for key, value in values.items())


def _top_ingredients(proportions: dict[str, float], *, limit: int = 3) -> str:
    items = sorted(proportions.items(), key=lambda item: item[1], reverse=True)[:limit]
    return ", ".join(f"{name} {value:.1%}" for name, value in items)


def _bread_campaign(n_blend_samples: int, n_process_samples: int, top: int) -> CampaignSpec:
    variants = (
        CampaignVariant(
            label="bread-sorghum-short-fermentation",
            family="sorghum-rice hydrocolloid bread",
            preset="sorghum-baseline",
            seed=8801,
            process_bounds=ProcessBounds(fermentation_duration_min=(120.0, 120.0)),
            sweep_values={"flour_family": "sorghum-rice", "fermentation_duration_min": "120", "hydration_proxy": "water_absorption"},
            n_blend_samples=n_blend_samples,
            n_process_samples=n_process_samples,
            top=top,
        ),
        CampaignVariant(
            label="bread-commercial-mid-fermentation",
            family="starch-protein commercial-style bread",
            preset="bobs-inspired",
            seed=8802,
            process_bounds=ProcessBounds(fermentation_duration_min=(150.0, 150.0)),
            sweep_values={"flour_family": "sorghum-potato-corn", "fermentation_duration_min": "150", "hydration_proxy": "water_absorption"},
            n_blend_samples=n_blend_samples,
            n_process_samples=n_process_samples,
            top=top,
        ),
        CampaignVariant(
            label="bread-rice-long-fermentation",
            family="rice-corn psyllium bread",
            preset="schaer-inspired",
            seed=8803,
            process_bounds=ProcessBounds(fermentation_duration_min=(180.0, 180.0)),
            sweep_values={"flour_family": "rice-corn", "fermentation_duration_min": "180", "hydration_proxy": "water_absorption"},
            n_blend_samples=n_blend_samples,
            n_process_samples=n_process_samples,
            top=top,
        ),
    )
    return CampaignSpec(
        slug="bread",
        title="Bread Digital",
        application="Pane",
        sweep_axes=(
            SweepAxis("flour_family", ("sorghum-rice", "sorghum-potato-corn", "rice-corn"), "engine_controlled", "Implemented through ingredient-bound presets."),
            SweepAxis("fermentation_duration_min", ("120", "150", "180"), "engine_controlled", "Fixed per variant to isolate duration effects."),
            SweepAxis("hydration_proxy", ("water_absorption",), "analyzed_output", "The current engine has no dough-water addition input; hydration is tracked through blend water absorption."),
        ),
        variants=variants,
        gap_notes=(
            "Bread campaigns use calibrated bread-quality curves where available, but retained families are still digital hypotheses.",
            "Dough hydration is represented by model-derived water absorption rather than an explicit added-water percentage.",
        ),
        output_requirements=(
            "Campaign parameters, sweep ranges, and seeds are listed above.",
            "Families and risk patterns are reported without directive formulation language.",
            "Coverage distribution comes from structured candidate confidence summaries.",
        ),
    )


def _pasta_campaign(n_blend_samples: int, n_process_samples: int, top: int) -> CampaignSpec:
    baseline = tuple(APPLICATION_PRESETS["pasta-rice-structure-v1"])
    higher_protein = tuple(
        replace(bound, min_proportion=0.06, max_proportion=0.10)
        if bound.name == "Soy protein isolate" else bound
        for bound in baseline
    )
    higher_gel = tuple(
        replace(bound, min_proportion=0.012, max_proportion=0.022)
        if bound.name in {"Sodium alginate", "Konjac glucomannan", "Curdlan"} else bound
        for bound in baseline
    )
    variants = (
        CampaignVariant(
            label="pasta-rice-calcium-baseline",
            family="rice-alginate fresh pasta",
            preset="pasta-rice-structure-v1",
            seed=8811,
            process_bounds=ProcessBounds(baking_temp_c=(100.0, 100.0), baking_duration_min=(8.0, 8.0)),
            sweep_values={"hydration_proxy": "water_absorption", "egg_ratio": "0", "drying_assumption": "fresh_calcium_gel"},
            bounds=baseline,
            n_blend_samples=n_blend_samples,
            n_process_samples=n_process_samples,
            top=top,
        ),
        CampaignVariant(
            label="pasta-higher-protein",
            family="soy-supported rice pasta",
            preset="pasta-rice-structure-v1",
            seed=8812,
            process_bounds=ProcessBounds(baking_temp_c=(100.0, 100.0), baking_duration_min=(10.0, 10.0)),
            sweep_values={"hydration_proxy": "water_absorption", "egg_ratio": "0", "drying_assumption": "fresh_calcium_gel"},
            bounds=higher_protein,
            n_blend_samples=n_blend_samples,
            n_process_samples=n_process_samples,
            top=top,
        ),
        CampaignVariant(
            label="pasta-higher-gel-network",
            family="alginate-kgm-curdlan rice pasta",
            preset="pasta-rice-structure-v1",
            seed=8813,
            process_bounds=ProcessBounds(baking_temp_c=(100.0, 100.0), baking_duration_min=(12.0, 12.0)),
            sweep_values={"hydration_proxy": "water_absorption", "egg_ratio": "0", "drying_assumption": "fresh_calcium_gel"},
            bounds=higher_gel,
            n_blend_samples=n_blend_samples,
            n_process_samples=n_process_samples,
            top=top,
        ),
    )
    return CampaignSpec(
        slug="pasta",
        title="Pasta Digital",
        application="Pasta fresca",
        sweep_axes=(
            SweepAxis("hydration_proxy", ("water_absorption",), "analyzed_output", "The pasta ranking path tracks hydration through blend water absorption and calcium-gel process parameters."),
            SweepAxis("egg_ratio", ("0",), "documented_gap", "No seeded egg ingredient or egg-pasta calibration exists; this campaign holds egg ratio at zero."),
            SweepAxis("drying_assumption", ("fresh_calcium_gel",), "documented_gap", "The executable application preset models fresh calcium-gel pasta, not dried extrusion."),
            SweepAxis("cooking_time_min", ("8", "10", "12"), "engine_controlled", "Mapped through the application process duration field."),
        ),
        variants=variants,
        gap_notes=(
            "No whole-egg ingredient or egg-pasta calibration is available in current seed/literature data.",
            "Dried pasta assumptions are documented as a gap because the executable preset is fresh calcium-gel pasta only.",
            "Whole-grain pasta support remains limited to current rice/soy/alginate/KGM/curdlan evidence.",
        ),
        output_requirements=(
            "Campaign parameters, sweep ranges, and seeds are listed above.",
            "Risk patterns include explicit unsupported egg and drying assumptions.",
            "Coverage distribution comes from structured candidate confidence summaries.",
        ),
    )


def _pizza_campaign(n_blend_samples: int, n_process_samples: int, top: int) -> CampaignSpec:
    baseline = tuple(APPLICATION_PRESETS["pizza-v1"])
    hpmc_supported = tuple(
        replace(bound, min_proportion=0.008, max_proportion=0.015)
        if bound.name == "HPMC (Hydroxypropyl Methylcellulose)" else
        replace(bound, min_proportion=0.0, max_proportion=0.002)
        if bound.name == "Xanthan gum" else bound
        for bound in baseline
    )
    xanthan_supported = tuple(
        replace(bound, min_proportion=0.003, max_proportion=0.005)
        if bound.name == "Xanthan gum" else
        replace(bound, min_proportion=0.0, max_proportion=0.006)
        if bound.name == "HPMC (Hydroxypropyl Methylcellulose)" else bound
        for bound in baseline
    )
    pizza_bounds = APPLICATION_PRESET_PROCESS_BOUNDS["pizza-v1"]
    variants = (
        CampaignVariant(
            label="pizza-v1-baseline",
            family="rice-sorghum-starch pizza v1",
            preset="pizza-v1",
            seed=8821,
            process_bounds=pizza_bounds,
            sweep_values={"hydrocolloid_system": "psyllium-hpmc-xanthan", "audit_boundary": "strict"},
            bounds=baseline,
            n_blend_samples=n_blend_samples,
            n_process_samples=n_process_samples,
            top=top,
        ),
        CampaignVariant(
            label="pizza-v1-hpmc-supported",
            family="hpmc-supported pizza v1",
            preset="pizza-v1",
            seed=8822,
            process_bounds=pizza_bounds,
            sweep_values={"hydrocolloid_system": "psyllium-hpmc", "audit_boundary": "strict"},
            bounds=hpmc_supported,
            n_blend_samples=n_blend_samples,
            n_process_samples=n_process_samples,
            top=top,
        ),
        CampaignVariant(
            label="pizza-v1-xanthan-supported",
            family="xanthan-supported pizza v1",
            preset="pizza-v1",
            seed=8823,
            process_bounds=pizza_bounds,
            sweep_values={"hydrocolloid_system": "psyllium-xanthan", "audit_boundary": "strict"},
            bounds=xanthan_supported,
            n_blend_samples=n_blend_samples,
            n_process_samples=n_process_samples,
            top=top,
        ),
    )
    return CampaignSpec(
        slug="pizza",
        title="Pizza V1 Digital",
        application="Pizza",
        sweep_axes=(
            SweepAxis("hydrocolloid_system", ("psyllium-hpmc-xanthan", "psyllium-hpmc", "psyllium-xanthan"), "engine_controlled", "All variants use only Pizza V1 audited ingredient families."),
            SweepAxis("fermentation_temp_c", ("37",), "audit_fixed", "Fixed to the Dey GF pizza anchor used by Pizza V1."),
            SweepAxis("fermentation_duration_min", ("120",), "audit_fixed", "Fixed to the Pizza V1 audit boundary."),
            SweepAxis("baking_temp_c", ("204.4",), "audit_fixed", "Fixed to the Pizza V1 audit boundary."),
            SweepAxis("baking_duration_min", ("10",), "audit_fixed", "Fixed to the Pizza V1 audit boundary."),
        ),
        variants=variants,
        gap_notes=(
            "Pizza V1 has audit-boundary diagnostics only; no structured pizza_baking JSONL calibration dataset exists.",
            "Lentil flour remains documented in the audit but outside the executable preset until a seeded ingredient exists.",
            "Cold fermentation, sourdough, high-temperature Neapolitan baking, and unsupported proteins are intentionally outside this campaign.",
        ),
        output_requirements=(
            "Campaign parameters, sweep ranges, and seeds are listed above.",
            "All process values are fixed within the Pizza V1 audit boundary.",
            "Coverage distribution includes Pizza V1 audit-boundary coverage fractions.",
        ),
    )

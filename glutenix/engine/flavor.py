from dataclasses import dataclass

import math

from glutenix.db.models import Ingredient


FLAVOR_DIMENSIONS = (
    "neutral",
    "cereal",
    "nutty",
    "earthy",
    "bitter",
    "sweet",
    "toasted",
    "rich",
)


@dataclass(frozen=True)
class FlavorTarget:
    name: str
    profile: dict[str, float]
    sigma: float = 0.35
    evidence_level: str = "heuristic"
    rationale: str = "Literature-informed sensory proxy; not calibrated with panel tests."
    sources: tuple[str, ...] = (
        "docs/flavor-heuristic-model.md",
        "docs/application-targets-research.md",
    )


INGREDIENT_FLAVOR_PROFILES: dict[str, dict[str, float]] = {
    "white rice flour": {
        "neutral": 0.90, "cereal": 0.25, "nutty": 0.05, "earthy": 0.03,
        "bitter": 0.02, "sweet": 0.15, "toasted": 0.10, "rich": 0.05,
    },
    "brown rice flour": {
        "neutral": 0.72, "cereal": 0.45, "nutty": 0.18, "earthy": 0.15,
        "bitter": 0.05, "sweet": 0.15, "toasted": 0.18, "rich": 0.10,
    },
    "buckwheat flour": {
        "neutral": 0.22, "cereal": 0.55, "nutty": 0.55, "earthy": 0.70,
        "bitter": 0.22, "sweet": 0.10, "toasted": 0.35, "rich": 0.28,
    },
    "sorghum flour": {
        "neutral": 0.58, "cereal": 0.65, "nutty": 0.28, "earthy": 0.18,
        "bitter": 0.08, "sweet": 0.18, "toasted": 0.28, "rich": 0.16,
    },
    "teff flour": {
        "neutral": 0.35, "cereal": 0.62, "nutty": 0.35, "earthy": 0.45,
        "bitter": 0.12, "sweet": 0.15, "toasted": 0.45, "rich": 0.22,
    },
    "almond flour": {
        "neutral": 0.25, "cereal": 0.10, "nutty": 0.95, "earthy": 0.10,
        "bitter": 0.04, "sweet": 0.35, "toasted": 0.40, "rich": 0.90,
    },
    "millet flour": {
        "neutral": 0.58, "cereal": 0.58, "nutty": 0.20, "earthy": 0.15,
        "bitter": 0.10, "sweet": 0.20, "toasted": 0.22, "rich": 0.12,
    },
    "oat flour (gf)": {
        "neutral": 0.62, "cereal": 0.60, "nutty": 0.35, "earthy": 0.10,
        "bitter": 0.04, "sweet": 0.35, "toasted": 0.32, "rich": 0.25,
    },
    "quinoa flour": {
        "neutral": 0.32, "cereal": 0.48, "nutty": 0.22, "earthy": 0.28,
        "bitter": 0.30, "sweet": 0.08, "toasted": 0.20, "rich": 0.16,
    },
    "tapioca starch": {
        "neutral": 0.95, "cereal": 0.05, "nutty": 0.02, "earthy": 0.02,
        "bitter": 0.01, "sweet": 0.08, "toasted": 0.04, "rich": 0.02,
    },
    "potato starch": {
        "neutral": 0.90, "cereal": 0.04, "nutty": 0.02, "earthy": 0.08,
        "bitter": 0.02, "sweet": 0.05, "toasted": 0.03, "rich": 0.02,
    },
    "corn starch": {
        "neutral": 0.86, "cereal": 0.16, "nutty": 0.05, "earthy": 0.03,
        "bitter": 0.02, "sweet": 0.12, "toasted": 0.08, "rich": 0.04,
    },
    "sweet rice flour (mochiko)": {
        "neutral": 0.88, "cereal": 0.22, "nutty": 0.04, "earthy": 0.03,
        "bitter": 0.01, "sweet": 0.22, "toasted": 0.08, "rich": 0.05,
    },
    "xanthan gum": {
        "neutral": 0.82, "cereal": 0.00, "nutty": 0.00, "earthy": 0.04,
        "bitter": 0.08, "sweet": 0.00, "toasted": 0.00, "rich": 0.02,
    },
    "psyllium husk": {
        "neutral": 0.42, "cereal": 0.12, "nutty": 0.08, "earthy": 0.45,
        "bitter": 0.08, "sweet": 0.02, "toasted": 0.05, "rich": 0.04,
    },
    "guar gum": {
        "neutral": 0.70, "cereal": 0.02, "nutty": 0.02, "earthy": 0.10,
        "bitter": 0.06, "sweet": 0.02, "toasted": 0.00, "rich": 0.03,
    },
    "hpmc (hydroxypropyl methylcellulose)": {
        "neutral": 0.92, "cereal": 0.00, "nutty": 0.00, "earthy": 0.02,
        "bitter": 0.02, "sweet": 0.00, "toasted": 0.00, "rich": 0.00,
    },
    "amaranth flour": {
        "neutral": 0.36, "cereal": 0.52, "nutty": 0.32, "earthy": 0.30,
        "bitter": 0.12, "sweet": 0.16, "toasted": 0.28, "rich": 0.20,
    },
    "sodium alginate": {
        "neutral": 0.88, "cereal": 0.00, "nutty": 0.00, "earthy": 0.03,
        "bitter": 0.02, "sweet": 0.00, "toasted": 0.00, "rich": 0.00,
    },
}


APPLICATION_FLAVOR_TARGETS: dict[str, FlavorTarget] = {
    "pizza": FlavorTarget(
        name="Pizza",
        profile={
            "neutral": 0.68, "cereal": 0.58, "nutty": 0.22, "earthy": 0.12,
            "bitter": 0.04, "sweet": 0.12, "toasted": 0.45, "rich": 0.18,
        },
        rationale="Pizza target approximates mild wheat-like cereal flavor with some baked/toasted character and low bitterness/earthiness.",
    ),
    "pane": FlavorTarget(
        name="Pane",
        profile={
            "neutral": 0.66, "cereal": 0.65, "nutty": 0.20, "earthy": 0.14,
            "bitter": 0.04, "sweet": 0.18, "toasted": 0.28, "rich": 0.16,
        },
        rationale="Bread target favors clean cereal notes, low bitterness, and moderate baked character.",
    ),
    "lievitati dolci": FlavorTarget(
        name="Lievitati dolci",
        profile={
            "neutral": 0.58, "cereal": 0.42, "nutty": 0.28, "earthy": 0.08,
            "bitter": 0.03, "sweet": 0.42, "toasted": 0.25, "rich": 0.38,
        },
        rationale="Sweet leavened target allows more sweetness/richness while keeping earthy and bitter notes low.",
    ),
    "frolla": FlavorTarget(
        name="Frolla",
        profile={
            "neutral": 0.50, "cereal": 0.35, "nutty": 0.45, "earthy": 0.08,
            "bitter": 0.03, "sweet": 0.48, "toasted": 0.38, "rich": 0.55,
        },
        rationale="Shortcrust target accepts richer nutty/toasted notes and sweetness, but penalizes earthy or bitter flours.",
    ),
    "pasta fresca": FlavorTarget(
        name="Pasta fresca",
        profile={
            "neutral": 0.76, "cereal": 0.45, "nutty": 0.12, "earthy": 0.08,
            "bitter": 0.03, "sweet": 0.10, "toasted": 0.05, "rich": 0.12,
        },
        rationale="Fresh pasta target prioritizes neutral clean cereal flavor without toasted, bitter, or earthy intensity.",
    ),
    "biscotti": FlavorTarget(
        name="Biscotti",
        profile={
            "neutral": 0.48, "cereal": 0.38, "nutty": 0.50, "earthy": 0.08,
            "bitter": 0.03, "sweet": 0.45, "toasted": 0.45, "rich": 0.52,
        },
        rationale="Cookie/biscuit target allows nutty and toasted notes with low bitterness and low earthy character.",
    ),
}


DEFAULT_FLAVOR_TARGET = FlavorTarget(
    name="Generico",
    profile={
        "neutral": 0.65, "cereal": 0.45, "nutty": 0.20, "earthy": 0.12,
        "bitter": 0.05, "sweet": 0.18, "toasted": 0.22, "rich": 0.18,
    },
    rationale="Generic target for balanced gluten-free flour blends when no application-specific sensory target is selected.",
)


def _empty_profile() -> dict[str, float]:
    return {dim: 0.0 for dim in FLAVOR_DIMENSIONS}


def _fallback_profile(ingredient: Ingredient) -> dict[str, float]:
    if ingredient.category == "starch":
        return {
            "neutral": 0.90, "cereal": 0.06, "nutty": 0.02, "earthy": 0.04,
            "bitter": 0.02, "sweet": 0.08, "toasted": 0.04, "rich": 0.02,
        }
    if ingredient.category == "hydrocolloid":
        return {
            "neutral": 0.70, "cereal": 0.02, "nutty": 0.02, "earthy": 0.12,
            "bitter": 0.06, "sweet": 0.01, "toasted": 0.01, "rich": 0.02,
        }
    return {
        "neutral": 0.55, "cereal": 0.50, "nutty": 0.20, "earthy": 0.18,
        "bitter": 0.08, "sweet": 0.15, "toasted": 0.20, "rich": 0.12,
    }


def get_ingredient_flavor_profile(ingredient: Ingredient) -> dict[str, float]:
    profile = INGREDIENT_FLAVOR_PROFILES.get(ingredient.name.strip().lower())
    return dict(profile or _fallback_profile(ingredient))


def calculate_blend_flavor(ingredient_data: list[tuple[Ingredient, float]]) -> dict[str, float]:
    profile = _empty_profile()
    total = sum(proportion for _, proportion in ingredient_data)
    if total <= 0:
        return profile

    for ingredient, proportion in ingredient_data:
        ingredient_profile = get_ingredient_flavor_profile(ingredient)
        weight = proportion / total
        for dim in FLAVOR_DIMENSIONS:
            profile[dim] += ingredient_profile[dim] * weight

    return {dim: round(value, 4) for dim, value in profile.items()}


def get_flavor_target(application_name: str | None) -> FlavorTarget:
    if not application_name:
        return DEFAULT_FLAVOR_TARGET
    return APPLICATION_FLAVOR_TARGETS.get(
        application_name.strip().lower(),
        DEFAULT_FLAVOR_TARGET,
    )


def score_flavor_against_target(profile: dict[str, float], target: FlavorTarget) -> float:
    sq = 0.0
    for dim in FLAVOR_DIMENSIONS:
        sq += (profile.get(dim, 0.0) - target.profile[dim]) ** 2
    distance = math.sqrt(sq / len(FLAVOR_DIMENSIONS))
    return math.exp(-0.5 * (distance / target.sigma) ** 2)


def serialize_flavor_target(target: FlavorTarget) -> dict:
    return {
        "name": target.name,
        "profile": target.profile,
        "sigma": target.sigma,
        "evidence_level": target.evidence_level,
        "rationale": target.rationale,
        "sources": list(target.sources),
    }

from glutenix.db.models import Ingredient
from glutenix.engine.flavor import (
    calculate_blend_flavor,
    get_flavor_target,
    score_flavor_against_target,
)


class TestFlavorModel:
    def test_calculate_blend_flavor_weighted_average(self):
        rice = Ingredient(name="White rice flour", category="flour")
        buckwheat = Ingredient(name="Buckwheat flour", category="flour")

        profile = calculate_blend_flavor([(rice, 0.8), (buckwheat, 0.2)])

        assert profile["neutral"] > profile["earthy"]
        assert profile["earthy"] > 0

    def test_flavor_score_prefers_target_like_profile(self):
        target = get_flavor_target("Pizza")
        close = dict(target.profile)
        far = dict(target.profile)
        far["bitter"] = 0.9
        far["earthy"] = 0.9
        far["neutral"] = 0.1

        assert score_flavor_against_target(close, target) > score_flavor_against_target(far, target)

    def test_unknown_application_uses_generic_target(self):
        assert get_flavor_target("unknown").name == "Generico"

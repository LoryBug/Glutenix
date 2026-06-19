from glutenix.db.models import (
    Application,
    Blend,
    BlendIngredient,
    ExperimentResult,
    Ingredient,
    SimulationResult,
)
from glutenix.schemas.models import (
    ApplicationCreate,
    BlendCreate,
    BlendIngredientCreate,
    ExperimentResultCreate,
    IngredientCreate,
    SimulationResultCreate,
)


class TestIngredientModel:
    def test_create_ingredient(self, db_session):
        i = Ingredient(name="Test flour", category="flour", protein_pct=10.5)
        db_session.add(i)
        db_session.commit()
        assert i.id is not None
        assert i.name == "Test flour"

    def test_ingredient_constraints(self, db_session):
        i = Ingredient(name="Test starch", category="starch", amylose_pct=25.0)
        db_session.add(i)
        db_session.commit()
        assert i.amylose_pct == 25.0

    def test_seed_data_count(self, db_session):
        from glutenix.db.seed import _seed_ingredients, _seed_applications

        _seed_ingredients(db_session)
        _seed_applications(db_session)
        db_session.commit()

        assert db_session.query(Ingredient).count() == 29
        assert db_session.query(Application).count() == 5


class TestBlendModel:
    def test_create_blend(self, db_session):
        i = Ingredient(name="Rice", category="flour", protein_pct=6.0)
        db_session.add(i)
        db_session.commit()

        b = Blend(name="Test blend")
        db_session.add(b)
        db_session.commit()

        bi = BlendIngredient(blend_id=b.id, ingredient_id=i.id, proportion=0.5)
        db_session.add(bi)
        db_session.commit()

        assert len(b.ingredients) == 1
        assert b.ingredients[0].proportion == 0.5

    def test_blend_proportions_sum(self, db_session):
        i1 = Ingredient(name="Flour A", category="flour")
        i2 = Ingredient(name="Flour B", category="flour")
        db_session.add_all([i1, i2])
        db_session.commit()

        b = Blend(name="Sum test")
        db_session.add(b)
        db_session.commit()

        db_session.add_all(
            [
                BlendIngredient(blend_id=b.id, ingredient_id=i1.id, proportion=0.3),
                BlendIngredient(blend_id=b.id, ingredient_id=i2.id, proportion=0.7),
            ]
        )
        db_session.commit()

        total = sum(bi.proportion for bi in b.ingredients)
        assert abs(total - 1.0) < 1e-6


class TestSimulationResult:
    def test_create_simulation_result(self, db_session):
        i = Ingredient(name="Flour", category="flour")
        db_session.add(i)
        db_session.commit()

        b = Blend(name="Sim blend")
        db_session.add(b)
        db_session.commit()

        sr = SimulationResult(
            blend_id=b.id,
            results='{"volume": 4.5, "hardness": 2.1}',
        )
        db_session.add(sr)
        db_session.commit()

        assert sr.id is not None
        import json

        data = json.loads(sr.results)
        assert data["volume"] == 4.5


class TestExperimentResult:
    def test_create_experiment_result(self, db_session):
        i = Ingredient(name="Flour", category="flour")
        db_session.add(i)
        db_session.commit()

        b = Blend(name="Exp blend")
        db_session.add(b)
        db_session.commit()

        er = ExperimentResult(
            blend_id=b.id,
            metrics='{"specific_volume": 3.2, "hardness": 5.1}',
        )
        db_session.add(er)
        db_session.commit()

        assert er.id is not None


class TestPydanticSchemas:
    def test_ingredient_create(self):
        data = IngredientCreate(
            name="Test", category="flour", protein_pct=12.5
        )
        assert data.name == "Test"
        assert data.protein_pct == 12.5

    def test_ingredient_invalid_category(self):
        import pydantic

        try:
            IngredientCreate(name="Bad", category="invalid")
            assert False, "Should have raised"
        except pydantic.ValidationError:
            pass

    def test_blend_create(self):
        data = BlendCreate(
            name="My blend",
            ingredients=[
                BlendIngredientCreate(ingredient_id=1, proportion=0.5),
                BlendIngredientCreate(ingredient_id=2, proportion=0.5),
            ],
        )
        assert len(data.ingredients) == 2

    def test_blend_ingredient_proportion_range(self):
        import pydantic

        try:
            BlendIngredientCreate(ingredient_id=1, proportion=1.5)
            assert False
        except pydantic.ValidationError:
            pass

    def test_simulation_result_create(self):
        data = SimulationResultCreate(
            blend_id=1,
            results='{"volume": 4.2}',
        )
        assert data.blend_id == 1

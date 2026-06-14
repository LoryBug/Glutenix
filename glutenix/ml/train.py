import torch

from glutenix.db.models import Ingredient
from glutenix.engine.blend import BlendCalculator
from glutenix.engine.fermentation import (
    FermentationParams,
    FermentationSimulator,
)
from glutenix.ml.gpr import PhysicsGPR


def generate_synthetic_data(
    ingredients: list[Ingredient],
    n_samples: int = 500,
    seed: int = 42,
) -> tuple[torch.Tensor, torch.Tensor]:
    torch.manual_seed(seed)

    calc = BlendCalculator()
    ferm = FermentationSimulator(
        FermentationParams(temp_c=28.0)
    )

    n_feats = len(PhysicsGPR.FEATURE_NAMES)
    features = []
    targets = []

    for _ in range(n_samples):
        weights = torch.rand(len(ingredients))
        weights = weights / weights.sum()

        ingredient_data = [
            (ing, w.item()) for ing, w in zip(ingredients, weights)
        ]

        props = calc.calculate(ingredient_data)

        result = ferm.simulate(
            viscosity_index=props.viscosity_index,
            duration_min=120.0,
        )

        feat_vec = torch.tensor(
            [
                props.protein_pct,
                props.starch_pct,
                props.fat_pct,
                props.fiber_pct,
                props.water_absorption,
                props.gelatinization_temp_min,
                props.amylose_pct,
                props.viscosity_index,
                props.hydrocolloid_pct,
            ],
            dtype=torch.float,
        )

        features.append(feat_vec)
        targets.append(result.final_volume_increase * 100)

    return torch.stack(features), torch.tensor(targets, dtype=torch.float)


def train_model(
    ingredients: list[Ingredient] | None = None,
    n_samples: int = 500,
    n_iter: int = 200,
) -> PhysicsGPR:
    from glutenix.db.base import SessionLocal
    from glutenix.db.seed import seed_database

    if ingredients is None:
        from glutenix.db.base import Base, engine

        Base.metadata.create_all(engine)
        seed_database()
        session = SessionLocal()
        ingredients = session.query(Ingredient).all()
        session.close()

    print(f"Generating {n_samples} synthetic blends...")
    train_x, train_y = generate_synthetic_data(ingredients, n_samples)

    print(f"Training GPR on {n_samples} samples ({n_iter} iterations)...")
    gpr = PhysicsGPR()
    gpr.train(train_x, train_y, n_iter=n_iter, verbose=True)

    return gpr

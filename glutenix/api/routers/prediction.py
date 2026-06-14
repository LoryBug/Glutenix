from fastapi import APIRouter, Depends
from pydantic import BaseModel

from glutenix.api.deps import get_gpr
from glutenix.ml.gpr import PhysicsGPR, Prediction

router = APIRouter(prefix="/predict", tags=["prediction"])


class PredictRequest(BaseModel):
    features: list[float]


class PredictResponse(BaseModel):
    mean: float
    std: float
    conf_interval_95: tuple[float, float]


@router.post("", response_model=PredictResponse)
def predict(body: PredictRequest, gpr: PhysicsGPR = Depends(get_gpr)):
    if not gpr.is_trained:
        return PredictResponse(mean=0.0, std=1.0, conf_interval_95=(-2.0, 2.0))
    pred: Prediction = gpr.predict(body.features)
    return PredictResponse(
        mean=round(pred.mean, 4),
        std=round(pred.std, 4),
        conf_interval_95=(round(pred.conf_interval_95[0], 4), round(pred.conf_interval_95[1], 4)),
    )

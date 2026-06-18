import structlog
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from glutenix.api.middleware import TracingMiddleware
from glutenix.api.routers import (
    applications,
    blends,
    calibration,
    experiments,
    ingredients,
    optimization,
    prediction,
    simulation,
)
from glutenix.logging import setup_logging

setup_logging()

logger = structlog.get_logger("glutenix.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("server_starting")
    yield
    logger.info("server_stopping")


app = FastAPI(title="Glutenix API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TracingMiddleware)

app.include_router(ingredients.router)
app.include_router(applications.router)
app.include_router(blends.router)
app.include_router(simulation.router)
app.include_router(prediction.router)
app.include_router(optimization.router)
app.include_router(experiments.router)
app.include_router(calibration.router)


@app.get("/health")
def health():
    logger.info("health_check")
    return {"status": "ok"}

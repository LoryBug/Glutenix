import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_URL = os.getenv(
    "GLUTENIX_DATABASE_URL",
    f"sqlite:///{PROJECT_ROOT / 'glutenix.db'}"
)

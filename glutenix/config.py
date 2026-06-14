from pathlib import Path


DATABASE_URL = "sqlite:///glutenix.db"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

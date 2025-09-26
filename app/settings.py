# app/settings.py
from pathlib import Path

# Smaller Text-to-SQL model
NLSQL_MODEL_ID = "NumbersStation/nsql-350M"
NLSQL_MAX_NEW_TOKENS = 128

PROJECT_ROOT = Path(__file__).resolve().parents[1]

HF_HOME = PROJECT_ROOT / "hf-cache"
TRANSFORMERS_CACHE = HF_HOME / "transformers"
TRANSFORMERS_CACHE.mkdir(parents=True, exist_ok=True)

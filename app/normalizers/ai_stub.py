from copy import deepcopy
from .base import Normalizer
from .types import CITypes, Record

class AINormalizer(Normalizer):
    """Placeholder for an LLM-backed normalizer. Currently a no-op."""
    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or "placeholder"

    def normalize_record(self, kind: CITypes, rec: Record) -> Record:
        # In future: call your model to infer/standardize fields.
        return deepcopy(rec)

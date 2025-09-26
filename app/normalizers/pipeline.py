# app/normalizers/pipeline.py
from copy import deepcopy
from typing import List
from .base import Normalizer
from .types import CITypes, Record
from .rules import RuleNormalizer
# from .ai_stub import AINormalizer  # enable later

class NormalizerPipeline(Normalizer):
    """Run stages in order; each stage's OUTPUT becomes the INPUT for the next."""
    def __init__(self, stages: List[Normalizer]):
        self.stages = stages

    def normalize_record(self, kind: CITypes, rec: Record) -> Record:
        out = deepcopy(rec)
        # Pass the record through each stage in sequence
        for stage in self.stages:
            out = stage.normalize_record(kind, out)
        return out

def get_default_normalizer() -> Normalizer:
    # Add AINormalizer later if/when needed:
    # return NormalizerPipeline([RuleNormalizer(), AINormalizer(...)])
    return NormalizerPipeline([RuleNormalizer()])

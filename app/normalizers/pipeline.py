from copy import deepcopy
from typing import List
from .base import Normalizer
from .types import CITypes, Record
from .rules import RuleNormalizer
# from .ai_stub import AINormalizer  # placeholder for a future ML normalizer

class NormalizerPipeline(Normalizer):
    """
    A chain of normalizers.
    Each stage takes the output of the previous stage,
    making it easy to mix rule-based and AI-based cleaning steps.
    """
    def __init__(self, stages: List[Normalizer]):
        self.stages = stages
    
    def normalize_record(self, kind: CITypes, rec: Record) -> Record:
        out = deepcopy(rec)  # Don't mutate the input
        # Apply each normalizer in a sequence
        for stage in self.stages:
            out = stage.normalize_record(kind, out)
        return out

def get_default_normalizer() -> Normalizer:
    """
    Factory for the default pipeline.
    Currently just rule-based, but adding an AI stage is a one-line change.
    """
    # Example for later:
    # return NormalizerPipeline([RuleNormalizer(), AINormalizer(...)])
    return NormalizerPipeline([RuleNormalizer()])

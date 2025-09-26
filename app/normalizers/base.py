# app/normalizers/base.py
from typing import Protocol
from .types import CITypes, Record

class Normalizer(Protocol):
    def normalize_record(self, kind: CITypes, rec: Record) -> Record:
        """Return a NEW normalized record. Do not mutate `rec`."""
        ...

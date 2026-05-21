from enum import Enum
from typing import NamedTuple

class DuplicateRemoveMode(Enum):
    NONE = -1
    OLDEST = 0
    NEWEST = 1
    UPDATE = 2
    SELECT = 3

class AnkiConfig(NamedTuple):
    col_path: str
    furigana_timeout: int
    sentence_timeout: int
    resti_readings_timeout: int
    expr_readings_timeout: int
    dupl_resolve: DuplicateRemoveMode
    min_meanings: int
    min_sentences: int
    min_compounds: int
    min_compound_meanings: int
    max_kanjis_meanings: int

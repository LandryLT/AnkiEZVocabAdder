from enum import Enum
from typing import NamedTuple

class DuplicateRemoveMode(Enum):
    NONE = -1
    OLDEST = 0
    NEWEST = 1
    SELECT = 2

class AnkiConfig(NamedTuple):
    col_path: str
    furigana_timeout: int
    dupl_resolve: DuplicateRemoveMode
    min_meanings: int
    min_sentences: int

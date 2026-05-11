from scripts.anki.ankiDeckGenerator import EZDecks
from scripts.anki.ankiModelGenerator import EZModels
from anki.storage import Collection

class AnkiNoteGen():
    def __init__(self, col: Collection, decks: EZDecks, models: EZModels):
        self.col = col
        self.decks = decks
        self.models = models
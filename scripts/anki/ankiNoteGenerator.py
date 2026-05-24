from scripts.anki.ankiDeckGenerator import EZDecks
from scripts.anki.ankiModelGenerator import EZModels
from anki.storage import Collection
from anki.decks import DeckDict
from anki.notes import Note
from pathlib import Path

class AnkiNoteGen():
    def __init__(self, col: Collection, decks: EZDecks, models: EZModels):
        self.col = col
        self.decks = decks
        self.models = models

    def submitNoteToDeck(self, note: Note, deck: DeckDict):
        self.col.add_note(note, deck["id"])

    def addAudio(self, filepath:str) -> str:
        if filepath and Path(filepath).is_file():
            return f'<audio class="sentence_audio" src="{self.col.media.add_file(filepath)}" preload="none"></audio>'
        return '<audio class="sentence_audio" src="" preload="none"></audio>'
    
    def addImage(self, filepath:str) -> str:
        if filepath and Path(filepath).is_file():
            return f'<img src="{self.col.media.add_file(filepath)}">'
        return ''
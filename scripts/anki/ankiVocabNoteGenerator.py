from ankiNoteGenerator import AnkiNoteGen
from scripts.scrappers.JishoSearchResult import JishoResult
class AnkiVocabNoteGen(AnkiNoteGen):
    def __init__(self, col, decks, models):
        super().__init__(col, decks, models)

    def genVovabNote(self, jisho_rez: JishoResult):
        new_note = self.col.new_note(self.models.vocab)
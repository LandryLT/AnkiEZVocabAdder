from scripts.anki.ankiNoteGenerator import AnkiNoteGen
from scripts.scrappers.KanjiResults import KanjiResult
from anki.notes import Note
import re

class AnkiKanjiNoteGen(AnkiNoteGen):
    def __init__(self, col, decks, models):
        super().__init__(col, decks, models)
        k_decks = self.decks.kanji
        self.ordered_jlpt_decks = [k_decks.deck, k_decks.n1, k_decks.n2, k_decks.n3, k_decks.n4, k_decks.n5]

    def submitNoteToKanjiDeck(self, note: Note):
        level = re.match(r'\d', note['JLPT'])
        if not level or level.group(0) == '0':
            self.submitNoteToDeck(note, self.ordered_jlpt_decks[0])
            return
        self.submitNoteToDeck(note, self.ordered_jlpt_decks[int(level.group(0))])
        
    def getAllKanjiImages(self, kanjis:str):
        output = {}
        for k in kanjis:
            output[k] = self.col.get_note(self.col.find_notes(f'note:{self.models.kanji["name"]} Kanji:{k}')[0])["Stroke Order Image"]
        return output

    def genKanjiNote(self, kanji_rez: KanjiResult) -> Note:
        new_note = self.col.new_note(self.models.kanji)
        new_note["Kanji"] = kanji_rez.kanji
        new_note["Meaning"] = kanji_rez.meaning
        new_note["OnYomi"] = "、".join(kanji_rez.on_yomi)
        new_note["KunYomi"] = "、".join(kanji_rez.kun_yomi)
        new_note["JLPT"] = str(kanji_rez.jlpt)
        new_note["Ranking"] = str(round(kanji_rez.ranking * 100, 2)) if kanji_rez.ranking != -1 else ""
        new_note["Stroke Order Image"] = self.addImage(kanji_rez.img_file)

        new_note = self.setCompounds(new_note, kanji_rez.compounds)
        return new_note

    def setCompounds(self, new_note: Note, compounds: dict[str, list[str]]) -> Note:
        for i in range(10):
            for yomi in compounds.keys():
                if i >= len(compounds[yomi]):
                    new_note[f'{yomi} Compound {i+1} Word'] = ""
                    new_note[f'{yomi} Compound {i+1} Furigana'] = ""
                    new_note[f'{yomi} Compound {i+1} Meaning'] = ""
                    continue
                compound_match = re.match(r'^(.+)【(.+)】(.+)$', compounds[yomi][i])
                if not compound_match:
                    break
                new_note[f'{yomi} Compound {i+1} Word'] = compound_match.group(1)
                new_note[f'{yomi} Compound {i+1} Furigana'] = compound_match.group(2)
                new_note[f'{yomi} Compound {i+1} Meaning'] = compound_match.group(3)
        return new_note



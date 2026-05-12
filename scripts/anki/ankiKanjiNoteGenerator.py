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
        

    def genKanjiNote(self, kanji_rez: KanjiResult) -> Note:
        new_note = self.col.new_note(self.models.kanji)
        new_note["Kanji"] = f'<div class="kanji">{kanji_rez.kanji}</div>'
        new_note["Meaning"] = f'<div class="meaning">{kanji_rez.meaning}</div>'
        new_note["OnYomi"] = f'<div class="on_yomi">{kanji_rez.on_yomi}</div>'
        new_note["KunYomi"] = f'<div class="kun_yomi">{kanji_rez.kun_yomi}</div>'
        new_note["JLPT"] = f'<div class="jlpt">{kanji_rez.jlpt}</div>'
        new_note["Ranking"] = f'<div class="ranking">{kanji_rez.ranking}</div>'
        new_note["Stroke Order Image"] = f'<div class="stroke_order">{self.addImage(kanji_rez.img_file)}</div>'

        new_note = self.setCompounds(new_note, kanji_rez.compounds)
        return new_note

    def setCompounds(self, new_note: Note, compounds: dict[str, list[str]]) -> Note:
        for i in range(10):
            for yomi in compounds.keys():
                if i >= len(compounds[yomi]):
                    break
                compound_match = re.match(r'^(([一-龯]|[ぁ-ゔ]|[ァ-ヴー]|[a-zA-Z0-9]|[ａ-ｚＡ-Ｚ０-９]|[々〆〤ヶ])+) 【(([一-龯]|[ぁ-ゔ]|[ァ-ヴー]|[a-zA-Z0-9]|[ａ-ｚＡ-Ｚ０-９]|[々〆〤ヶ])+)】 (.+)$', compounds[yomi][i])
                if not compound_match:
                    break
                new_note[f'{yomi} - Compound {i+1} Word'] = compound_match.group(1)
                new_note[f'{yomi} - Compound {i+1} Furigana'] = compound_match.group(3)
                new_note[f'{yomi} - Compound {i+1} Meaning'] = compound_match.group(5)



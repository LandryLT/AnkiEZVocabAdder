from scripts.anki.ankiNoteGenerator import AnkiNoteGen
from scripts.scrappers.JishoSearchResult import Meaning
from scripts.scrappers.VocabScrapper import VocabScraperResult
from scripts.anki.ankiDeckGenerator import VocabJLPTDeck
from scripts.scrappers.NeocitiesScrapper import NeocitiesResult
from anki.notes import Note
import re

class AnkiVocabNoteGen(AnkiNoteGen):
    def __init__(self, col, decks, models):
        super().__init__(col, decks, models)
        v_decks = self.decks.vocab
        self.ordered_jlpt_decks = [v_decks.deck, v_decks.n1, v_decks.n2, v_decks.n3, v_decks.n4, v_decks.n5]
    
    @staticmethod
    def setKanjisStrokes(notes: list[Note], kanjis_images: dict[str, str]):
        for n in notes:
            strokes = []
            for k in re.findall(r'[一-龯]', n['Expression']):
                strokes.append(kanjis_images[k])
            n["Kanjis"] = "".join(strokes)


    def submitNoteToVocabDeck(self, note: Note):
        level_match = re.match(r'\d', note['JLPT'])
        if not level_match or level_match.group(0) == '0':
            self.submitNoteToDeck(note, self.ordered_jlpt_decks[0])
            return
        level: VocabJLPTDeck = self.ordered_jlpt_decks[int(level_match.group(0))]
        
        def findTypeInTags(word_type: str):
            pattern = re.compile(f'(?mi)<div class="m_tag">[^<]*({word_type})[^<]*<\/div>')
            return len(re.findall(pattern, note["Meanings"]))
        
        intransitive_verb_matches = findTypeInTags("intransitive")
        transitive_verb_matches = findTypeInTags("transitive")
        i_adj_matches = findTypeInTags("i-adjective")
        na_adj_matches = findTypeInTags("a-adjective")
        expr_matches = findTypeInTags("verb")
        noun_matches = findTypeInTags("noun")
        
        if transitive_verb_matches and intransitive_verb_matches:
            self.submitNoteToDeck(note, level.verbs.deck)
        elif transitive_verb_matches:
            self.submitNoteToDeck(note, level.verbs.transitive)
        elif intransitive_verb_matches:
            self.submitNoteToDeck(note, level.verbs.intransitive)
        elif i_adj_matches:
            self.submitNoteToDeck(note, level.adjectives.i)
        elif na_adj_matches:
            self.submitNoteToDeck(note, level.adjectives.na)
        elif expr_matches:
            self.submitNoteToDeck(note, level.expressions)
        elif noun_matches:
            self.submitNoteToDeck(note, level.nouns)
        else:
            self.submitNoteToDeck(note, level.deck)

  

    def genVocabNote(self, vocab_rez: VocabScraperResult) -> Note:
        jisho_rez = vocab_rez.jisho
        neocities_rez = vocab_rez.neocities
        new_note = self.col.new_note(self.models.vocab)
        new_note["Expression"] = jisho_rez.expression
        new_note["Furigana"] = jisho_rez.furigana
        new_note["Romaji"] = jisho_rez.romaji
        new_note["JLPT"] = str(jisho_rez.JLPT)
        
        new_note["Kanjis"] = ""
        new_note["Meanings"] = self.setMeanings(jisho_rez.meanings)
        new_note["Audio"] = self.addAudio(jisho_rez.soundfile)
        new_note["Transitivity"] = self.setTransitivity(jisho_rez.meanings)
        
        new_note = self.setInflections(new_note, jisho_rez.inflections)
        new_note = self.setSentences(new_note, neocities_rez)
        return new_note


    def setMeanings(self, meanings: list[Meaning]) -> str:
        output = '<div class="meanings">'
        for i, m in enumerate(meanings):
            output += f'<div class="m_h_wrapper"><div class="m_ind">{i+1}.</div>'
            output += f'<div class="m_v_wrapper"><div class="m_tag">{m.tag}</div><div class="m_mean">{m.meaning}</div></div></div>'
        output += '</div>'
        return output

    def setInflections(self, new_note: Note, inflections: dict | None) -> Note:
        # if not inflections:
        #     return new_note
        modes = ["Affirmative", "Negative"]
        for infl in ["Non-past", "Non-past polite", "Past", "Past polite", "Te-form", "Potential", "Passive", "Causative", "Causative Passive", "Imperative"]:
            for i in range(2):
                new_note[f"Inflection - {infl} - {modes[i]}"] = '' if not inflections or infl not in inflections.keys() else inflections[infl][i]
        return new_note

    def setSentences(self, new_note: Note, sentences: list[NeocitiesResult]) -> Note:
        for i in range(20):
            if i >= len(sentences):
                new_note[f'Sentence {i+1} Japanese'] = ""
                new_note[f'Sentence {i+1} English'] = ""
                new_note[f'Sentence {i+1} Audio'] = ""
            else:    
                s = sentences[i]
                new_note[f'Sentence {i+1} Japanese'] = self.boldSearchTerm(s.japanese, s.search_term)
                new_note[f'Sentence {i+1} English'] = s.english
                new_note[f'Sentence {i+1} Audio'] = self.addAudio(s.soundfile)

        return new_note

    @staticmethod
    def boldSearchTerm(sentence:str, search_term: str):
        for m in list(re.finditer(re.compile(search_term), sentence))[::-1]:
            sentence = sentence[:m.start()] + '<span class="search_term">' + sentence[m.start():m.end()] + "</span>" + sentence[m.end():]
        return sentence

    def setTransitivity(self, meanings: list[Meaning]) -> str:
        all_tags = [m.tag for m in meanings]
        has_transitive = any([re.match(r".*(?i:\btransitive\b).*", t) for t in all_tags])
        has_intransitive = any([re.match(r".*(?i:\bintransitive\b).*", t) for t in all_tags])
        # def div_decorate(s: str):
        #     return f'<div class="transitiveness">{s}</div>'
        if has_intransitive and has_transitive:
            return "Transitive & Intransitive"
        elif has_transitive:
            return "Transitive"
        elif has_intransitive:
            return "Intransitive"
        else:
            return ""
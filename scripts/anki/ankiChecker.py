import logging
from scripts.utils.printingUtils import clearConsole, grey, bold
from scripts.scrappers.VocabScrapper import VocabScraperResult
from scripts.scrappers.JishoSearchResult import JishoResult
from scripts.scrappers.Scrapper import Scrapper
from anki.storage import Collection
from anki.decks import Deck
from anki.models import NotetypeDict
from anki.notes import Note

from pathlib import Path
import os
import re
from copy import deepcopy
from collections import namedtuple
VocabVerb = namedtuple("VocabVerb", ["deck", "transitive", "intransitive"], defaults=[*[Deck]*3])
VocabAdj = namedtuple("VocabAdj", ["deck", "i", "a"], defaults=[*[Deck]*3])
VocabJLPTDeck = namedtuple("VocabJLPTDeck", ["deck", "verbs", "ajectives", "nouns", "expression", "others"], defaults=[Deck, VocabVerb, VocabAdj, *[Deck]*3])
JLPT_NN = [f"n{i+1}" for i in range(5)]
VocabDecks = namedtuple("VocabDecks", ["deck", *JLPT_NN], defaults=[Deck, *[VocabJLPTDeck]*5])
KanjiDecks = namedtuple("KanjiDecks", ["deck", *JLPT_NN], defaults=[*[Deck]*6])
EZDecks = namedtuple("EZDecks", ["deck", "vocab", "kanji"], defaults=[Deck, VocabDecks, KanjiDecks])
EZModels = namedtuple("EZModels", ["kanji", "vocab"], defaults=[NotetypeDict, NotetypeDict])

ResultConflict = namedtuple("ResultConflict", ["candidate", "conflicting_notes"], defaults=[JishoResult, list[Note]])

class AnkiChecker():
    logger = logging.getLogger(__name__)
    def __init__(self, col_path: str = None):
        self.col_path = self.findCollections() if not col_path else col_path
        self.kanji_model_name = "EZAnkiAdder-Kanji"
        self.vocab_model_name = "EZAnkiAdder-Vocab"
        if not Path(col_path).is_file():
            raise AnkiChecker.ColNotFound
    
    def conflictingKanjis(self, kanjis: list[str]):
        curr_kanji = [self.col.get_note(n)["Kanji"] for n in self.col.find_cards(f'note:{self.kanji_model_name}')]
        return [k for k in kanjis if k in curr_kanji]
    
    def conflictingVocab(self, scrapper_results: VocabScraperResult):
        curr_vocab = [self.col.get_note(n) for n in self.col.find_cards(f'note:{self.vocab_model_name}')]
        conflicting_results = []
        for rez in scrapper_results:
            assert isinstance(rez, VocabScraperResult)
            assert isinstance(rez.jisho, JishoResult)
            conflicting_meanings = [n for n in curr_vocab if n["Meanings"] == rez.jisho.meanings]
            if conflicting_meanings:
                conflicting_results.append(ResultConflict(rez, conflicting_meanings))
            
            cleaned_rez_pattern = re.compile('\b' + re.sub(r' \([^\(\)]+\)', '', rez.jisho.expression) + '\b')
            conflicting_expression = [n for n in curr_vocab if re.match(cleaned_rez_pattern, n["Expression"])]
            if conflicting_expression:
                conflicting_results.append(ResultConflict(rez, conflicting_expression))
        return conflicting_results

    def __enter__(self):
        self.col = Collection(self.col_path)
        self.models = self.findModels()
        self.decks = self.findDecks()

    def __exit__(self, exc_type, exc, tb):
        self.col.close()

    def findDecks(self):
        deck_tree = self._deckTreeBuilder()
        flattened_deck_names = self._getDeckTreePaths(deck_tree)
        all_decks = self.col.decks.all_names_and_ids()
        for deck_name in flattened_deck_names:
            if deck_name not in [d.name for d in all_decks]:
                self.logger.info(f'{deck_name} not found, creating new deck')
                new_deck = self.col.decks.new_deck()
                new_deck.name = deck_name
                self.col.decks.add_deck(new_deck)
        

        v_d = self._getVocabDecks()
        k_d = self._getKanjiDecks()
        return EZDecks(self.col.decks.by_name("EZAnki"), v_d, k_d)
        
    def _getKanjiDecks(self):
        base_path = "EZAnki::Kanji::_JLPT N1_::_JLPT N2_::_JLPT N3_::_JLPT N4_::_JLPT N5_"
        split_path = base_path.split("::")
        kanji_deck = self.col.decks.by_name('::'.join(split_path[:2]))
        jlpt_decks = []
        for i in range(5):
            jlpt_decks.append(self.col.decks.by_name('::'.join(split_path[:3+i])))
        return KanjiDecks(kanji_deck, *jlpt_decks)
        
    def _getVocabDecks(self):
        base_path = "EZAnki::Vocabulary::_JLPT N1_::_JLPT N2_::_JLPT N3_::_JLPT N4_::_JLPT N5_"
        split_path = base_path.split("::")
        kanji_deck = self.col.decks.by_name('::'.join(split_path[:2]))
        jlpt_decks = []
        for i in range(5):
            curr_branch = '::'.join(split_path[:3+i])
            jlpt_d = self.col.decks.by_name(curr_branch)
            verb_branch = curr_branch + "::Verbs"
            verb_d = VocabVerb(self.col.decks.by_name(verb_branch),
                               self.col.decks.by_name(verb_branch+"::Transitive"),
                               self.col.decks.by_name(verb_branch+"::Intransitive"),)
            adj_branch = curr_branch + "::Adjectives"
            adj_d = VocabAdj(self.col.decks.by_name(adj_branch),
                             self.col.decks.by_name(adj_branch+"::I-Adjective"),
                             self.col.decks.by_name(adj_branch+"::Na-Adjective"),)
            noun_d = self.col.decks.by_name(curr_branch+"::Nouns")
            expr_d = self.col.decks.by_name(curr_branch+"::Expressions")
            other_d = self.col.decks.by_name(curr_branch+"::Others")
            jlpt_decks.append(VocabJLPTDeck(jlpt_d, verb_d, adj_d, noun_d, expr_d, other_d))
            
        return VocabDecks(kanji_deck, *jlpt_decks)
    
    @staticmethod
    def _getDeckTreePaths(deck_tree: dict, join_with: str = "::"):
        output = []
        def recursive_branch_finder(tree: dict, c_branch: list):
            for k, v in tree.items():
                new_branch = c_branch.copy()
                new_branch.append(k)
                if isinstance(v, dict):
                    if not v.keys():
                        output.append(join_with.join(new_branch))
                    else:
                        recursive_branch_finder(v ,new_branch)
        recursive_branch_finder(deck_tree, [])
        return output

    @staticmethod
    def _deckTreeBuilder():
        jlpts = { "_JLPT N1_": { "_JLPT N2_": { "_JLPT N3_": { "_JLPT N4_": { "_JLPT N5_": {}}}}}}
        word_types = {
            "Verbs": {
                "Transitive":{},
                "Intransitive":{},
            },
            "Adjectives":{
                "I-Adjective":{},
                "Na-Adjective":{}
            },
            "Nouns":{},
            "Expressions":{},
            "Others":{}
        }
        deck_tree = {
            "EZAnki":{
                "Kanji": deepcopy(jlpts),
                "Vocabulary": deepcopy(jlpts),
            }
        }
        
        def _inject_word_types(tree: dict, template: dict):
            for key, value in tree.items():
                if isinstance(value, dict):
                    for wt_key, wt_value in template.items():
                        value.setdefault(wt_key, deepcopy(wt_value))
                    for child_key, child_value in value.items():
                        assert isinstance(child_key, str)
                        if child_key.startswith("_JLPT N"):
                            _inject_word_types({child_key: child_value}, template)
        _inject_word_types(deck_tree["EZAnki"]["Vocabulary"], word_types)
        return deck_tree
            
    def findCollections(self, config_file: str = './searchConfig.txt') -> Path:
        clearConsole()
        supposed_collection_folder = Path(*Path('.').absolute().parts[0:3] + ("AppData/Roaming/Anki2",))
        if not os.path.isdir(supposed_collection_folder):
            raise AnkiChecker.ColNotFound
        data_bases = {}
        for dir in os.listdir(supposed_collection_folder):
            coll_path = Path(supposed_collection_folder).joinpath(dir).joinpath("collection.anki2")
            if coll_path.is_file():
                data_bases[dir] = coll_path

        if len(data_bases.keys()) == 1:
            output = data_bases.values[0]
            self.writeColPathInConfigFile(output, config_file)
            return output
        
        print(grey("Please select a Anki collection :"))
        for i, k in enumerate(data_bases.keys()):
            print("\t" + bold(f'{i}. {k}'))
        
        while True:
            response = re.match(r'\d+', input(grey(": ")))
            if response and int(response.group(0)) < len(data_bases.keys()):
                output = list(data_bases.values())[int(response.group(0))]
                self.writeColPathInConfigFile(output, config_file)
                return output
        
    @staticmethod
    def writeColPathInConfigFile(colpath: Path, config_file: Path):
        with open(config_file, 'r') as f:
            lines = f.read()
        lines = re.sub(r'(?m:(?<=^anki_collection_file_path=).*$)', colpath.as_posix(), lines)
        with open(config_file, 'w') as f:
            f.write(lines)
        
    def findModels(self) -> EZModels:
        self.kanji_model = None
        self.vocab_model = None
        models = self.col.models.all()
        for m in models:
            if m['name'] == self.kanji_model_name:
                self.logger.info("Found kanji note model in Anki")
                self.kanji_model = self.col.models.get(m['id'])
                continue
            if m['name'] == self.vocab_model_name:
                self.logger.info("Found vocab note model in Anki")
                self.vocab_model = self.col.models.get(m['id'])
        
        if not self.kanji_model:
            self.logger.info("Kanji note model not found")
            self.kanji_model = self.genKanjiModel()
        if not self.vocab_model:
            self.logger.info("Vocab note model not found")
            self.kanji_model = self.genVocabModel()
        
        return EZModels(self.vocab_model, self.kanji_model)

    def genKanjiModel(self):
        self.logger.info("Generating kanji note model...")
        anki_models = self.col.models
        model = anki_models.new(self.kanji_model_name)
        anki_models.add_field(model, anki_models.new_field("Kanji"))
        anki_models.add_field(model, anki_models.new_field("Meaning"))
        anki_models.add_field(model, anki_models.new_field("OnYomi"))
        anki_models.add_field(model, anki_models.new_field("KunYomi"))
        anki_models.add_field(model, anki_models.new_field("Stroke Order Image"))
        anki_models.add_field(model, anki_models.new_field("JLPT"))
        anki_models.add_field(model, anki_models.new_field("Ranking"))
        for r in ["OnYomi", "KunYomi"]:
            for i in range(10):
                for t in ["Word", "Furigana", "Meaning"]:
                    anki_models.add_field(model, anki_models.new_field(f"{r} Compound {i} {t}"))
        
        restitution_template = anki_models.new_template("Restitution Card")
        expression_template = anki_models.new_template("Expression Card")

        restitution_template["qfmt"] = "{{Kanji}}"
        restitution_template["afmt"] = "{{FrontSide}}<hr id='answer'>{{Meaning}}"
        expression_template["qfmt"] = "{{Meaning}}"
        expression_template["afmt"] = "{{FrontSide}}<hr id='answer'>{{Kanji}}"

        anki_models.add_template(model, restitution_template)
        anki_models.add_template(model, expression_template)

        anki_models.add_dict(model)
        return anki_models.by_name(self.kanji_model_name)
    
    def genVocabModel(self):
        self.logger.info("Generating vocab note model...")
        anki_models = self.col.models
        model = anki_models.new(self.vocab_model_name)
        anki_models.add_field(model, anki_models.new_field("Expression"))
        anki_models.add_field(model, anki_models.new_field("Kanjis"))
        anki_models.add_field(model, anki_models.new_field("Furigana"))
        anki_models.add_field(model, anki_models.new_field("Romaji"))
        anki_models.add_field(model, anki_models.new_field("Meanings"))
        anki_models.add_field(model, anki_models.new_field("Audio"))
        anki_models.add_field(model, anki_models.new_field("JLPT"))
        anki_models.add_field(model, anki_models.new_field("Transitivness"))
        for infl in ["Non-past", "Non-past polite", "Past", "Past polite", "Te-form", "Potential", "Passive", "Causative", "Causative passive", "Imperative"]:
            for m in ["Affirmative", "Negative"]:
                anki_models.add_field(model, anki_models.new_field(f"Inflection - {infl} - {m}"))
        for i in range(20):
            for f in ["Japanese", "English", "Audio"]:
                anki_models.add_field(model, anki_models.new_field(f"Sentence {i} {f}"))

        restitution_template = anki_models.new_template("Restitution Card")
        expression_template = anki_models.new_template("Expression Card")
                
        restitution_template["qfmt"] = "{{Expression}}"
        restitution_template["afmt"] = "{{FrontSide}}<hr id='answer'>{{Meanings}}"
        expression_template["qfmt"] = "{{Meanings}}"
        expression_template["afmt"] = "{{FrontSide}}<hr id='answer'>{{Expression}}"

        anki_models.add_template(model, restitution_template)
        anki_models.add_template(model, expression_template)

        anki_models.add_dict(model)
        return anki_models.by_name(self.vocab_model_name)

    class ColNotFound(Exception):
        def __init__(self, *args):
            super().__init__(*args)
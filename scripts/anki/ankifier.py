import logging
from scripts.utils.printingUtils import clearConsole, grey, bold
from scripts.scrappers.VocabScrapper import VocabScraperResult
from scripts.scrappers.JishoSearchResult import JishoResult
from scripts.anki.ankiModelGenerator import AnkiModelGen
from scripts.anki.ankiDeckGenerator import AnkiDeckGen
from scripts.anki.ankiKanjiNoteGenerator import AnkiKanjiNoteGen
from scripts.anki.ankiVocabNoteGenerator import AnkiVocabNoteGen
from anki.storage import Collection
from anki.notes import Note
from anki.errors import DBError

from pathlib import Path
import os
import re
from typing import NamedTuple

ResultConflict = NamedTuple("ResultConflict", [("candidate", JishoResult), ("conflicting_notes", list[Note])])

class Ankifier():
    logger = logging.getLogger(__name__)
    def __init__(self, col_path: str = None):
        self.kanji_model_name = "EZAnkiAdder-Kanji"
        self.vocab_model_name = "EZAnkiAdder-Vocab"
        self.col_path = self.findCollections() if not col_path else col_path
        if not Path(col_path).is_file():
            raise Ankifier.ColNotFound
    
    def __enter__(self):
        try:
            self.col = Collection(self.col_path)
            self.logger.critical(self.col.fix_integrity())
        except DBError as e:
            raise Ankifier.AnkiAlreadyOpen
        model_gen = AnkiModelGen(self.col, self.vocab_model_name, self.kanji_model_name)
        self.models = model_gen.findModels()
        deck_gen = AnkiDeckGen(self.col)
        self.decks = deck_gen.findDecks()
        self.vocab_gen = AnkiVocabNoteGen(self.col, self.decks, self.models)
        self.kanji_gen = AnkiKanjiNoteGen(self.col, self.decks, self.models)

    def __exit__(self, exc_type, exc, tb):
        self.col.close()

    def conflictingKanjis(self, kanjis: list[str]):
        curr_kanji = [self.col.get_note(n)["Kanji"] for n in self.col.find_notes(f'note:{self.kanji_model_name}')]
        return [k for k in kanjis if k in curr_kanji]
    
    def conflictingVocab(self, scrapper_results: VocabScraperResult):
        curr_vocab = [self.col.get_note(n) for n in self.col.find_notes(f'note:{self.vocab_model_name}')]
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

            
    def findCollections(self, config_file: str = './searchConfig.txt') -> Path:
        clearConsole()
        supposed_collection_folder = Path(*Path('.').absolute().parts[0:3] + ("AppData/Roaming/Anki2",))
        if not os.path.isdir(supposed_collection_folder):
            raise Ankifier.ColNotFound
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

    class ColNotFound(Exception):
        def __init__(self, *args):
            super().__init__(*args)
    class AnkiAlreadyOpen(Exception):
        def __init__(self, *args):
            super().__init__(*args)
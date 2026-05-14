import logging
from scripts.utils.printingUtils import clearConsole, grey, bold, italic
from scripts.scrappers.VocabScrapper import VocabScraperResult
from scripts.scrappers.JishoSearchResult import JishoResult
from scripts.anki.ankiModelGenerator import AnkiModelGen
from scripts.anki.ankiDeckGenerator import AnkiDeckGen
from scripts.anki.ankiKanjiNoteGenerator import AnkiKanjiNoteGen
from scripts.anki.ankiVocabNoteGenerator import AnkiVocabNoteGen
from anki.storage import Collection
from anki.notes import Note
from anki.errors import DBError
from scripts.utils.utils import list_duplicates
from datetime import datetime

from pathlib import Path
import os
import re
from typing import NamedTuple
from collections import defaultdict
from difflib import ndiff

ResultConflict = NamedTuple("ResultConflict", [("candidate", JishoResult), ("conflicting_notes", list[Note])])

class Ankifier():
    logger = logging.getLogger(__name__)
    def __init__(self, col_path: str = None):
        self.kanji_model_name = "EZAnkiAdder-Kanji"
        self.vocab_model_name = "EZAnkiAdder-Vocab"
        self.col_path = self.findCollections() if not col_path else col_path
        if not Path(self.col_path).is_file():
            raise Ankifier.ColNotFound
    
    def __enter__(self):
        try:
            self.col = Collection(self.col_path)
            self.col.fix_integrity()
        except DBError as e:
            raise Ankifier.AnkiAlreadyOpen
        model_gen = AnkiModelGen(self.col, self.vocab_model_name, self.kanji_model_name)
        self.models = model_gen.findModels()
        deck_gen = AnkiDeckGen(self.col)
        self.decks = deck_gen.findDecks()
        self.vocab_gen = AnkiVocabNoteGen(self.col, self.decks, self.models)
        self.kanji_gen = AnkiKanjiNoteGen(self.col, self.decks, self.models)
        return self

    def __exit__(self, exc_type, exc, tb):
        self.col.close()

    def resolveNewKanjis(self, kanjis: list[str]):
        curr_kanji = [re.sub(r'<[^>]*>', '', self.col.get_note(n)["Kanji"]) for n in self.col.find_notes(f'note:{self.kanji_model_name}')]
        return [k for k in kanjis if not k in curr_kanji]
    
    def resolveConflictingVocab(self, new_notes: list[Note]):
        new_ids = [n.id for n in new_notes]
        def group_by(indices: list[int], values: list[str]):
            groups = defaultdict(list)
            for i in indices:
                groups[values[i]].append(i)
            return groups

        while True:
            clearConsole()
            print(italic(grey("Resovling duplicates")))
            all_notes = [self.col.get_note(n) for n in self.col.find_notes(f'note:{self.vocab_model_name}')] + new_notes
            if not all_notes:
                return
            all_ids = [n.id for n in all_notes]
            all_expr = [re.sub(r'<[^>]*>', '', n["Expression"]) for n in all_notes]
            all_compare_expr = [re.sub(r'(【.*】|\[\d+\])', '', n) for n in all_expr]
            all_furigana = [re.sub(r'<[^>]*>', '', n["Furigana"]) for n in all_notes]
            all_meanings = [n["Meanings"] for n in all_notes]
            all_sentences = [tuple([n[f"Sentence {i + 1} Japanese"] for i in range(20)]) for n in all_notes]

            expr_groups = group_by(range(len(all_notes)), all_compare_expr)
            deleted_notes = False
            for expr, expr_inds in expr_groups.items():
                if len(expr_inds) <= 1:
                    continue

                # Furigana
                furigana_groups = group_by(expr_inds, all_furigana)
                if len(furigana_groups) > 1:
                    notes_to_update = []
                    for furi, inds in furigana_groups.items():
                        for i in inds:
                            if all_expr[i] == expr:
                                all_notes[i]["Expression"] = f'<div class="expr">{expr}<span class="in_furi">【{furi}】</span></div>'
                                if not all_ids[i] in new_ids:
                                    notes_to_update.append(all_notes[i])
                    if notes_to_update:
                        self.col.update_notes(notes_to_update)                
                    # continue
                for furi_inds in furigana_groups.values():
                    # Meaning
                    meaning_groups = group_by(furi_inds, all_meanings)
                    if len(meaning_groups) > 1:
                        self.selectMeaningDuplicate(furi_inds, new_notes, all_notes, all_compare_expr, all_expr, all_ids)
                        deleted_notes = True
                        break
                    meaning_inds = next(iter(meaning_groups.values()))
                    # '<div class="meanings"><div class="m_tag">Godan verb - Iku/Yuku special class, Intransitive verb</div><div><span class="m_ind">1.</span><span class="m_mean">to go; to move (towards); to head (towards); to leave (for)</span></div><br/></div>'
                    # '<div class="meanings"><div class="m_tag">Godan verb - Iku/Yuku special class, Intransitive verb</div><div><span class="m_ind">1.</span><span class="m_mean">to go; to move (towards); to head (towards); to leave (for)</span></div><br></div>'
                    # Sentence
                    sentence_groups = group_by(meaning_inds, all_sentences)
                    if len(sentence_groups) > 1:
                        self.selectSentenceDuplicate(meaning_inds, new_notes, all_notes, all_compare_expr, all_expr, all_ids)
                        deleted_notes = True
                        break
                    sentence_inds = next(iter(sentence_groups.values()))

                    # Hard duplicate
                    if len(sentence_inds) > 1:
                        for r in sentence_inds[1:]:
                            if all_ids[r] == 0:
                                new_notes.remove(all_notes[r])
                        self.col.remove_notes([all_ids[i] for i in sentence_inds[1:]])
                        deleted_notes = True
                        break

            if not deleted_notes:
                break


    def selectMeaningDuplicate(self, dupl_ind_set: list[int], new_notes: list[Note], all_notes: list[Note], all_compare_expr: list[str], all_expr: list[str], all_ids: list[int]) -> None:
        clearConsole()
        print(grey(f'[DUPLICATE {bold(all_compare_expr[dupl_ind_set[0]])}')+grey(']\n'))
        for i, dupl_ind in enumerate(dupl_ind_set):
            print(bold(f'\t{i}. {all_expr[dupl_ind]}') + grey(f' [created: {datetime.fromtimestamp(all_ids[dupl_ind] / 1000).strftime("%Y/%m/%d %H:%M:%S")}]' if all_ids[dupl_ind] else ' [new note]'))
            cleaned_meaning = "\t\t- " + "\n\t\t- ".join(re.findall(r'<span class="m_mean">(.*?)<\/span>' , all_notes[dupl_ind][f"Meanings"]))
            print(cleaned_meaning+"\n")
        print(bold(grey("Caution: ")) + grey("Bear in mind that removing notes will erase their associated learning data"))
        response = None
        while response is None or response >= len(dupl_ind_set):
            response_match = re.match(r'^\s*(\d+)\s*$' ,input(grey("Note to keep : (")+bold("0-...")+grey(") : ")))
            if response_match:
                response = int(response_match.group(0))
        remaining = dupl_ind_set[:]
        remaining.pop(response)
        for r in remaining:
            if all_ids[r] == 0:
                new_notes.remove(all_notes[r])
        self.col.remove_notes([all_ids[i] for i in remaining])

    def selectSentenceDuplicate(self, dupl_ind_set: list[int], new_notes: list[Note], all_notes: list[Note], all_compare_expr: list[str], all_expr: list[str], all_ids: list[int]) -> None:
        clearConsole()
        print(grey(f'[DUPLICATE {bold(all_compare_expr[dupl_ind_set[0]])}')+grey(']\n'))
        for i, dupl_ind in enumerate(dupl_ind_set):
            print(bold(f'\t{i}. {all_expr[dupl_ind]}') + grey(f' [created: {datetime.fromtimestamp(all_ids[dupl_ind] / 1000).strftime("%Y/%m/%d %H:%M:%S")}]' if all_ids[dupl_ind] else ' [new note]'))
            for sen_ind in range(20):
                if not all_notes[dupl_ind][f"Sentence {sen_ind+1} Japanese"]:
                    break
                print(bold("\t\t- "+re.sub(r'<[^>]*>', '', all_notes[dupl_ind][f"Sentence {sen_ind+1} Japanese"])))
                print(italic("\t\t "+re.sub(r'<[^>]*>', '', all_notes[dupl_ind][f"Sentence {sen_ind+1} English"])))
            print("")
                
        print(bold(grey("Caution: ")) + grey("Bear in mind that removing notes will erase their associated learning data"))
        response = None
        while response is None or response >= len(dupl_ind_set):
            response_match = re.match(r'^\s*(\d+)\s*$' ,input(grey("Note to keep : (")+bold("0-...")+grey(") : ")))
            if response_match:
                response = int(response_match.group(1))
        remaining = dupl_ind_set[:]
        remaining.pop(response)
        for r in remaining:
            if all_ids[r] == 0:
                new_notes.remove(all_notes[r])
        self.col.remove_notes([all_ids[i] for i in remaining])
            
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
            output = list(data_bases.values())[0]
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
import logging
from scripts.utils.printingUtils import clearConsole, grey, bold, italic
from scripts.scrappers.JishoSearchResult import JishoResult
from scripts.anki.ankiModelGenerator import AnkiModelGen
from scripts.anki.ankiDeckGenerator import AnkiDeckGen
from scripts.anki.ankiKanjiNoteGenerator import AnkiKanjiNoteGen
from scripts.anki.ankiVocabNoteGenerator import AnkiVocabNoteGen
from anki.storage import Collection
from anki.notes import Note
from anki.errors import DBError
from datetime import datetime
import math
from pathlib import Path
import os
import re
from typing import NamedTuple
from collections import defaultdict
from scripts.anki.ankiConfig import AnkiConfig, DuplicateRemoveMode
import asyncio
ResultConflict = NamedTuple("ResultConflict", [("candidate", JishoResult), ("conflicting_notes", list[Note])])

class Ankifier():
    logger = logging.getLogger(__name__)
    def __init__(self, anki_config: AnkiConfig):
        self.config = anki_config
        self.duplicate_resolve_mode = anki_config.dupl_resolve
        self.kanji_model_name = "EZAnkiAdder-Kanji"
        self.vocab_model_name = "EZAnkiAdder-Vocab"
        self.col_path = self.findCollections() if not anki_config.col_path else anki_config.col_path
        self.furigana_timeout = anki_config.furigana_timeout
        self.min_meanings = anki_config.min_meanings
        self.min_sentences = anki_config.min_sentences
        if not Path(self.col_path).is_file():
            raise Ankifier.ColNotFound
    
    async def __aenter__(self):
        clearConsole()
        try:
            self.col = Collection(self.col_path)
        except DBError as e:
            raise Ankifier.AnkiAlreadyOpen
        print(italic(grey("Warming up Anki...")))
        model_gen = AnkiModelGen(self.col, self.vocab_model_name, self.kanji_model_name, self.config)
        self.models = model_gen.findModels()
        deck_gen = AnkiDeckGen(self.col)
        self.decks = deck_gen.findDecks()
        self.vocab_gen = AnkiVocabNoteGen(self.col, self.decks, self.models)
        self.kanji_gen = AnkiKanjiNoteGen(self.col, self.decks, self.models)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.col.close()

    async def checkAnkiIntegrity(self):
        clearConsole()
        print(italic(grey("Checking Anki integrity...")))
        await asyncio.to_thread(self.col.fix_integrity)
        print("Integrity check complete")

    def resolveNewKanjis(self, kanjis: list[str]):
        curr_kanji = [re.sub(r'<[^>]*>', '', self.col.get_note(n)["Kanji"]) for n in self.col.find_notes(f'note:{self.kanji_model_name}')]
        return [k for k in kanjis if not k in curr_kanji]
    
    def setDuplicateResolve(self):
        while self.duplicate_resolve_mode == DuplicateRemoveMode.NONE:
            clearConsole()
            print(grey("Select duplicate resolution mode"))
            print(bold("\t1. ") + f"Keep oldest {grey('(keeps learning data)')}")
            print(bold("\t2. ") + f"Keep newest {grey('(updates card but deletes learning data)')}")
            print(bold("\t3. ") + f"Transfer newest data to oldest {grey('(best of both worlds)')}")
            print(bold("\t4. ") + f"Select for each")
            response = re.match(r'^[1-4]$', input(grey(": ")))
            if response:
                self.duplicate_resolve_mode = DuplicateRemoveMode(int(response.group()) - 1)

    def transferNoteData(self, all_notes: list[Note], all_ids: list[int], new_notes: list[Note],  indices: list[int]):
        oldest_note = all_notes[indices[0]]
        newest_note = all_notes[indices[-1]]
        for field_name in newest_note.keys():
            if field_name in oldest_note and field_name != "Kanjis":
                oldest_note[field_name] = newest_note[field_name]
        if not oldest_note in new_notes:
            self.col.update_note(oldest_note)
        self.keepOldest(all_notes, all_ids, new_notes, indices)

    def keepOldest(self, all_notes: list[Note], all_ids: list[int], new_notes: list[Note],  indices: list[int]):
        for r in indices[1:]:
            if all_ids[r] == 0:
                new_notes.remove(all_notes[r])
        self.col.remove_notes([all_ids[i] for i in indices[1:]])

    def keepYoungest(self, all_notes: list[Note], all_ids: list[int], new_notes: list[Note],  indices: list[int]):
        for r in indices[:-1]:
            if all_ids[r] == 0:
                new_notes.remove(all_notes[r])
        self.col.remove_notes([all_ids[i] for i in indices[:-1]])


    def resolveConflictingVocab(self, new_notes: list[Note]) -> list[Note]:
        new_ids = [n.id for n in new_notes]
        def group_by(indices: list[int], values: list[str]):
            groups = defaultdict(list)
            for i in indices:
                groups[values[i]].append(i)
            return groups
        self.setDuplicateResolve()
        while True:
            clearConsole()
            print(italic(grey("Resovling duplicates")))
            def order_notes(n: Note):
                if not n.id:
                    return math.inf
                return n.id
            all_notes = sorted([self.col.get_note(n) for n in self.col.find_notes(f'note:{self.vocab_model_name}')] + new_notes, key=order_notes)
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
                                all_notes[i]["Expression"] = expr+ f'<span id="in_furi">【{furi}】</span>'
                                if not all_ids[i] in new_ids:
                                    notes_to_update.append(all_notes[i])
                    if notes_to_update:
                        self.col.update_notes(notes_to_update)                
                    # continue
                for furi_inds in furigana_groups.values():
                    # Meaning
                    meaning_groups = group_by(furi_inds, all_meanings)
                    if len(meaning_groups) > 1:
                        if self.duplicate_resolve_mode is DuplicateRemoveMode.SELECT:
                            self.selectMeaningDuplicate(furi_inds, new_notes, all_notes, all_compare_expr, all_expr, all_ids)
                        elif self.duplicate_resolve_mode is DuplicateRemoveMode.UPDATE:
                            self.transferNoteData(all_notes, all_ids, new_notes, furi_inds)
                        elif self.duplicate_resolve_mode is DuplicateRemoveMode.OLDEST:
                            self.keepOldest(all_notes, all_ids, new_notes, furi_inds)
                        elif self.duplicate_resolve_mode is DuplicateRemoveMode.NEWEST:
                            self.keepYoungest(all_notes, all_ids, new_notes, furi_inds)
                        deleted_notes = True
                        break
                    meaning_inds = next(iter(meaning_groups.values()))
                    # '<div class="meanings"><div class="m_tag">Godan verb - Iku/Yuku special class, Intransitive verb</div><div><span class="m_ind">1.</span><span class="m_mean">to go; to move (towards); to head (towards); to leave (for)</span></div><br/></div>'
                    # '<div class="meanings"><div class="m_tag">Godan verb - Iku/Yuku special class, Intransitive verb</div><div><span class="m_ind">1.</span><span class="m_mean">to go; to move (towards); to head (towards); to leave (for)</span></div><br></div>'
                    # Sentence
                    sentence_groups = group_by(meaning_inds, all_sentences)
                    if len(sentence_groups) > 1:
                        if self.duplicate_resolve_mode is DuplicateRemoveMode.SELECT:
                            self.selectSentenceDuplicate(meaning_inds, new_notes, all_notes, all_compare_expr, all_expr, all_ids)
                        elif self.duplicate_resolve_mode is DuplicateRemoveMode.UPDATE:
                            self.transferNoteData(all_notes, all_ids, new_notes, meaning_inds)
                        elif self.duplicate_resolve_mode is DuplicateRemoveMode.OLDEST:
                            self.keepOldest(all_notes, all_ids, new_notes, meaning_inds)
                        elif self.duplicate_resolve_mode is DuplicateRemoveMode.NEWEST:
                            self.keepYoungest(all_notes, all_ids, new_notes, meaning_inds)
                        # elif self.duplicate_resolve_mode is DuplicateRemoveMode.OLDEST:
                        #     for r in meaning_inds[1:]:
                        #         if all_ids[r] == 0:
                        #             new_notes.remove(all_notes[r])
                        #     self.col.remove_notes([all_ids[i] for i in meaning_inds[1:]])
                        # elif self.duplicate_resolve_mode is DuplicateRemoveMode.NEWEST:
                        #     for r in meaning_inds[:-1]:
                        #         if all_ids[r] == 0:
                        #             new_notes.remove(all_notes[r])
                        #     self.col.remove_notes([all_ids[i] for i in meaning_inds[:-1]])
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
        return new_notes


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
            
    def findCollections(self, config_files: list[str] = ['./searchConfig.txt', './scripts/scrappers/JLPTsearchConfig.txt']) -> Path:
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
            self.writeColPathInConfigFile(output, config_files)
            return output
        
        print(grey("Please select a Anki collection :"))
        for i, k in enumerate(data_bases.keys()):
            print("\t" + bold(f'{i}. {k}'))
        
        while True:
            response = re.match(r'\d+', input(grey(": ")))
            if response and int(response.group(0)) < len(data_bases.keys()):
                output = list(data_bases.values())[int(response.group(0))]
                for file in config_files:
                    self.writeColPathInConfigFile(output, file)
                return output
        
    @staticmethod
    def writeColPathInConfigFile(colpath: Path, config_file: Path):
        for conf_file in config_file:
            with open(conf_file, 'r') as f:
                lines = f.read()
            lines = re.sub(r'(?m:(?<=^anki_collection_file_path=).*$)', colpath.as_posix(), lines)
            with open(conf_file, 'w') as f:
                f.write(lines)  

    class ColNotFound(Exception):
        def __init__(self, *args):
            super().__init__(*args)
    class AnkiAlreadyOpen(Exception):
        def __init__(self, *args):
            super().__init__(*args)
import logging
import os
from scripts.scrappers import VocabScrapper, Scrapper
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.WARNING)
from scripts.scrappers.JishoSearchResult import word_audio_folder
from scripts.scrappers.NeocitiesScrapper import sentence_audio_folder
from scripts.scrappers.KanjiResults import image_folder
from scripts.utils.scrapperConfigParser import scrapperConfigParser
from scripts.anki.ankifier import Ankifier
import asyncio
import re

vocab_filepath = "./vocab2add.txt"
scrapperConfig_filepath = "./searchConfig.txt"

async def main():
    vocab_list = []
    if not os.path.isfile(vocab_filepath):
        with open(vocab_filepath, "w"):
            pass
    
    with open(vocab_filepath, "rb") as f:
        for line in f:
            try:
                word = line.decode()
                vocab_list.append(re.sub(r'(\r|\n)', '', word))
            except UnicodeDecodeError:
                pass
    

    if not os.path.isfile(vocab_filepath):
        scrapperConfig = {}
    else:
        config_parser = scrapperConfigParser(scrapperConfig_filepath)
        scrapperConfig = config_parser.parsedParams


    # return

    if not vocab_list:
        logger.warning("No words in search list, exiting...")
        quit()
    
    scrapper = VocabScrapper(max_display=config_parser.max_results_displayed)
    ankifier = Ankifier(config_parser.anki_col_path)
    async with scrapper:
        try:
            vocab_results = await scrapper.searchVocabList(vocab_list=vocab_list, **scrapperConfig)
            try:
                with ankifier:
                    conflicting_results = ankifier.conflictingVocab(vocab_results)
                    kanji_results = await scrapper.searchForKanjis([k for k in scrapper.all_kanjis if not k in ankifier.conflictingKanjis(scrapper.all_kanjis)])
                    new_vocab_notes = [ankifier.vocab_gen.genVocabNote(r) for r in vocab_results]
                    new_kanji_notes = [ankifier.kanji_gen.genKanjiNote(r) for r in kanji_results]
                    [ankifier.vocab_gen.submitNoteToVocabDeck(n) for n in new_vocab_notes]
                    [ankifier.kanji_gen.submitNoteToKanjiDeck(n) for n in new_kanji_notes]
            except Ankifier.ColNotFound:
                print("No Anki collection found, please change the 'anki_collection_file_path' in searchConfig.txt")
                return
        except Scrapper.Quit:
            logger.info("User exited early")
            
if __name__ == "__main__":
    asyncio.run(main())
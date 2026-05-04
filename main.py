import logging
import os
from scripts.scrappers.VocabScrapperClass import VocabScrapper
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.WARNING)
from scripts.scrappers.JishoSearchResult import audio_folder
from scripts.utils.scrapperConfigParser import scrapperConfigParser

vocab_filepath = "./vocab2add.txt"
scrapperConfig_filepath = "./searchConfig.txt"

def clearSoundFiles():
    for f in os.listdir(audio_folder):
        os.remove(audio_folder+f)

if __name__ == "__main__":
    clearSoundFiles()
    vocab_list = []
    if not os.path.isfile(vocab_filepath):
        with open(vocab_filepath, "w"):
            pass
    
    with open(vocab_filepath, "rb") as f:
        for line in f:
            try:
                word = line.decode()
                vocab_list.append(word)
            except UnicodeDecodeError:
                pass
    

    if not os.path.isfile(vocab_filepath):
        scrapperConfig = {}
    else:
        scrapperConfig = scrapperConfigParser(scrapperConfig_filepath)
        scrapperConfig = scrapperConfig.parsedParams

    if not vocab_list:
        logger.warning("No words in search list, exiting...")
        quit()
    
    scrapper = VocabScrapper()
    with scrapper:
        try:
            scrapper.searchVocabList(vocab_list=vocab_list, **scrapperConfig)
        except VocabScrapper.Quit:
            logger.info("Goodbye")
            
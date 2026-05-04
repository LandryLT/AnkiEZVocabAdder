import logging
import os
from scripts.scrappers.VocabScrapperClass import VocabScrapper
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.WARNING)
from scripts.scrappers.JishoSearchResult import audio_folder

def clearSoundFiles():
    for f in os.listdir(audio_folder):
        os.remove(audio_folder+f)

if __name__ == "__main__":
    clearSoundFiles()
    vocab_list = []
    if not os.path.isfile("./vocab2add.txt"):
        with open("./vocab2add.txt", "w"):
            pass
    with open("./vocab2add.txt", "rb") as f:
        for line in f:
            try:
                word = line.decode()
                vocab_list.append(word)
            except UnicodeDecodeError:
                pass
    
    if not vocab_list:
        logger.warning("No words in search list, exiting...")
        quit()
    
    scrapper = VocabScrapper()
    with scrapper:
        try:
            scrapper.searchVocabList(vocab_list)
        except VocabScrapper.Quit:
            logger.info("Goodbye")
            
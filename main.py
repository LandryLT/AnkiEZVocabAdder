import logging
import os
from scripts.scrappers import VocabScrapper, Scrapper
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.WARNING)
from scripts.scrappers.JishoSearchResult import audio_folder
from scripts.utils.scrapperConfigParser import scrapperConfigParser
import asyncio

vocab_filepath = "./vocab2add.txt"
scrapperConfig_filepath = "./searchConfig.txt"

def clearSoundFiles():
    for f in os.listdir(audio_folder):
        os.remove(audio_folder+f)

async def main():
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
        config_parser = scrapperConfigParser(scrapperConfig_filepath)
        scrapperConfig = config_parser.parsedParams

    if not vocab_list:
        logger.warning("No words in search list, exiting...")
        quit()
    
    scrapper = VocabScrapper(max_display=config_parser.max_results_displayed)
    async with scrapper:
        # print("Started")
        try:
            await scrapper.searchVocabList(vocab_list=vocab_list, **scrapperConfig)
        except Scrapper.Quit:
            logger.info("Goodbye")
            
if __name__ == "__main__":
    asyncio.run(main())
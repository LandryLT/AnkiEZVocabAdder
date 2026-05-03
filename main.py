import logging
import os
from VocabScrapper import VocabScrapper
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.WARNING)


if __name__ == "__main__":
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
            scrapper.decideManually(vocab_list)
        except KeyboardInterrupt:
            logger.info("Goodbye")
            
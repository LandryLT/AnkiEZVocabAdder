import logging
import os
from scripts.scrappers import VocabScrapper, Scrapper
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.CRITICAL)
from scripts.scrappers.JishoSearchResult import word_audio_folder
from scripts.scrappers.NeocitiesScrapper import sentence_audio_folder
from scripts.scrappers.KanjiResults import image_folder
from scripts.utils.scrapperConfigParser import scrapperConfigParser
from scripts.anki.ankifier import Ankifier
from scripts.utils.printingUtils import clearConsole, bold, italic, grey
import asyncio
import re
from tqdm import tqdm
from scripts.utils.printingUtils import tqdm_bar_format
from requests.exceptions import ConnectTimeout
from urllib3.exceptions import ReadTimeoutError

vocab_filepath = "./vocab2add.txt"
scrapperConfig_filepath = "./searchConfig.txt"

async def main():
    asyncio.get_event_loop().set_debug(False)
    vocab_list = []
    if not os.path.isfile(vocab_filepath):
        open(vocab_filepath, "w").close()
    
    with open(vocab_filepath, "rb") as f:
        for line in f:
            try:
                word = line.decode()
                vocab_list.append(re.sub(r'(\r|\n)', '', word))
            except UnicodeDecodeError:
                pass
    

    if not os.path.isfile(scrapperConfig_filepath):
        clearConsole()
        print(bold("ERROR: ") + f"Configuration file not found, there should be a {italic('scrapperConfig.txt')} ({italic('https://github.com/LandryLT/AnkiEZVocabAdder/blob/main/searchConfig.txt')}) file in the root folder of this program.")
        input(grey(f"Press {italic('Enter')}") + grey("key to exit..."))
        return
    else:
        config_parser = scrapperConfigParser(scrapperConfig_filepath)
        scrapperConfig = config_parser.parsedParams

    
    while True:
        try:
            async with Ankifier(config_parser.anki_config) as ankifier:
                async with VocabScrapper(max_display=config_parser.max_results_displayed) as scrapper:
                    # Check if you should clear cache on start
                    if config_parser.use_cache is None:
                        clearConsole()
                        response = input(f"{grey('Use cached data if found ? (')}{bold('y')}{grey('(es)|')}{bold('n')}{grey('(o)) : ')}")
                        config_parser.use_cache = re.match(r'\b(?i:y(es)?)\b', response) or not response
                    if not config_parser.use_cache:
                        scrapper.clearCache()
                    try:
                        while not vocab_list:
                            vocab_list = await scrapper.matome.fillVocab2AddWithJLPTN()                            
                        vocab_results = await scrapper.searchVocabList(vocab_list=vocab_list, **scrapperConfig)
                        try:
                            clearConsole()
                            print(italic(grey(f"Generating {len(vocab_results)} new vocabulary Anki note")))
                            new_vocab_notes = [ankifier.vocab_gen.genVocabNote(r) for r in tqdm(vocab_results, bar_format=tqdm_bar_format)]
                            new_vocab_notes = ankifier.resolveConflictingVocab(new_vocab_notes)
                            
                            kanji_results = await scrapper.searchForKanjis(ankifier.resolveNewKanjis(scrapper.all_kanjis))
                            new_kanji_notes = [ankifier.kanji_gen.genKanjiNote(r) for r in kanji_results]
                            [ankifier.kanji_gen.submitNoteToKanjiDeck(n) for n in new_kanji_notes]
                            kanjis_images = ankifier.kanji_gen.getKanjiNotes(scrapper.all_kanjis)
                            ankifier.vocab_gen.setKanjisStrokes(new_vocab_notes, kanjis_images, config_parser.anki_config.max_kanjis_meanings)
                            [ankifier.vocab_gen.submitNoteToVocabDeck(n) for n in new_vocab_notes]
                            
                            
                            # Clear cache
                            if config_parser.clear_cache_on_complete is None:
                                clearConsole()
                                response = input(f"{grey('Clear cached data ? :')}")
                                config_parser.clear_cache_on_complete = re.match(r'\b(?i:y(es)?)\b' , response) 
                            if config_parser.clear_cache_on_complete:
                                scrapper.clearCache()
                            # Clear vocablist
                            if config_parser.clear_vocab_on_complete is None:
                                clearConsole()
                                response = input(f"{grey('Clear vocab2add.txt ? :')}")
                                config_parser.clear_vocab_on_complete = re.match(r'\b(?i:y(es)?)\b' , response)
                            if config_parser.clear_vocab_on_complete:
                                with open(vocab_filepath, "w", encoding="utf-8") as f:
                                    f.write("\n".join(scrapper.jisho.no_results))
                            clearConsole()
                            has_new_notes = len(new_vocab_notes) + len(new_kanji_notes) > 0
                            if has_new_notes:
                                if new_vocab_notes:
                                    print(bold(grey("[NEW VOCAB NOTES]: ")))
                                    for i, n in enumerate(new_vocab_notes):
                                        print("\t" + f"{i+1}. {bold(re.sub(r'<[^<]*>', '', n['Expression']))}:" + "\t" + re.findall(r'<div class="m_mean">([^<]*)<\/div>', n['Meanings'])[0])
                                    print("")
                                if new_kanji_notes:
                                    print(bold(grey("[NEW KANJI NOTES]: ")) + ", ".join([bold(k["Kanji"]) for k in new_kanji_notes]) + "\n")
                                print(grey(f"Sucessfully added {bold(str(len(new_vocab_notes)))}") + grey(f" new Vocab' notes and {bold(str(len(new_kanji_notes)))}") + grey(" new Kanji notes to Anki.\n"))
                            else:
                                print(grey("No new notes added to Anki.\n"))
                            if scrapper.jisho.no_results:
                                print(grey(bold(f"But some search terms returned no results from {italic('jisho.org')}")))
                                print(grey("[") + f"{bold('NO RESULTS')}: {', '.join(scrapper.jisho.no_results)}" + grey("]"))
                                print(grey("Please check the spelling or ") + bold(grey("jlpt_filter")) + grey(f" in {italic('searchConfig.txt')}" + "\n"))
                            if has_new_notes:
                                print(grey(f"勉強頑張って！また今度ね ;)"))
                            else:
                                print(grey(f"またね"))
                            input(f"Press {italic('Enter')} to exit")
                            return
                        except (ConnectTimeout, ReadTimeoutError, TimeoutError) as e:
                            clearConsole()
                            print(f"{bold('ERROR')}: There seems to be a problem with the connection")
                            input(grey(f"Press ") + italic('Enter') + grey(" to see error : "))
                            print(e)
                            print("\n" + grey(f"Data is cached, you can pick up where you left next time"))
                            input(f"Press {italic('Enter')} to exit")
                            return
                    except Scrapper.Quit:
                        logger.info("User exited early")
                        clearConsole()
                        response = re.match(r'\b(?i:n(o)?)\b', input(f"{grey('Save to cache ? :')}"))
                        if response:
                            scrapper.clearCache()
                            return
                        print(grey(f"Data is cached, you can pick up where you left next time"))
                    input("\n" + f"Press {italic('Enter')} to exit")
                    return
        except Ankifier.ColNotFound:
            clearConsole()
            print(f"{bold('ERROR')}: No Anki collection found, please change the value of {italic(grey('anki_collection_file_path'))} in {italic('searchConfig.txt')} to your current {italic('collection.anki2')} path {grey('(ex:'+  italic('C:/Users/{...}/AppData/Roaming/Anki2/{...}/collection.anki2)') + 'for Windows')}")
            print(grey('(see: https://docs.ankiweb.net/files.html#user-data)\n'))
            input("\n" + f"Press {italic('Enter')} to exit")
            return
        except Ankifier.AnkiAlreadyOpen:
            clearConsole()
            input(f"{bold('ERROR')}: Anki seems to be already running, please close the Anki app and press {italic('Enter')} to resume")
            continue
        # except Exception as e:
        #     clearConsole()
        #     if hasattr(e, 'message'):
        #         print(e.message)
        #     else:
        #         print(e)
        #     print("\n" + grey(f"Data is cached, you can pick up where you left next time"))
        #     input(f"Press {italic('Enter')} to exit")
        #     return
                
if __name__ == "__main__":
    asyncio.run(main())
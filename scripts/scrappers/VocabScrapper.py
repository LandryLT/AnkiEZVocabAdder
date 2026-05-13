from scripts.utils.printingUtils import bold, italic, grey, clearConsole, tqdm_bar_format
import logging
from scripts.scrappers import NeocitiesSelectMode, JishoScrapper, NeocitiesScrapper, JishoSelectMode, JishoResult, NeocitiesResult, KanjiScrapper, KanjiResult
from playwright.async_api import async_playwright
from typing import NamedTuple
import random
from tqdm.asyncio import tqdm
import os
from scripts.scrappers.JishoSearchResult import word_audio_folder
from scripts.scrappers.NeocitiesScrapper import sentence_audio_folder
from scripts.scrappers.KanjiResults import image_folder

VocabScraperResult = NamedTuple('VocabScraperResult', [('jisho', JishoResult), ('neocities', list[NeocitiesResult])])

class VocabScrapper():
    logger = logging.getLogger(__name__)
    
    def __init__(self, max_display:int):
        self.max_rez_display = max_display
        self.all_kanjis = []

    def clearCache(self):
        self.jisho.clearCache()
        self.jisho_kanji.clearCache()
        self.neocities.clearCache()


    async def searchVocabList(self, vocab_list: list[str], 
                       jisho_mode: JishoSelectMode, 
                       neocities_mode: NeocitiesSelectMode,
                       printout_rez = False): 
        
        # Navigate through vocab list

        jisho_mode.setAutoselectExpressionMode()
        jisho_mode.setAutoSelectJLPTFilter()
        selected_expr = await self.jisho.selectExpressions(vocab_list, jisho_mode.autoselect_expression_mode, jisho_mode.is_exact_match_autoselect, jisho_mode.jlpt_filter)
        jisho_mode.setAudioAutoDownload()
        selected_expr = await self.jisho.downloadSounds(selected_expr, jisho_mode.enable_word_sound_download, jisho_mode.auto_download_sounds)
        jisho_mode.setAutoselectMeaningMode()
        selected_expr = await self.jisho.selectMeanings(selected_expr, jisho_mode.autoselect_meaning_mode)
        [expr.setUsuallyWrittenInKana() for expr in selected_expr]
        [[self.all_kanjis.append(k) for k in expr.kanjis] for expr in selected_expr]
        self.all_kanjis = list(set(self.all_kanjis))

        # Look for sentences
        await neocities_mode.setAutoMode()
        selected_sentences = await self.neocities.selectSentence(selected_expr, neocities_mode)
        selected_sentences = await self.neocities.downloadSounds(selected_sentences, neocities_mode.download_audio)
        selected_pairs = []
        for expr in selected_expr:
            for i, sen in enumerate(selected_sentences):
                if not sen:
                    selected_pairs.append((expr, []))                    
                    break
                if sen[0].jisho_uuid == expr.uuid:
                    selected_pairs.append((expr, selected_sentences.pop(i)))                    
                    break
            else:
                selected_pairs.append((expr, []))

        selected_rez = [VocabScraperResult(jisho, neocities) for jisho, neocities in selected_pairs]
        
        if not printout_rez:
            return selected_rez
        
        clearConsole()
        print(f'{bold("[SEARCH RESULTS]")}')
        for rez in selected_rez:
            has_audio = rez.jisho.soundfile != None
            has_jlpt = rez.jisho.JLPT > 0
            print('__________________________________________________________')
            print("\n"+f'{bold(rez.jisho.expression)} - {rez.jisho.furigana} ' + grey(('[' + ('\033[3mAudio\033[0m\033[2m' if has_audio else "")+(" - " if has_audio and has_jlpt else "")+("\033[3mJLPT N"+str(rez.jisho.JLPT)+"\033[0m\033[2m" if has_jlpt else "")+']') if has_audio or has_jlpt else ''))
            for i, definition in enumerate(rez.jisho.meanings):
                print("\t"+f'{grey(definition.tag)}')
                print("\t"+f'{i+1}. {definition.meaning}')
            
            if rez.neocities:
                random_sentence: NeocitiesResult = random.choice(rez.neocities)
                print(grey("\n\tExample sentence :"))
                NeocitiesScrapper.boldSearchTerm([random_sentence.japanese], random_sentence.search_term)
                print(italic("\t"+random_sentence.japanese))
                print(italic("\t"+random_sentence.english))

    async def searchForKanjis(self, kanjis: list[str]):
        all_kanji_rez: list[KanjiResult] = []
        for i, k in enumerate(kanjis):
            clearConsole()
            header = f'[{bold(k)}] ' + grey(f'({i}/{len(kanjis)} kanjis)') + "\n"
            all_kanji_rez.append(await self.jisho_kanji.jishoKanjiSearch(k, header))
        clearConsole()
        print(grey(italic(f"Downloading {len(all_kanji_rez)} kanji strokes images")))
        img_download_cors = [k.downloadImage() for k in all_kanji_rez]
        await tqdm.gather(*img_download_cors, bar_format=tqdm_bar_format)
        return all_kanji_rez

    async def __aenter__(self):
        self.logger.info("Launching Playwright...")
        self.driver = await async_playwright().start()
        self.browser = await self.driver.firefox.launch(headless=True)
        self.page = await self.browser.new_page()
        self.logger.info("Playwright Headless Firefox driver launched !")
        self.jisho = JishoScrapper(self.page, self.max_rez_display)
        self.neocities = NeocitiesScrapper(self.page, self.max_rez_display)
        self.jisho_kanji = KanjiScrapper(self.page, self.max_rez_display)

    async def __aexit__(self, exc_type, exc, tb):
        await self.browser.close()
        await self.driver.stop()
        self.logger.info("Playwright Headless Firefox driver closed !")
    

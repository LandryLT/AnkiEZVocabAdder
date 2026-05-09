from scripts.utils.printingUtils import bold, italic, grey, clearConsole
import logging
from scripts.scrappers import SentenceSelectMode, JishoScrapper, NeocitiesScrapper
from playwright.async_api import async_playwright


class VocabScrapper():
    logger = logging.getLogger(__name__)
    
    def __init__(self, max_display):
        self.max_rez_display = max_display
    
    async def searchVocabList(self, vocab_list: list[str], 
                       autoselect_expression_mode: JishoScrapper.SelectMode = JishoScrapper.SelectMode.NONE,
                       is_exact_match_autoselect: bool = None, 
                       autoselect_meaning_mode: JishoScrapper.SelectMode = JishoScrapper.SelectMode.NONE, 
                       autoselect_sentence_mode: SentenceSelectMode = None, 
                       enable_word_sound_download: bool = True,
                       auto_download_sounds: bool = None): 
            
        # Navigate through vocab list
        selected_expr = await self.jisho.selectExpressions(vocab_list, autoselect_expression_mode, is_exact_match_autoselect)
        selected_expr = await self.jisho.downloadSounds(selected_expr, enable_word_sound_download, auto_download_sounds)
        selected_expr = await self.jisho.selectMeanings(selected_expr, autoselect_meaning_mode)
        [expr.setUsuallyWrittenInKana() for expr in selected_expr]
        selected_expr = await self.neocities.selectSentence(selected_expr, autoselect_sentence_mode)
        
        clearConsole()
        print(f'{bold("[SEARCH RESULTS]")}')
        for expr in selected_expr:
            print(f'\n{bold(expr.expression)} - {expr.furigana}')
            for i, definition in enumerate(expr.meanings):
                print(f'{i+1}. {definition.meaning}')

    async def __aenter__(self):
        # options = Options()
        # options.add_argument("--headless=new")
        self.logger.info("Launching Playwright...")
        self.driver = await async_playwright().start()
        self.browser = await self.driver.firefox.launch(headless=True)
        self.page = await self.browser.new_page()
        self.logger.info("Playwright Headless Firefox driver launched !")
        self.jisho = JishoScrapper(self.page, self.max_rez_display)
        self.neocities = NeocitiesScrapper(self.page, self.max_rez_display)

    async def __aexit__(self, exc_type, exc, tb):
        await self.browser.close()
        await self.driver.stop()
        self.logger.info("Playwright Headless Firefox driver closed !")
    

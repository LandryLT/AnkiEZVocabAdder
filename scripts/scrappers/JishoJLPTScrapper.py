from scripts.scrappers.Scrapper import Scrapper, oopsable
from scripts.utils.printingUtils import clearConsole, italic, grey, bold, tqdm_bar_format
import re
from tqdm import tqdm

class JishoJLPTScrapper(Scrapper):
    def __init__(self, page, max_rez_display):
        super().__init__(page, max_rez_display)

    
    def promptForLevel(self) -> int:
        clearConsole()
        print(grey(f"No words in ") + grey(italic('vocab2add.txt')) + grey(", do you wish to bulk add vocabulary from a certain JLPT level ? "))
        while True:
            try:
                response = re.match(r'\d+', self._checkAbortResponse(grey("[") + bold("1 - 5") + grey("] or ") + bold("quit") + grey(": ")))
            except self.Oops:
                continue
            if response:
                response = int(response.group())
                if response >= 1 and response <= 5:
                    return response

    async def fillVocab2AddWithJLPTN(self) -> list[str]:
        level = self.promptForLevel()
        clearConsole()
        print(italic(grey(f'Loading from jisho.org\n')))
        output = []
        page_num = 1
        await self.page.goto(self._jishoJLPTsearch(level, page_num))
        await self.page.wait_for_function("() => document.querySelector('.result_count') != null", timeout=2000)
        max_rez = await self.page.evaluate("() => parseInt(document.querySelector('.result_count').innerText.match(/\d+/)[0])")
        with tqdm(total=max_rez, bar_format=tqdm_bar_format) as pbar:
            while True:
                if page_num > 1: 
                    await self.page.goto(self._jishoJLPTsearch(level, page_num))
                    await self.page.wait_for_function("() => (document.querySelector('.result_count') != null || document.querySelector('#no-matches') != null)", timeout=2000)
                rez = await self.page.evaluate("""() => {
                                                return [...document.querySelectorAll('.concept_light-representation > .text')].map(x => x.innerText)
                                               }                    
                """)
                if not rez:
                    break
                output.extend(rez)
                pbar.update(len(rez))
                page_num += 1
        return output
    
    @staticmethod
    def _jishoJLPTsearch(level: int, page: int) -> str:
        return f'https://jisho.org/search/%20%23jlpt-n{level}%20%23words?page={page}'
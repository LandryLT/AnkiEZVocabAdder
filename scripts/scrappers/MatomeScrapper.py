from scripts.scrappers.Scrapper import Scrapper, oopsable
from scripts.utils.printingUtils import clearConsole, italic, grey, bold, tqdm_bar_format
import re
from tqdm import tqdm

class MatomeScrapper(Scrapper):
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
        print(italic(grey(f'Loading from jlptmatome.com\n')))
        output = []
        page_num = 1
        await self.page.goto(self._matomesearch(level, page_num))
        await self.page.wait_for_function("() => document.querySelector('#top span + button') != null", timeout=2000)
        max_pages = await self.page.evaluate("() => parseInt(document.querySelector('#top span + button').textContent)")
        with tqdm(total=max_pages+1, bar_format=tqdm_bar_format) as pbar:
            while True:
                if page_num > 1: 
                    await self.page.goto(self._matomesearch(level, page_num))
                    await self.page.wait_for_function("() => document.querySelector('#top span + button') != null", timeout=2000)
                rez = await self.page.evaluate("""() => {
                                                        return [...document.querySelectorAll("#vocabulary-list > a > div > div > p:first-child")].map(x => x.textContent)
                                                    }
                """)
                if not rez:
                    break
                pbar.update(1)
                output.extend(rez)
                page_num += 1

        return output
    
    @staticmethod
    def _matomesearch(level: int, page: int):
        return f"https://www.jlptmatome.com/jlpt-n{level}-vocabulary-list?page={page}"
        
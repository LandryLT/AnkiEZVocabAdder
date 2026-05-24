from scripts.scrappers.Scrapper import Scrapper, oopsable
from scripts.utils.printingUtils import clearConsole, italic, grey, bold, tqdm_bar_format
import re
from tqdm import tqdm

class JishoJLPTScrapper(Scrapper):
    def __init__(self, page, max_rez_display):
        super().__init__(page, max_rez_display)

    
    def promptForLevel(self) -> list[int]:
        clearConsole()
        print(grey(f"No words in ") + grey(italic('vocab2add.txt')) + grey(", do you wish to bulk add vocabulary from a certain JLPT level ? "))
        output = []
        while True:
            try:
                response = self._checkAbortResponse(grey("[") + bold("1 - 5") + grey("] or ") + bold("quit") + grey(": "))
                if re.findall(r'\b[a-zA-Z]+\b', response):
                    if re.match(r'(?i:\ba(ll)?\b)', response):
                        output = list(range(1, 6))
                        break
                if re.match(r'^([ ]*\b[1-5]\b(,| |-)*)+$', response):
                    for a, b in re.findall(r'([1-5])[ ]*-[ ]*([1-5])', response):
                        output.extend(list(range(min(int(a), int(b)), max(int(a), int(b)) + 1)))
                    response = re.sub(r'[1-5][ ]*-[ ]*[1-5]', '',response)
                    output.extend([int(r) for r in re.findall(r'\b[1-5]\b', response) if int(r)])
                    break             
            except self.Oops:
                continue
        return output

    async def fillVocab2AddWithJLPTN(self) -> list[str]:
        level = self.promptForLevel()
        clearConsole()
        print(italic(grey(f'Loading from jisho.org\n')))
        output = []
        max_rez = 0
        for l in level:
            await self.page.goto(self._jishoJLPTsearch(l, 1))
            await self.page.wait_for_function("() => document.querySelector('.result_count') != null", timeout=2000)
            max_rez += await self.page.evaluate("() => parseInt(document.querySelector('.result_count').innerText.match(/\d+/)[0])")
        with tqdm(total=max_rez, bar_format=tqdm_bar_format) as pbar:
            for l in level:
                page_num = 1
                while True:
                    await self.page.goto(self._jishoJLPTsearch(l, page_num))
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
from .Scrapper import Scrapper
from .KanjiResults import KanjiResults, KanjiResultsRaw
from scripts.utils.printingUtils import clearConsole, italic, grey

class KanjiScrapper(Scrapper):
    def __init__(self, page, max_rez_display):
        super().__init__(page, max_rez_display)
    
    async def jishoKanjiSearch(self, kanji:str, header: str):
        clearConsole()
        print(header)
        print(italic(grey(f'Loading kanji from jisho.org...\n')))
        await self.page.goto(self._jishokanjisearch(kanji))
        dict_rez = await self.page.evaluate("""() => {
                                        const rez = document.querySelector('#main_results .kanji.details  > .row:nth-of-type(1)')
                                        const compounds = document.querySelectorAll('#main_results .kanji.details  > .row:nth-of-type(3) .compounds > div')
                                        function getCompounds(elems) {
                                            output = {}
                                            for (c of elems){
                                                if (c.querySelector('h2').innerText.includes("Kun")){
                                                    output["kun"] = [...c.querySelectorAll('li')].map(x => x.innerText)
                                                } else if (c.querySelector('h2').innerText.includes("On")){
                                                    output["on"] = [...c.querySelectorAll('li')].map(x => x.innerText)
                                                }
                                            }
                                            return output
                                        }

                                        return {
                                            meaning: rez.querySelector('.kanji-details__main-meanings')?.innerText ?? '',
                                            on_yomi: [...rez.querySelectorAll('dl.dictionary_entry.on_yomi .kanji-details__main-readings-list > a')].map(x => x.innerText),
                                            kun_yomi: [...rez.querySelectorAll('dl.dictionary_entry.kun_yomi .kanji-details__main-readings-list > a')].map(x => x.innerText),
                                            jlpt: parseInt((rez.querySelector('.jlpt > strong')?.innerText ?? 'N0').replace('N', '')),
                                            ranking: rez.querySelector('.frequency')?.innerText ?? null,
                                            compounds: getCompounds(compounds)
                                        }
                                    }""")
        return KanjiResults(kanji, KanjiResultsRaw(**dict_rez))
    
    @staticmethod
    def _jishokanjisearch(term: str) -> str:
        return f'https://jisho.org/search/{term}%23kanji'
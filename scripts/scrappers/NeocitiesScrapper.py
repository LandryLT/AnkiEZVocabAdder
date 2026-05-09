from scripts.scrappers.Scrapper import Scrapper, oopsable
from scripts.scrappers.JishoSearchResult import JishoResult
from scripts.scrappers.NeocitiesSelectMode import SentenceSelectMode
from scripts.utils.printingUtils import bold, italic, grey, clearConsole, tqdm_bar_format
import re
from tqdm.asyncio import tqdm
from collections import namedtuple

NeocitiesResult = namedtuple('NeocitiesResult', ["japanese", "english", "audio_link"])

class NeocitiesScrapper(Scrapper):  
    def __init__(self, page, max_rez_display):
        super().__init__(page, max_rez_display)
        
    @oopsable()
    async def selectSentence(self, selected_expr: list[JishoResult], mode: SentenceSelectMode = None) -> list[JishoResult]:
        clearConsole()
        while mode == None or mode.mode == SentenceSelectMode.SelectMode.NONE:
            clearConsole()
            new_mode = SentenceSelectMode()
            if re.match(r'(?i:^y(es)?$)', self._checkAbortResponse(grey('Enable \033[1mauto-select sentences\033[0m\033[2m ? ') + f"({bold('y')}|{bold('n')}) {grey(':')} ")) != None:
                new_mode.mode = SentenceSelectMode.SelectMode.AUTO
                new_mode.setAutoMode()
            else:
                new_mode.mode = SentenceSelectMode.SelectMode.MANUAL

            mode = new_mode

        output = selected_expr.copy()
        selected_sentences = []
        expression_question = True
        for i, expression in enumerate(selected_expr):
            search_terms = [expression.expression]+expression.getFlattenedListOfInflection()+[expression.furigana if expression.usually_kana else None]
            search_term = f'{"|".join([st for st in search_terms if st])}'
            neocities_rez = await self.neo_cities_search_term(search_term, expression.expression, f'[{expression.search_term} - {bold(expression.expression)}] {grey(f"({i + 1}/{len(output)} sentences to set)")}\n')
            if not neocities_rez:
                continue
            clearConsole()
            if mode.mode == SentenceSelectMode.SelectMode.MANUAL:
                choices = [f'{s.japanese}\n\t\t{s.english}\n' for s in neocities_rez]
                for ind, choice in enumerate(choices):
                    for m in list(re.finditer(re.compile(search_term), choice))[::-1]:
                        choice = choice[:m.start()] + bold(choice[m.start():m.end()]) + choice[m.end():]
                    choices[ind] = choice
                self.promptForSelection(choices=choices,
                                        input_text=(grey("Sentences indices to keep ") + f"({grey('ex:')} {bold('0, 2, 7')} {grey('or')} {bold('a')} {grey('or')} {bold('none')}) " if expression_question else "") + ": ",
                                        header=f'[{expression.search_term} - {bold(expression.expression)} ({expression.furigana})] {grey(f"({i + 1}/{len(output)} sentences to set)")}\n{grey(italic(expression.meanings[0].meaning))}\n',
                                        callback=lambda i: selected_sentences.append(neocities_rez[i]))
                expression_question = False
        return output

    
    async def neo_cities_search_term(self, search_term: str, expression: str, header: str) -> list[NeocitiesResult]:
        clearConsole()
        print(italic(grey(f'Loading sentencesearch.neocities.org...')))
        await self.page.goto(self._neocitiessearch(search_term))
        if not await self.page.evaluate("() => document.querySelector('#results-info').checkVisibility()"):
            await self.page.locator("#searchButton").click()
            await self.page.wait_for_function("() => document.querySelector('#results-info').checkVisibility()")
        total_results = int(await self.page.evaluate("document.querySelector('#num-results').innerText"))
        clearConsole()
        print(header)
        if not total_results:
            self.logger.warning(f'Searching for {bold(f"{expression} returned no results")}, skipping...')
            return []

        clearConsole()
        print(header)        
        return await self.load_all_neocities_results()

    async def load_all_neocities_results(self)  -> list[NeocitiesResult]:
        previous_count = 0
        total_rez = int(await self.page.evaluate("() => {return document.querySelector('#num-results').innerText}"))
        print(grey(f'Gathering {total_rez} sentences from {italic("sentencesearch.neocities.org...")}'))
        with tqdm(total=total_rez, bar_format=tqdm_bar_format+grey(' [{n_fmt}/{total_fmt}]')) as pbar:
            while True:
                current_count = await self.page.evaluate("() => {return document.querySelectorAll('#search-results-list .search-result').length}")
                pbar.update(current_count - previous_count)
                if current_count == previous_count:
                    break
                previous_count = current_count
                await self.page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
                try:
                    await self.page.wait_for_function(
                        expression="prev => {return document.querySelectorAll('#search-results-list .search-result').length > prev}",
                        arg=previous_count,
                        timeout=1500
                    )
                except:
                    break
            output = await self.page.evaluate("""
            () => {
                return [...document.querySelectorAll('#search-results-list .search-result')]
                    .map(el => ({
                        japanese: el.querySelector('.jap')?.innerText || '',
                        english: el.querySelector('.eng')?.innerText || '',
                        audio_link: el.querySelector('.audioButton')?.href || ''
                    }))
                    .filter(x => x.japanese && x.english);
            }
            """)

        return [NeocitiesResult(**rez) for rez in output]
            
    @staticmethod
    def _neocitiessearch(term: str) -> str:
        return f'https://sentencesearch.neocities.org/#{term}'
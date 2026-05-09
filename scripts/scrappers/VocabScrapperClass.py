from scripts.utils.printingUtils import bold, italic, grey, clearConsole
from typing import Callable
import logging
# from scrappers import JishoSearchResultElement
from scripts.scrappers import JishoResult, JishoSearchResultRaw
# from scripts.scrappers import NeocitiesSearchResultElement, SentenceSelectMode, JishoSearchResultElement
from scripts.scrappers import SentenceSelectMode, NeocitiesResult
from re import match, findall, finditer, compile
from time import sleep
from enum import Enum
import math

from tqdm.asyncio import tqdm, trange
tqdm_bar_format = grey('{desc}: {percentage:3.0f}%|{bar:20}|')

import functools
import asyncio
from playwright.async_api import async_playwright


def oopsable():
    def wrapper(f):
        @functools.wraps(f)
        async def wrap(*args, **kwargs):
            while True:
                try:
                    return await f(*args, **kwargs)
                except VocabScrapper.Oops:
                    continue
        return wrap
    return wrapper

class VocabScrapper():
    logger = logging.getLogger(__name__)
    class SelectMode(Enum):
        NONE = -1
        FIRST = 0
        SELECT = 1
        ALL = 2

    class Quit(Exception):
        def __init__(self, *args):
            super().__init__(*args)

    class Oops(Exception):
        def __init__(self, *args):
            super().__init__(*args)
    
    def __init__(self, max_display):
        self.max_rez_display = max_display
    
    async def searchVocabList(self, vocab_list: list[str], 
                       autoselect_expression_mode: SelectMode = SelectMode.NONE,
                       is_exact_match_autoselect: bool = None, 
                       autoselect_meaning_mode: SelectMode = SelectMode.NONE, 
                       autoselect_sentence_mode: SentenceSelectMode = None, 
                       enable_word_sound_download: bool = True,
                       auto_download_sounds: bool = None):     
        # Navigate through vocab list
        selected_expr = await self.selectExpressions(vocab_list, autoselect_expression_mode, is_exact_match_autoselect)
        selected_expr = await self.downloadSounds(selected_expr, enable_word_sound_download, auto_download_sounds)
        selected_expr = await self.selectMeanings(selected_expr, autoselect_meaning_mode)
        selected_expr = await self.selectSentence(selected_expr, autoselect_sentence_mode)
        
        clearConsole()
        print(f'{bold("[SEARCH RESULTS]")}')
        for expr in selected_expr:
            print(f'\n{bold(expr.expression)} - {expr.furigana}')
            for i, definition in enumerate(expr.meanings):
                print(f'{i+1}. {definition.meaning}')

    @oopsable()
    async def selectExpressions(self, vocab_list: list[str], mode: SelectMode = None, is_exact_match_autoselect: bool = False) -> list[JishoResult]:
        # Auto-select expression mode
        clearConsole()
        while mode == self.SelectMode.NONE:
            clearConsole()
            print(grey("Auto-select \033[1mexpression\033[0m\033[2m mode"))
            print(f"\t{bold('1')}. First only")
            print(f"\t{bold('2')}. Select")
            print(f"\t{bold('3')}. All")
            response = match(r'([1-3]|oops)', self._checkAbortResponse(f'{grey("Select mode")} ({bold("1")}|{bold("2")}|{bold("3")}) {grey(": ")}'))
            if response:
                mode = self.SelectMode(int(response.group(0))-1)
                self.logger.info(f"Auto-selecting expression mode is {mode.name}")
            # Auto-select exact match
            if mode == self.SelectMode.SELECT:
                response = self._checkAbortResponse(f"\n{grey('Enable auto-selecting only exact matches ?')} ({bold('y')}|{bold('n')}) {grey(':')} ")
                is_exact_match_autoselect = match(r'(?i:^y(es)?$)', response) != None
                self.logger.info(f"Auto-selecting exact matches is {'en' if is_exact_match_autoselect else 'dis'}abled")
        
        output = []
        expression_question = True
        # Go through vocab list
        for word_ind, word in enumerate(vocab_list):
            word = word.replace('\r\n', "")
            header = f'[{bold(word)}] {grey(f"({word_ind + 1}/{len(vocab_list)} search terms)")}\n'
            jisho_results = await self.jishoSearchTerm(word, header)
            clearConsole()
            print(f'[{bold(word)}] {grey(f"({word_ind + 1}/{len(vocab_list)} search terms)")}\n')
            
            # No results
            if not jisho_results:
                continue
            # Exact match and auto-select
            if mode == self.SelectMode.FIRST or (mode == self.SelectMode.SELECT and is_exact_match_autoselect and jisho_results[0].is_exact_match) or len(jisho_results) == 1:
                if jisho_results[0].is_exact_match:
                    self.logger.warning(f"Found exact match for {word} !")
                output.append(jisho_results[0])
                continue
            elif mode == self.SelectMode.ALL:
                [output.append(rez) for rez in jisho_results]
                continue

            self.promptForSelection(choices=[f"{bold(expr.expression)} ({expr.romaji}):\t\"{italic(expr.meanings[0].meaning)}\" {grey(f'(1/{len(expr.meanings)} meanings)')}" for expr in jisho_results], 
                                    input_text=(grey("Expressions indices to keep ") + f"({grey('ex:')} {bold('0, 2, 7')} {grey('or')} {bold('a')} {grey('or')} {bold('none')}) " if expression_question else "") + ": ",
                                    header=header+grey(f"\nPlease select expressions to keep"),
                                    callback=lambda i: output.append(jisho_results[i]))
            
            expression_question = False
        return output
    
    @oopsable()
    async def downloadSounds(self, selected_expr: list[JishoResult], enable:bool = True, auto_download: bool = None) -> list[JishoResult]:
        output = selected_expr.copy()
        expr_with_links = [expr for expr in output if expr.soundlink]
        if not enable:
            return output
        clearConsole()
        if not expr_with_links:
            self.logger.info("No soundlinks found in selected expressions, skipping...")
            return output
        if auto_download == None:
            auto_download = match(r'(?i:^y(es)?$)', self._checkAbortResponse(grey('\033[1mAuto-download sound\033[0m\033[2m when found ?') + f"({bold('y')}|{bold('n')}) {grey(':')} ")) != None
            self.logger.info(f"Auto-downloading sound is {'en' if auto_download else 'dis'}abled")
        
        if auto_download:
            print(grey(italic(f'Downloading {len(expr_with_links)} audio files...\n')))
            download_cors = [e.downloadSound() for e in expr_with_links]
            await tqdm.gather(*download_cors, bar_format=tqdm_bar_format)
            return output
        
        for i, expression in enumerate(expr_with_links):
            clearConsole()
            print(f'[{expression.search_term} - {bold(expression.expression)}] {grey(f"({i + 1}/{len(expr_with_links)} sounds to download)")}\n')
            if match(r'(?i:^y(es)?$)', self._checkAbortResponse(grey('Skip this file ? ') + f"({bold('y')}|{bold('n')}) {grey(':')} ")) != None:
                continue
            clearConsole()
            print(f'[{expression.search_term} - {bold(expression.expression)}] {grey(f"({i + 1}/{len(expr_with_links)} sounds to download)")}\n')
            print(italic(grey(f'Downloading audio from jisho.org')))
            await expression.downloadSound()
        return output
        
    @oopsable()
    async def selectMeanings(self, selected_expr: list[JishoResult], mode: SelectMode = SelectMode.SELECT) -> list[JishoResult]:
        # Auto-select meanings mode
        while mode == self.SelectMode.NONE:
            clearConsole()
            print(grey("Auto-select \033[1mmeaning\033[0m\033[2m mode"))
            print(f"\t{bold('1')}. First only")
            print(f"\t{bold('2')}. Select")
            print(f"\t{bold('3')}. All")
            response = match(r'[1-3]', self._checkAbortResponse(f'{grey("Select mode")} ({bold("1")}|{bold("2")}|{bold("3")}) {grey(": ")}'))
            if response:
                mode = self.SelectMode(int(response.group(0))-1)
                self.logger.info(f"Auto-selecting definition mode is {mode.name}")

        
        output = selected_expr.copy()
        expression_question = True
        for i, expression in enumerate(output):
            clearConsole()
            print()
            if mode == self.SelectMode.SELECT and len(expression.meanings) > 1:
                selected_def = []
                self.promptForSelection(choices=[f"{italic(m.meaning)}" for m in expression.meanings], 
                                        input_text=(grey("Meanings indices to keep ") + f"({grey('ex:')} {bold('0, 2, 7')} {grey('or')} {bold('a')}) " if expression_question else "") + ": ",
                                        header=f'[{expression.search_term} - {bold(expression.expression)}] {grey(f"({i + 1}/{len(output)} expressions to check)")}\n'+
                                                    grey(f"\nPlease select meanings to keep"),
                                        callback=lambda i: selected_def.append(expression.meanings[i]),
                                        use_none=False)
                expression_question = False
                expression.meanings = selected_def

            elif mode == self.SelectMode.FIRST:
                expression.meanings = [expression.meanings[0]]

            self.logger.debug(f"{[{expression.search_term} - {bold(expression.expression)}]}'s meanings: {expression.meanings}")
        return output
    
    @oopsable()
    async def selectSentence(self, selected_expr: list[JishoResult], mode: SentenceSelectMode = None) -> list[JishoResult]:
        clearConsole()
        while mode == None or mode.mode == SentenceSelectMode.SelectMode.NONE:
            clearConsole()
            new_mode = SentenceSelectMode()
            if match(r'(?i:^y(es)?$)', self._checkAbortResponse(grey('Enable \033[1mauto-select sentences\033[0m\033[2m ? ') + f"({bold('y')}|{bold('n')}) {grey(':')} ")) != None:
                new_mode.mode = SentenceSelectMode.SelectMode.AUTO
                new_mode.setAutoMode()
            else:
                new_mode.mode = SentenceSelectMode.SelectMode.MANUAL

            mode = new_mode

        output = selected_expr.copy()
        selected_sentences = []
        expression_question = True
        for i, expression in enumerate(selected_expr):
            search_term = f'{"|".join([expression.expression]+expression.getFlattenedListOfInflection())}'
            neocities_rez = await self.neo_cities_search_term(search_term, expression.expression, f'[{expression.search_term} - {bold(expression.expression)}] {grey(f"({i + 1}/{len(output)} sentences to set)")}\n')
            if not neocities_rez:
                continue
            clearConsole()
            if mode.mode == SentenceSelectMode.SelectMode.MANUAL:
                choices = [f'{s.japanese}\n\t\t{s.english}\n' for s in neocities_rez]
                for ind, choice in enumerate(choices):
                    for m in list(finditer(compile(search_term), choice))[::-1]:
                        choice = choice[:m.start()] + bold(choice[m.start():m.end()]) + choice[m.end():]
                    choices[ind] = choice
                self.promptForSelection(choices=choices,
                                        input_text=(grey("Sentences indices to keep ") + f"({grey('ex:')} {bold('0, 2, 7')} {grey('or')} {bold('a')} {grey('or')} {bold('none')}) " if expression_question else "") + ": ",
                                        header=f'[{expression.search_term} - {bold(expression.expression)}] {grey(f"({i + 1}/{len(output)} sentences to set)")}\n',
                                        callback=lambda i: selected_sentences.append(neocities_rez[i]))
                expression_question = False
        return output

    async def jishoSearchTerm(self, search_term: str, header: str) -> list[JishoResult]:
        clearConsole()
        print(header)
        print(italic(grey(f'Loading from jisho.org...\n')))
        await self.page.goto(self._jishosearch(search_term))
        dict_rez = await self.page.evaluate("""() => {
                                                function getDomPath(el) {
                                                    if (!(el instanceof Element)) return null;
                                                    const path = [];
                                                    while (el && el.nodeType === Node.ELEMENT_NODE) {
                                                        let selector = el.nodeName.toLowerCase();

                                                        // Prefer ID if available
                                                        if (el.id) {
                                                        selector += `#${CSS.escape(el.id)}`;
                                                        path.unshift(selector);
                                                        break;
                                                        }

                                                        // Add classes
                                                        if (el.classList.length) {
                                                        selector += [...el.classList]
                                                            .map(cls => `.${CSS.escape(cls)}`)
                                                            .join('');
                                                        }

                                                        // Add nth-of-type for uniqueness
                                                        let sibling = el;
                                                        let nth = 1;

                                                        while ((sibling = sibling.previousElementSibling)) {
                                                        if (sibling.nodeName === el.nodeName) nth++;
                                                        }

                                                        selector += `:nth-of-type(${nth})`;

                                                        path.unshift(selector);
                                                        el = el.parentElement;
                                                    }

                                                    return path.join(' > ');
                                                }
                                                return [...document.querySelectorAll('#primary > div > div')].map((el) => ({
                                                    expression: el.querySelector('.text')?.innerText ?? '',
                                                    furiganas: [...el.querySelectorAll('.furigana .kanji')].map(x => x.innerText),
                                                    meanings: [...el.querySelectorAll('.concept_light-meanings .meanings-wrapper')].map(m => ({
                                                        tag: m.querySelector('.meaning-tags')?.innerText ?? '',
                                                        meaning: m.querySelector('.meaning-meaning')?.innerText ?? ''
                                                    })),
                                                    tags: [...el.querySelectorAll('.concept_light-tag')].map(x => x.innerText),
                                                    soundlink: el.querySelector('source[type="audio/mpeg"]')?.src ?? null,
                                                    inflectionlink: getDomPath(el.querySelector('.show_inflection_table')) ?? null
                                                }))
                                            }""")
        output = [JishoResult(JishoSearchResultRaw(**rez), search_term) for rez in dict_rez]
        [await rez.queryInflection(self.page) for rez in output]
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

    def promptForSelection(self, choices: list[str], input_text: str, header: str, callback: Callable[[int], None], use_none: bool = True):
        start_index = 0
        num_of_choices = len(choices)
        while True:
            clearConsole()
            print(header)
            end_index = start_index + self.max_rez_display
            for i, choice in enumerate(choices[start_index: min(end_index, num_of_choices)]):
                print(f"\t{bold(str(i+start_index))}.\t{choice}")
            if num_of_choices > self.max_rez_display:
                print(grey(f'[{start_index}-{min(end_index, num_of_choices)-1}/{num_of_choices}]') +
                      f'({italic("Enter")}: {grey("next choices")} | p: {grey("prev. choices ")})')
            response = VocabScrapper._checkAbortResponse(input_text).replace(" ", "")
            if not response:
                start_index = 0 if end_index >= num_of_choices else (self.max_rez_display + start_index) % num_of_choices
                continue
            if findall(r'\b[a-zA-Z]+\b', response):
                if match(r'\bp\b', response):
                    start_index = start_index - self.max_rez_display
                    if start_index < 0:
                        start_index = int(math.floor(num_of_choices/(self.max_rez_display))*self.max_rez_display)
                    continue
                if match(r'\ba\b', response):
                    output = list(range(len(choices)))
                    break
                if match(r'(?i:\bnone\b)', response) and use_none:
                    output = []
                    break
            if match(r'^((,| )*\b\d+\b(,| )*)+$', response):
                output = [int(r) for r in findall(r'\b\d+\b', response)]
                break
        [callback(i) if i < len(choices) else "" for i in output]
        return
            
    async def __aenter__(self):
        # options = Options()
        # options.add_argument("--headless=new")
        self.logger.info("Launching Playwright...")
        self.driver = await async_playwright().start()
        self.browser = await self.driver.firefox.launch(headless=True)
        self.page = await self.browser.new_page()
        self.logger.info("Playwright Headless Firefox driver launched !")

    async def __aexit__(self, exc_type, exc, tb):
        await self.browser.close()
        await self.driver.stop()
        self.logger.info("Playwright Headless Firefox driver closed !")

    @staticmethod
    def _jishosearch(term: str) -> str:
        return f'https://jisho.org/search/{term}'
    
    @staticmethod
    def _neocitiessearch(term: str) -> str:
        return f'https://sentencesearch.neocities.org/#{term}'

    @staticmethod
    def _checkAbortResponse(request: str) -> str:
        response = input(request)
        if response == "oops":
            raise VocabScrapper.Oops
        elif response == "quit":
            raise VocabScrapper.Quit
        return response
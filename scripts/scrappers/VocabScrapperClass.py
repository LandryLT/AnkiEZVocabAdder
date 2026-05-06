from selenium.webdriver import Firefox
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from scripts.utils.printingUtils import bold, italic, grey, clearConsole
from typing import Callable

import logging
# from scrappers import JishoSearchResultElement
from scripts.scrappers import NeocitiesSearchResultElement, SentenceSelectMode, JishoSearchResultElement
from re import match, findall, finditer, compile
from time import sleep
from enum import Enum
import math
import asyncio

from concurrent.futures import ThreadPoolExecutor

def oopsable(f):
    def wrap(*args, **kwargs):
        while True:
            try:
                return f(*args, **kwargs)
            except VocabScrapper.Oops:
                continue
    return wrap

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
    
    def searchVocabList(self, vocab_list: list[str], 
                       autoselect_expression_mode: SelectMode = SelectMode.NONE,
                       is_exact_match_autoselect: bool = None, 
                       autoselect_meaning_mode: SelectMode = SelectMode.NONE, 
                       autoselect_sentence_mode: SentenceSelectMode = None, 
                       enable_word_sound_download: bool = True,
                       auto_download_sounds: bool = None):     
        # Navigate through vocab list
        selected_expr = self.selectExpressions(vocab_list, autoselect_expression_mode, is_exact_match_autoselect)
        selected_expr = self.downloadSounds(selected_expr, enable_word_sound_download, auto_download_sounds)
        selected_expr = self.selectMeanings(selected_expr, autoselect_meaning_mode)
        selected_expr = self.selectSentence(selected_expr, autoselect_sentence_mode)
        
        clearConsole()
        print(f'{bold("[SEARCH RESULTS]")}')
        for expr in selected_expr:
            print(f'\n{bold(expr.expression)} - {expr.furigana}')
            for i, definition in enumerate(expr.meanings):
                print(f'{i+1}. {definition.meaning}')

    @oopsable
    def selectExpressions(self, vocab_list: list[str], mode: SelectMode = None, is_exact_match_autoselect: bool = False) -> list[JishoSearchResultElement]:
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
            jisho_results = self.jishoSearchTerm(word, header)
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
            
            # num_of_results = len(jisho_results)
            # # Too many results
            # if num_of_results > 10:
            #     response = self._checkAbortResponse(grey(f'{num_of_results} results, how many to display ? '))

            #     response = match(r'^\d+$', response)
            #     num_of_choices = num_of_results if response == None else int(response.group(0))
            #     jisho_results = jisho_results[:min(num_of_choices, num_of_results)]


            print()
            self.promptForSelection(choices=[f"{bold(expr.expression)} ({expr.romaji}):\t\"{italic(expr.meanings[0].meaning)}\" {grey(f'(1/{len(expr.meanings)} meanings)')}" for expr in jisho_results], 
                                    input_text=grey("Expressions indices to keep ") + (f"({grey('ex:')} {bold('0, 2, 7')} {grey('or')} {bold('a')}) " if expression_question else "") + ": ",
                                    header=grey(f"Please select expressions to keep"),
                                    callback=lambda i: output.append(jisho_results[i]))
            
            # expression_question = False
        return output
    
    @oopsable
    def downloadSounds(self, selected_expr: list[JishoSearchResultElement], enable:bool = True, auto_download: bool = None):
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
        for i, expression in enumerate(expr_with_links):
            clearConsole()
            print(f'[{expression.search_term} - {bold(expression.expression)}] {grey(f"({i + 1}/{len(expr_with_links)} sounds to download)")}\n')
            if not auto_download and match(r'(?i:^y(es)?$)', self._checkAbortResponse(grey('Skip this file ? ') + f"({bold('y')}|{bold('n')}) {grey(':')} ")) != None:
                continue
            clearConsole()
            print(f'[{expression.search_term} - {bold(expression.expression)}] {grey(f"({i + 1}/{len(expr_with_links)} sounds to download)")}\n')
            print(italic(grey(f'Downloading audio from jisho.org')))
            expression.downloadSound()
        return output
        
    @oopsable
    def selectMeanings(self, selected_expr: list[JishoSearchResultElement], mode: SelectMode = SelectMode.SELECT) -> list[JishoSearchResultElement]:
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
        for i, expression in enumerate(output):
            clearConsole()
            print(f'[{expression.search_term} - {bold(expression.expression)}] {grey(f"({i + 1}/{len(output)} expressions to check)")}\n')
            if mode == self.SelectMode.SELECT and len(expression.meanings) > 1:
                selected_def = []
                self.promptForSelection(choices=[f"{italic(m.meaning)}" for m in expression.meanings], 
                                        input_text=grey(": "),
                                        header=grey(f"Please select meanings to keep"),
                                        callback=lambda i: selected_def.append(expression.meanings[i]))
                expression.meanings = selected_def

            elif mode == self.SelectMode.FIRST:
                expression.meanings = [expression.meanings[0]]

            self.logger.debug(f"{[{expression.search_term} - {bold(expression.expression)}]}'s meanings: {expression.meanings}")
        return output
    
    @oopsable
    def selectSentence(self, selected_expr: list[JishoSearchResultElement], mode: SentenceSelectMode = None) -> list[JishoSearchResultElement]:
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
        
        for i, expression in enumerate(selected_expr):
            search_term = f'{"|".join([expression.expression]+expression.getFlattenedListOfInflection())}'
            neocities_rez = self.neocitiesSearchTerm(search_term, expression.expression, f'[{expression.search_term} - {bold(expression.expression)}] {grey(f"({i + 1}/{len(output)} sentences to set)")}\n')
            if not neocities_rez:
                continue
            clearConsole()
            if mode.mode == SentenceSelectMode.SelectMode.MANUAL:
                choices = [f'{s.japanese}\n\t\t{s.english}\n' for s in neocities_rez]
                for ind, choice in enumerate(choices):
                    for match in list(finditer(compile(search_term), choice))[::-1]:
                        choice = choice[:match.start()] + bold(choice[match.start():match.end()]) + choice[match.end():]
                    choices[ind] = choice
                self.promptForSelection(choices=choices,
                                        input_text=': ',
                                        header=f'[{expression.search_term} - {bold(expression.expression)}] {grey(f"({i + 1}/{len(output)} sentences to set)")}\n',
                                        callback=lambda i: selected_sentences.append(neocities_rez[i]))
        return output

    def jishoSearchTerm(self, search_term: str, header: str) -> list[JishoSearchResultElement]:
        clearConsole()
        print(header)
        print(italic(grey(f'Loading from jisho.org...')))
        self.driver.get(self._jishosearch(search_term))
        search_results = self.driver.find_element(By.ID, "primary").find_elements(By.XPATH, "./div/div")
        if not search_results:
            self.logger.warning(f'Searching for {bold(f"{search_term} returned no results")}, skipping...')
            return
        
        self.logger.info(f'Searching for {bold(search_term)} [{len(search_results)} results]')
        output = []
        for i, r in enumerate(search_results):
            clearConsole()
            print(header)
            print(italic(grey(f'Loading {i}/{len(search_results)} expressions from jisho.org...')))
            output.append(JishoSearchResultElement(self.driver, r, search_term))
        return output
    
    def neocitiesSearchTerm(self, search_term: str, expression: str, header: str) -> list[NeocitiesSearchResultElement]:
        clearConsole()
        print(italic(grey(f'Loading sentencesearch.neocities.org...')))
        self.driver.get(self._neocitiessearch(search_term))
        while not self.driver.find_element(By.ID, "results-info").is_displayed():
            self.driver.find_element(By.ID, "searchButton").click()
        total_results = int(self.driver.find_element(By.ID, "num-results").text)
        while not self.driver.find_element(By.ID, "results-list-end").is_displayed():
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            search_results = self.driver.find_element(By.ID, "search-results-list").find_elements(By.XPATH, "./div")
            clearConsole()
            print(header)
            print(italic(grey(f'Loading {len(search_results)}/{total_results} sentences from sentencesearch.neocities.org...')))
            sleep(0.05)
        clearConsole()
        print(header)
        search_results = self.driver.find_element(By.ID, "search-results-list").find_elements(By.XPATH, "./div")
        if not search_results:
            self.logger.warning(f'Searching for {bold(f"{expression} returned no results")}, skipping...')
            return 
        print(italic(grey(f'Loaded {len(search_results)} sentences from sentencesearch.neocities.org...')))
        self.logger.info(f'Searching for {bold(expression)} [{len(search_results)} results]')
        
        def scrap(i_rez_pair):
            (i, rez) = i_rez_pair
            # clearConsole()
            # print(header)
            # print(italic(grey(f'Loaded {len(search_results)} sentences from sentencesearch.neocities.org...')))
            # print(italic(grey(f'Scrapping {i} sentences from loaded sentences...')))
            elem = NeocitiesSearchResultElement(rez, search_term)
            if elem.japanese and elem.english:
                return elem
            return None
        with ThreadPoolExecutor() as executor:
            output = executor.map(scrap, enumerate(search_results))
            executor.shutdown(wait=True)
        
        return [e for e in output if e]
        


    def promptForSelection(self, choices: list[str], input_text: str, header: str, callback: Callable[[int], None]):
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
            if match(r'^((,| )*\b\d+\b(,| )*)+$', response):
                output = [int(r) for r in findall(r'\b\d+\b', response)]
                break
        [callback(i) if i < len(choices) else "" for i in output]
        return
            
    def __enter__(self):
        options = Options()
        options.add_argument("--headless=new")
        self.logger.info("Launching Selenium...")
        self.driver = Firefox(options=options)
        self.logger.info("Selenium Headless Firefox driver launched !")

    def __exit__(self, exc_type, exc, tb):
        self.driver.close()
        self.logger.info("Selenium Headless Firefox driver closed !")

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
from selenium.webdriver import Firefox
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from printingUtils import bold, italic, grey, clearConsole
from typing import Callable

import logging
from JishoSearchResult import JishoSearchResultElement
from re import match, findall

import os
from enum import Enum

class VocabScrapper():
    logger = logging.getLogger(__name__)
    class SelectMode(Enum):
        NONE = -1
        FIRST = 0
        ALL = 1
        SELECT = 2

    def __init__(self):
        pass 

    def decideManually(self, vocab_list: list[str], autoselect_expression_mode = SelectMode.NONE, autoselect_meaning_mode = SelectMode.NONE):
        is_exact_match_autoselect = False
        clearConsole()
        # Auto-select expression mode
        while autoselect_expression_mode == self.SelectMode.NONE:
            print(grey("Auto-select \033[1mexpression\033[0m\033[2m mode"))
            print(f"\t{bold('1')}. First only")
            print(f"\t{bold('2')}. All")
            print(f"\t{bold('3')}. Select")
            response = match(r'[1-3]', input(f'{grey("Select mode")} ({bold("1")}|{bold("2")}|{bold("3")}) {grey(": ")}'))
            if response:
                autoselect_expression_mode = self.SelectMode(int(response.group(0))-1)
                self.logger.info(f"Auto-selecting expression mode is {autoselect_expression_mode.name}")
            # Auto-select exact match
            if autoselect_expression_mode == self.SelectMode.SELECT:
                is_exact_match_autoselect = match(r'(?i:^y(es)?$)', input(f"{grey('Enable auto-selecting only exact matches ?')} ({bold('y')}|{bold('n')}) {grey(':')} ")) != None
                self.logger.info(f"Auto-selecting exact matches is {'en' if is_exact_match_autoselect else 'dis'}abled")
        # Auto-select meanings mode
        while autoselect_meaning_mode == self.SelectMode.NONE:
            print(grey("Auto-select \033[1mmeaning\033[0m\033[2m mode (same choices as expression mode)"))
            response = match(r'[1-3]', input(f'{grey("Select mode")} ({bold("1")}|{bold("2")}|{bold("3")}) {grey(": ")}'))
            if response:
                autoselect_meaning_mode = self.SelectMode(int(response.group(0))-1)
                self.logger.info(f"Auto-selecting definition mode is {autoselect_meaning_mode.name}")

        # Navigate through vocab list
        selected_expr = self.selectExpressions(vocab_list, autoselect_expression_mode, is_exact_match_autoselect)
        selected_expr = self.selectMeanings(selected_expr, autoselect_meaning_mode)
        for expr in selected_expr:
            print(f'{bold(expr.expression)}')
            for definition in expr.meanings:
                print(definition["meaning"])

    def selectExpressions(self, vocab_list: list[str], mode: SelectMode = SelectMode.SELECT, is_exact_match_autoselect: bool = False) -> list[JishoSearchResultElement]:
        output = []
        expression_question = True
        # Go through vocab list
        for word_ind, word in enumerate(vocab_list):
            word = word.replace('\r\n', "")
            clearConsole()
            print(f'[{bold(word)}] {grey(f"({word_ind + 1}/{len(vocab_list)} search terms)")}\n')
            jisho_results = self.jishoSearchTerm(word)
            
            # No results
            if not jisho_results:
                continue
            # Exact match and auto-select
            if mode == self.SelectMode.FIRST or (is_exact_match_autoselect and jisho_results[0].is_exact_match):
                if jisho_results[0].is_exact_match:
                    self.logger.warning(f"Found exact match for {word} !")
                output.append(jisho_results[0])
                continue
            elif mode == self.SelectMode.ALL:
                [output.append(rez) for rez in jisho_results]
                continue
            
            # Too many results
            if len(jisho_results) > 10:
                response = match(r'^\d+$', input(f'{len(jisho_results)} results, how many to display ? '))
                num_of_choices = 10 if response == None else int(response.group(0))
                jisho_results = jisho_results[:min(num_of_choices, len(jisho_results))]


            print(grey(f"Please select expressions to keep"))
            self.promptForSelection(choices=[f"{bold(expr.expression)} ({expr.romaji}):\t\"{italic(expr.meanings[0]['meaning'])}\" {grey(f'(1/{len(expr.meanings)} meanings)')}" for expr in jisho_results], 
                                    input_text="\n" + grey("Expressions indices to keep ") + (f"({grey('ex:')} {bold('0, 2, 7')} {grey('or')} {bold('a')}) " if expression_question else "") + ": ",
                                    callback=lambda i: output.append(jisho_results[i]))
            expression_question = False
        return output
        
    def selectMeanings(self, selected_expr: list[JishoSearchResultElement], mode: SelectMode = SelectMode.SELECT) -> list[JishoSearchResultElement]:
        output = selected_expr.copy()
        for i, expression in enumerate(output):
            if mode == self.SelectMode.SELECT:
                selected_def = []
                clearConsole()
                print(f'[{expression.search_term} - {bold(expression.expression)}] {grey(f"({i + 1}/{len(output)} expressions to check)")}\n')
                print(grey(f"Please select meanings to keep"))
                self.promptForSelection(choices=[f"{italic(m['meaning'])}" for m in expression.meanings], 
                                        input_text=grey("\n: "),
                                        callback=lambda i: selected_def.append(expression.meanings[i]))
                expression.meanings = selected_def

            elif mode == self.SelectMode.FIRST:
                expression.meanings = [expression.meanings[0]]
        return output
                      
    def jishoSearchTerm(self, search_term: str):
        self.driver.get(self._jishosearch(search_term))
        search_results = self.driver.find_element(By.ID, "primary").find_elements(By.XPATH, "./div")
        if not search_results:
            self.logger.warning(f'Searching for {bold(f"{search_term} returned no results")}, skipping...')
            return
        
        self.logger.info(f'Searching for {bold(search_term)} [{len(search_results)} results]')
        return [JishoSearchResultElement(r, search_term) for r in search_results]
    
    @staticmethod
    def promptForSelection(choices: list[str], input_text: str, callback: Callable[[int], None]):
        for i, choice in enumerate(choices):
            print(f"\t{bold(str(i))}.\t{choice}")
        response = [int(r) if r != 'a' and r else 'a' for r in findall(r'(\d+(?=,?)|a)', input(input_text).replace(" ", ""))]
        response = list(range(len(choices))) if 'a' in response or not response else response
        [callback(i) if i < len(choices) else "" for i in response]
            
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




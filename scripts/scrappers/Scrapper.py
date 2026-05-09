from scripts.utils.printingUtils import bold, italic, grey, clearConsole
import re
from playwright.async_api import Page
import functools
from typing import Callable
import math
import logging

def oopsable():
    def wrapper(f):
        @functools.wraps(f)
        async def wrap(*args, **kwargs):
            while True:
                try:
                    return await f(*args, **kwargs)
                except Scrapper.Oops:
                    continue
        return wrap
    return wrapper

class Scrapper():
    logger = logging.getLogger(__name__)
    def __init__(self, page: Page, max_rez_display: int):
        self.page = page
        self.max_rez_display = max_rez_display

    
    class Quit(Exception):
        def __init__(self, *args):
            super().__init__(*args)

    class Oops(Exception):
        def __init__(self, *args):
            super().__init__(*args)

    
    @staticmethod
    def _checkAbortResponse(request: str) -> str:
        response = input(request)
        if response == "oops":
            raise Scrapper.Oops
        elif response == "quit":
            raise Scrapper.Quit
        return response
    
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
            response = self._checkAbortResponse(input_text).replace(" ", "")
            if not response:
                start_index = 0 if end_index >= num_of_choices else (self.max_rez_display + start_index) % num_of_choices
                continue
            if re.findall(r'\b[a-zA-Z]+\b', response):
                if re.match(r'\bp\b', response):
                    start_index = start_index - self.max_rez_display
                    if start_index < 0:
                        start_index = int(math.floor(num_of_choices/(self.max_rez_display))*self.max_rez_display)
                    continue
                if re.match(r'\ba\b', response):
                    output = list(range(len(choices)))
                    break
                if re.match(r'(?i:\bnone\b)', response) and use_none:
                    output = []
                    break
            if re.match(r'^((,| )*\b\d+\b(,| )*)+$', response):
                output = [int(r) for r in re.findall(r'\b\d+\b', response)]
                break
        [callback(i) if i < len(choices) else "" for i in output]
        return

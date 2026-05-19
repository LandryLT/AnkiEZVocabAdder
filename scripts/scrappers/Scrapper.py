from scripts.utils.printingUtils import bold, italic, grey, clearConsole
import re
from playwright.async_api import Page
import functools
from typing import Callable
import math
import logging
from typing import Any
from scripts.caching.cacheSearch import SearchCache

def oopsable(cache: SearchCache | None = None, is_async = True):
    def wrapper(f):
        if is_async:
            @functools.wraps(f)
            async def wrap(*args, **kwargs):
                while True:
                    try:
                        return await f(*args, **kwargs)
                    except Scrapper.Oops:
                        if cache:
                            cache.cache = {}
                        continue
        else:
            def wrap(*args, **kwargs):
                while True:
                    try:
                        return f(*args, **kwargs)
                    except Scrapper.Oops:
                        if cache:
                            cache.cache = {}
                        continue
        return wrap
    return wrapper

def cacheable(cache: SearchCache):
    def wrapper(f):
        @functools.wraps(f)
        async def wrap(*args, **kwargs):
            try:
                output = await f(*args, **kwargs)
            except Scrapper.Oops as e:
                raise e
            except Exception as e:
                cache.save_pickled_cache()
                raise e
            cache.save_pickled_cache()
            return output
        return wrap
    return wrapper

class Scrapper():
    logger = logging.getLogger(__name__)
    def __init__(self, page: Page, max_rez_display: int):
        self.page = page
        self.max_rez_display = max_rez_display

    def fromcache(self, cache: SearchCache, search_terms: list[str], callback: Callable[[Any], None] | None = None,  prepare_output_func: Callable[[Any, list[str]], None] | None = None, output_buffer: list = []) -> tuple[list[str], list[Any], Callable[[str, Any], None]]:
        cache_data = cache.cache
        cached_search = [cached_data for key, cached_data in cache_data.items() if key in search_terms]        
        cached_objects = output_buffer
        for csgroup in cached_search:
            for cs in csgroup:
                if prepare_output_func:
                    prepare_output_func(cs, search_terms)
                    # output.append(cs)
        # [[output.append(cs) for cs in csgroup] for csgroup in cached_search]
        uncached_search_terms = [st for st in search_terms if not st in cache_data.keys()]
        # callback = cached_objects.append if callback is None else callback 
        def on_append_result(search_term: str, rez: Any):
            if callback:
                callback(rez)
            cache.addToCache(search_term, rez)
        return (uncached_search_terms, cached_objects, on_append_result)

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
    
    @staticmethod
    def defErrorCallback(i):
        pass

    def promptForSelection(self, choices: list[str], input_text: str, header: str, callback: Callable[[int], None], use_none: bool = True, errorCallback: Callable[[int], None] = defErrorCallback, reverse_callback_order=False, max_results=-1):
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
            response = self._checkAbortResponse(input_text)
            if not response:
                start_index = 0 if end_index >= num_of_choices else (self.max_rez_display + start_index) % num_of_choices
                continue
            if re.findall(r'\b[a-zA-Z]+\b', response):
                if re.match(r'(?i:\bp(rev(ious)?)?\b)', response):
                    start_index = start_index - self.max_rez_display
                    if start_index < 0:
                        start_index = int(math.floor(num_of_choices/(self.max_rez_display))*self.max_rez_display)
                    continue
                if re.match(r'(?i:\ba(ll)?\b)', response):
                    output = list(range(len(choices)))
                    break
                if re.match(r'(?i:\bn(one)?\b)', response) and use_none:
                    output = []
                    break
            if re.match(r'^([ ]*\b\d+\b(,| |-)*)+$', response):
                output = []
                for a, b in re.findall(r'(\d+)[ ]*-[ ]*(\d+)', response):
                    output.extend(list(range(min(int(a), int(b)), max(int(a), int(b)) + 1)))
                response = re.sub(r'\d+[ ]*-[ ]*\d+', '',response)
                output.extend([int(r) for r in re.findall(r'\b\d+\b', response)])
                break
        if max_results > 0:
            output = output[:max_results]
        [callback(i) if i < len(choices) else errorCallback(i) for i in sorted(output, reverse=reverse_callback_order)]
        return
    

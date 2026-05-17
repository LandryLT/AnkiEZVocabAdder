from scripts.utils.printingUtils import bold, italic, grey, clearConsole, tqdm_bar_format
from enum import Enum
from scripts.scrappers.JishoSearchResult import JishoResult, JishoSearchResultRaw, word_audio_folder
from scripts.scrappers.Scrapper import Scrapper, oopsable, cacheable
from scripts.scrappers.JishoSelectMode import JishoSelectMode
import re
from typing import Callable
from tqdm.asyncio import tqdm
from scripts.caching.cacheSearch import SearchCache
from typing import Any
import os

expression_cache = SearchCache("./caches/jisho/exprcache")
meaning_cache = SearchCache("./caches/jisho/meancache")
sound_cache = SearchCache("./caches/jisho/sndcache")

class JishoScrapper(Scrapper):    
    def __init__(self, page, max_rez_display):
        super().__init__(page, max_rez_display)
        self.no_results = []

    @cacheable(expression_cache)
    @oopsable(expression_cache)
    async def selectExpressions(self, vocab_list: list[str], mode: JishoSelectMode.SelectMode | int = None, is_exact_match_autoselect: bool = False, jlpt_filter: int = 0) -> list[JishoResult]:        
        expression_question = True
        output = []
        # def prepare_cached_output_func(rez: JishoResult, cached_search_terms: str):
        #     if rez.search_term in cached_search_terms:
        #         output.append(rez)
        prepare_output: Callable[[JishoResult, list[str]], None] = lambda rez, stl: output.append(rez) if rez.search_term in stl else True
        callback = lambda rez: output.append(rez)
        (uncached_vocab_list, output, cache_on_append_result) = self.fromcache(expression_cache, vocab_list, callback, prepare_output, output)
        # Go through vocab list
        for word_ind, word in enumerate(uncached_vocab_list):
            word = word.replace('\r\n', "")
            header = f'[{bold(word)}] {grey(f"({word_ind + 1}/{len(uncached_vocab_list)} search terms)")}\n'
            jisho_results = await self.jishoSearchTerm(word, header)
            jisho_results = list(filter(lambda r: r.JLPT >= jlpt_filter, jisho_results))
            clearConsole()
            print(f'[{bold(word)}] {grey(f"({word_ind + 1}/{len(uncached_vocab_list)} search terms)")}\n')
            
            # No results
            if not jisho_results:
                self.no_results.append(word)
                continue
            # Exact match and auto-select
            if not isinstance(mode, JishoSelectMode.SelectMode):
                assert isinstance(mode, int)
                for i in range(min(len(jisho_results), mode)):
                    cache_on_append_result(jisho_results[i].search_term, jisho_results[i])
                continue

            if (mode == JishoSelectMode.SelectMode.SELECT and is_exact_match_autoselect and jisho_results[0].is_exact_match) or len(jisho_results) == 1:
                if jisho_results[0].is_exact_match:
                    self.logger.warning(f"Found exact match for {word} !")
                cache_on_append_result(jisho_results[0].search_term, jisho_results[0])
                continue
            elif mode == JishoSelectMode.SelectMode.ALL:
                [cache_on_append_result(rez.search_term, rez) for rez in jisho_results]
                continue

            self.promptForSelection(choices=[f"{bold(expr.expression)} ({expr.romaji}):\t\"{italic(expr.meanings[0].meaning)}\" {grey(f'(1/{len(expr.meanings)} meanings)')}" for expr in jisho_results], 
                                    input_text=(grey("Expressions indices to keep ") + f"({grey('ex:')} {bold('0, 2, 7')} {grey('or')} {bold('a')+grey(italic('(ll)'))} {grey('or')} {bold('n')+grey(italic('(one)'))}) " if expression_question else "") + ": ",
                                    header=header+grey(f"\nPlease select expressions to keep"),
                                    callback=lambda i: cache_on_append_result(jisho_results[i].search_term, jisho_results[i]))
            
            expression_question = False
        return output
    
    @cacheable(sound_cache)
    @oopsable(sound_cache)
    async def downloadSounds(self, selected_expr: list[JishoResult], enable:bool = True, auto_download: bool = None) -> list[JishoResult]:
        if not enable:
            return selected_expr
        output = []
        expr_uuids = [e.uuid for e in selected_expr]
        prepare_output = lambda rez, stl: output.append(rez) if rez.uuid in stl else True
        (uncached_results, output, cache_on_append_result) = self.fromcache(sound_cache, expr_uuids, prepare_output_func=prepare_output, output_buffer=output)
        selected_expr = output + [rz for rz in selected_expr.copy() if rz.uuid in uncached_results]
        expr_with_links_to_download = [expr for expr in selected_expr if expr.soundlink and (not expr.soundfile or not os.path.isfile(expr.soundfile))]

        clearConsole()
        if not expr_with_links_to_download:
            self.logger.info("No soundlinks found in selected expressions, skipping...")
            return selected_expr
        
        if auto_download:
            print(grey(italic(f'Downloading {len(expr_with_links_to_download)} audio files...\n')))
            download_cors = [e.downloadSound(cache_on_append_result) for e in expr_with_links_to_download]
            await tqdm.gather(*download_cors, bar_format=tqdm_bar_format)
            return selected_expr
        
        for i, expression in enumerate(expr_with_links_to_download):
            clearConsole()
            print(f'[{expression.search_term} - {bold(expression.expression)}] {grey(f"({i + 1}/{len(expr_with_links_to_download)} sounds to download)")}\n')
            if re.match(r'(?i:^y(es)?$)', self._checkAbortResponse(grey('Skip this file ? ') + f"({bold('y')}|{bold('n')}) {grey(':')} ")) != None:
                continue
            clearConsole()
            print(f'[{expression.search_term} - {bold(expression.expression)}] {grey(f"({i + 1}/{len(expr_with_links_to_download)} sounds to download)")}\n')
            print(italic(grey(f'Downloading audio from jisho.org')))
            await expression.downloadSound(cache_on_append_result)
        return selected_expr
        
    @cacheable(meaning_cache)
    @oopsable(meaning_cache)
    async def selectMeanings(self, selected_expr: list[JishoResult], mode: JishoSelectMode.SelectMode = JishoSelectMode.SelectMode.NONE) -> list[JishoResult]:     
        results_uuids = [se.uuid for se in selected_expr]
        output = []
        prepare_output: Callable[[Any, list[str]], None] = lambda rez, stl: output.append(rez) if rez.uuid in stl else True
        (uncached_uuids, cached_rez, cache_result) = self.fromcache(meaning_cache, results_uuids, prepare_output_func=prepare_output, output_buffer=output)
        # Update soundfile links
        for ca_rez in cached_rez:
            assert isinstance(ca_rez, JishoResult)
            ca_rez.soundfile = list(filter(lambda x: x.uuid == ca_rez.uuid, selected_expr))[0].soundfile
        output = cached_rez + [expr for expr in selected_expr.copy() if expr.uuid in uncached_uuids]
        
        expression_question = True
        for i, expression in enumerate(output):
            assert isinstance(expression, JishoResult)
            if not expression.uuid in uncached_uuids:
                continue
            clearConsole()
            print(f'[{expression.search_term} - {bold(expression.expression)} ({expression.furigana})] {grey(f"({i + 1}/{len(output)} search terms)")}\n')
            selected_def = []
            if not isinstance(mode, JishoSelectMode.SelectMode):
                assert isinstance(mode, int)
                selected_def = expression.meanings[:min(len(expression.meanings), mode)]
            elif mode == JishoSelectMode.SelectMode.SELECT and len(expression.meanings) > 1:
                self.promptForSelection(choices=[f"{italic(m.meaning)}" for m in expression.meanings], 
                                        input_text=(grey("Meanings indices to keep ") + f"({grey('ex:')} {bold('0, 2, 7')} {grey('or')} {bold('a')+grey(italic('(ll)'))} {grey('or')} {bold('n')+grey(italic('(one)'))}) " if expression_question else "") + ": ",
                                        header=f'[{expression.search_term} - {bold(expression.expression)} ({expression.furigana})] {grey(f"({i + 1}/{len(output)} expressions to check)")}\n'+
                                                    grey(f"\nPlease select meanings to keep"),
                                        callback=lambda i: selected_def.append(expression.meanings[i]))
                expression_question = False
            
            expression.meanings = list(filter(lambda x: not x is None, selected_def))
            cache_result(expression.uuid, expression)
            self.logger.debug(f"{[{expression.search_term} - {bold(expression.expression)}]}'s meanings: {expression.meanings}")
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
                                                    meanings: (() => {
                                                        const m = el.querySelector('.concept_light-meanings > .meanings-wrapper')
                                                        const tags = [...m.querySelectorAll('.meaning-tags')].map(x => x.innerText)
                                                        const meanings = [...m.querySelectorAll('.meaning-meaning')].map(x => x.innerText)
                                                        const supplemental_infos = [...m.querySelectorAll('.meaning-wrapper')].map(x => [...x.querySelectorAll('.supplemental_info > span.tag-tag')].map(y => y.innerText))
                                                        const output = meanings.map((x, i) => ({
                                                            tag: tags[i],
                                                            meaning: meanings[i],
                                                            supplemental_info: supplemental_infos[i],
                                                        }))
                                                        return output.filter(x => (x["tag"] != "Notes" && x["tag"] != "Other forms"))
                                                    })(),
                                                    tags: [...el.querySelectorAll('.concept_light-tag')].map(x => x.innerText),
                                                    soundlink: el.querySelector('source[type="audio/mpeg"]')?.src ?? null,
                                                    inflectionlink: getDomPath(el.querySelector('.show_inflection_table')) ?? null
                                                }))
                                            }""")
        output = [JishoResult(JishoSearchResultRaw(**rez), search_term) for rez in dict_rez]
        [await rez.queryInflection(self.page) for rez in output]
        return output
    
    @staticmethod
    def _jishosearch(term: str) -> str:
        return f'https://jisho.org/search/{term}'
    
    def clearCache(self):
        for f in os.listdir(word_audio_folder):
            os.remove(word_audio_folder+f)
        expression_cache.clearCache()
        meaning_cache.clearCache()
        sound_cache.clearCache()


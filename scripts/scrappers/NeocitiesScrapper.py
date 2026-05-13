from scripts.scrappers.Scrapper import Scrapper, oopsable, cacheable
from scripts.scrappers.JishoSearchResult import JishoResult
from scripts.scrappers.NeocitiesSelectMode import NeocitiesSelectMode
from scripts.utils.printingUtils import bold, italic, grey, clearConsole, tqdm_bar_format
import re
from tqdm.asyncio import tqdm
from typing import NamedTuple
import random
import math
import uuid
import os
import asyncio
import requests
from scripts.caching.cacheSearch import SearchCache

NeocitiesResult = NamedTuple('NeocitiesResult', [("japanese", str), ("english", str), ("audio_link", str), ("soundfile", str), ("expression", str), ("search_term", str), ("jisho_uuid", str), ("uuid", str)])
sentence_audio_folder = "./caches/audio/sentences/"

page_cache = SearchCache("./caches/neocities/pagecache")
sentence_cache = SearchCache("./caches/neocities/sencache")
sound_cache = SearchCache("./caches/neocities/sndcache")

class NeocitiesScrapper(Scrapper):  
    def __init__(self, page, max_rez_display):
        super().__init__(page, max_rez_display)
        
    def clearCache(self):
        for f in os.listdir(sentence_audio_folder):
            os.remove(sentence_audio_folder+f)
        sentence_cache.clearCache()
        sound_cache.clearCache()
        page_cache.clearCache()

    @cacheable(sentence_cache)
    @oopsable(sentence_cache)
    async def selectSentence(self, selected_expr: list[JishoResult], mode: NeocitiesSelectMode = None) -> list[list[NeocitiesResult]]:
        if mode.quantity == 0:
            return [*[[]]*len(selected_expr)]
        clearConsole()
        output = []
        all_uuids = [rez.uuid for rez in selected_expr]
        def select_cached_ouput(rez: list[NeocitiesResult], jisho_uuids: list[str]):
            if rez and rez[0].jisho_uuid in jisho_uuids:
                output.append(rez)
        (uncached_uuids, output, cache_result_func) = self.fromcache(sentence_cache, all_uuids, lambda rez: output.append(rez), select_cached_ouput, output)
        
        all_expr = [expr for expr in selected_expr.copy() if expr.uuid in uncached_uuids]
        expression_question = True
        # remember to cache selection
        for i, expression in enumerate(all_expr):
            selected_sentences = []
            search_term = expression.neoCitiesSearchTerm()
            neocities_rez = await self.neo_cities_search_term(search_term, expression.expression, f'[{expression.search_term} - {bold(expression.expression)}] {grey(f"({i + 1}/{len(all_expr)} sentences to set)")}\n', expression.uuid)
            if not neocities_rez:
                cache_result_func(expression.uuid, selected_sentences)
                continue
            if mode.max_length != -1 and (mode.min_length != -1 or mode.min_length <= mode.max_length):
                neocities_rez = [nr for nr in neocities_rez if len(nr.japanese) <= mode.max_length]
            if mode.min_length != -1 and (mode.max_length != -1 or mode.min_length <= mode.max_length):
                neocities_rez = [nr for nr in neocities_rez if len(nr.japanese) >= mode.min_length]
            clearConsole()
            if mode.mode == NeocitiesSelectMode.SelectMode.MANUAL:
                choices = [f'{s.japanese}\n\t\t{s.english}\n' for s in neocities_rez]
                input_text = (grey("Sentences indices to keep ") + f"({grey('ex:')} {bold('0, 2, 7')} {grey('or')} {bold('a')} {grey('or')} {bold('none')}) " if expression_question else "") + ": "
                self.boldSearchTerm(choices, search_term)                    
                self.promptForSelection(choices=choices,
                                        input_text=input_text,
                                        header=f'[{expression.search_term} - {bold(expression.expression)} ({expression.furigana})] {grey(f"({i + 1}/{len(all_expr)} sentences to set)")}\n{grey(italic(expression.meanings[0].meaning))}\n',
                                        callback=lambda i: selected_sentences.append(neocities_rez[i]))
                expression_question = False
                cache_result_func(expression.uuid,selected_sentences)
            else:
                indices_to_remove = []
                selected_ind = []
                filtered_chunks = []
                while True:
                    filtered_indices = indices_to_remove + selected_ind
                    remaining = mode.quantity-len(selected_ind)
                    if len(neocities_rez)-len(filtered_indices) <= remaining:
                        selected_sentences = [neocities_rez[i] for i in selected_ind]
                        self.logger.info(f"{expression.expression} sentence result returned less results than asked for, returning all results")
                        cache_result_func(expression.uuid, selected_sentences)
                        break
                    if len(selected_ind) < mode.quantity:
                        if mode.length_distribution == NeocitiesSelectMode.LengthDistribution.RANDOM:
                            selected_ind += random.choices([i for i in range(len(neocities_rez)) if i not in filtered_indices], k=remaining)
                        else:
                            selected_ind += self.evenChoiceOfSentences(len(neocities_rez), mode.quantity, filtered_indices, filtered_chunks)
                        selected_ind.sort()
                        selected_sentences = [neocities_rez[i] for i in selected_ind]
                    if mode.auto_validate_random:
                        cache_result_func(expression.uuid, selected_sentences)
                        break
                    choices = [f'{s.japanese}\n\t\t{s.english}\n' for s in selected_sentences]
                    self.boldSearchTerm(choices, search_term)                    
                    def removeIndCallback(i):
                        indices_to_remove.append(selected_ind.pop(i))
                        filtered_chunks.append(i)
                    
                    invalid_input = []
                    def errorInput(i):
                        invalid_input.append(i)

                    filtered_chunks = []
                    input_text = (grey("Sentences indices to remove from selection ") if expression_question else "") + grey(f"[{len(neocities_rez)-len(indices_to_remove + selected_ind)} remaining sentences]\n") + (f"({grey('ex:')} {bold('0, 2, 7')} {grey('or')} {bold('a')+grey(italic('(ll)'))} {grey('or')} {bold('n')+grey(italic('(one)'))}) " if expression_question else "") + ": "
                    expression_question = False
                    self.promptForSelection(choices=choices,
                                            input_text=input_text,
                                            header=f'[{expression.search_term} - {bold(expression.expression)} ({expression.furigana})] {grey(f"({i + 1}/{len(all_expr)} sentences to set)")}\n{grey(italic(expression.meanings[0].meaning))}\n',
                                            callback=removeIndCallback,
                                            errorCallback=errorInput,
                                            reverse_callback_order=True)
                    if mode.quantity == len(selected_ind) and not invalid_input:
                        cache_result_func(expression.uuid, selected_sentences)
                        break
            sentence_cache.save_pickled_cache()
        return output

    @staticmethod
    def evenChoiceOfSentences(num_of_rez:int, qty: int, filtered_indices: list[int], filtered_chunks: list[int]) -> list[NeocitiesResult]:
        divider = num_of_rez / qty
        indices = [[math.floor(i*divider), math.ceil((i+1)*divider)] for i in range(qty)]
        sel_indices = []
        for c_ind, chunks in enumerate(indices):            
            if filtered_chunks and not c_ind in filtered_chunks:
                continue
            valid_ind = [i for i in list(range(*chunks)) if i not in sel_indices + filtered_indices]
            virtual_c_ind = c_ind
            while not valid_ind:
                virtual_c_ind -= 1
                if virtual_c_ind >= -c_ind and virtual_c_ind < 0:
                    continue
                valid_ind = [i for i in list(range(*indices[abs(virtual_c_ind)])) if i not in sel_indices + filtered_indices]
            rand_ind = random.choice(valid_ind)
            sel_indices.append(rand_ind)
        return sel_indices
        
    @staticmethod
    def boldSearchTerm(choices: list[NeocitiesResult], search_term: str):
        for ind, choice in enumerate(choices):
            for m in list(re.finditer(re.compile(search_term), choice))[::-1]:
                choice = choice[:m.start()] + bold(choice[m.start():m.end()]) + choice[m.end():]
            choices[ind] = choice

    @cacheable(sound_cache)
    async def downloadSounds(self, sentence_groups: list[list[NeocitiesResult]], enable: bool = True) -> list[list[NeocitiesResult]]:
        if not enable or not sentence_groups:
            return
        
        clearConsole()
        flat_sentences = []
        [flat_sentences.extend(grp) for grp in sentence_groups]
        print(italic(grey(f'Downloading audio for {len(flat_sentences)} sentences from sentencesearch.neocities.org...')))
        download_cors = [self._downloadSound(s) for s in flat_sentences]
        flat_sentences: list[NeocitiesResult] = await tqdm.gather(*download_cors, bar_format=tqdm_bar_format)
        output = {}
        for sen in flat_sentences:
            if not sen.jisho_uuid in output.keys():
                output[sen.jisho_uuid] = [sen]
            else:
                output[sen.jisho_uuid].append(sen)
        return list(output.values())

    @cacheable(page_cache)
    async def neo_cities_search_term(self, search_term: str, expression: str, header: str, jisho_uuid: str) -> list[NeocitiesResult]:
        if search_term in page_cache.cache.keys():
            return page_cache.cache[search_term][0]
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
        result = await self.load_all_neocities_results(expression, search_term, jisho_uuid)
        page_cache.addToCache(search_term, result)
        return result

    async def load_all_neocities_results(self, expression:str, search_term: str, jisho_uuid)  -> list[NeocitiesResult]:
        previous_count = 0
        total_rez = int(await self.page.evaluate("() => {return document.querySelector('#num-results').innerText}"))
        print(grey(f'Gathering {total_rez} sentences from {italic("sentencesearch.neocities.org...")}'))
        with tqdm(total=total_rez, bar_format=tqdm_bar_format+grey(' [{n_fmt}/{total_fmt}]')) as pbar:
            while True:
                current_count = await self.page.evaluate("() => {return document.querySelectorAll('#search-results-list .search-result').length}")
                pbar.update(current_count - previous_count)
                all_loaded = await self.page.evaluate("() => {return document.querySelector('#results-list-end').checkVisibility()}")
                if current_count == previous_count or all_loaded:
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

        return [NeocitiesResult(**rez, expression=expression, soundfile=None, search_term=search_term, jisho_uuid=jisho_uuid, uuid=str(uuid.uuid1())) for rez in output]
            
    @staticmethod
    def _neocitiessearch(term: str) -> str:
        return f'https://sentencesearch.neocities.org/#{term}'
    
    async def _downloadSound(self, sentence: NeocitiesResult) -> NeocitiesResult:
        if not sentence.audio_link:
            return
        if sentence.uuid in sound_cache.cache.keys() and os.path.isfile(sound_cache.cache[sentence.uuid][0].soundfile):
            sentence = sentence._replace(soundfile=sound_cache.cache[sentence.uuid][0].soundfile)
            return sentence
        download_file_name = f'{sentence.expression}_sentence_{str(uuid.uuid1())}.mp3'
        download_file_path = sentence_audio_folder + download_file_name
        
        r = await asyncio.get_event_loop().run_in_executor(None, requests.get, sentence.audio_link)
        with open(download_file_path, "wb") as file:
            for chunk in r.iter_content():
                file.write(chunk)
        sentence = sentence._replace(soundfile=os.path.abspath(download_file_path))
        sound_cache.addToCache(sentence.uuid, sentence)
        return sentence
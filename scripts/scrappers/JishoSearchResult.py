from playwright.async_api import Page, ElementHandle
import re
from scripts.utils.furiganaToRomaji import convertToRomaji
import requests
import uuid
import os
import asyncio
from typing import NamedTuple, Callable
import re

word_audio_folder = "./caches/audio/words/"
def parseFurigana(expression, kanjis, furiganas):
    output = ""
    for c in expression:
        if c in kanjis and furiganas:
            output += furiganas.pop(0)
        else:
            output += c
    return output



JishoSearchResultRaw = NamedTuple('JishoSearchResult', [('expression', str), ('furiganas', str), ('meanings', list[dict[str, str | None]]), ('tags', list[str]), ('soundlink', str), ('inflectionlink', ElementHandle)])
Meaning = NamedTuple('Meaning', [('tag', str), ('meaning', str), ('supplemental_info', list[str])])
class JishoResult():
    def __init__(self, raw: JishoSearchResultRaw, search_term: str):
        self.search_term = search_term
        self.uuid = str(uuid.uuid1())
        self.expression = raw.expression
        self.kanjis = re.findall(r'[一-龯]', self.expression)
        self.furigana = parseFurigana(raw.expression, self.kanjis, raw.furiganas)
        self.romaji = convertToRomaji(self.furigana)
        self.is_exact_match = self.search_term in (self.expression, self.furigana, self.romaji) 
        self.meanings = [Meaning(r['tag'], r['meaning'], r['supplemental_info']) for r in raw.meanings]
        self.tags = raw.tags
        self.JLPT = 0
        for tag in self.tags:
            jlpt_tag = re.match(r'^jlpt n([1-5])$', tag)
            if jlpt_tag:
                self.JLPT = int(jlpt_tag.group(1))
                break
        self.soundlink = raw.soundlink
        self.soundfile = None
        self.inflectionlink = raw.inflectionlink
        pass

    async def queryInflection(self, page: Page):
        if not self.inflectionlink:
            self.inflections = None
            return
        self.inflections = {}
        link = await page.query_selector(self.inflectionlink)
        await link.click()
        cell_path = "#inflection_modal > .modal_content > .inflection_table > tbody:nth-of-type(2) > tr > td"
        cells = await page.evaluate("() => {return [...document.querySelectorAll('"+cell_path+"')].map(x => x.innerText)}")
        if any([c == '' for c in cells]):
            await page.wait_for_function("() => [...document.querySelectorAll('"+cell_path+"')].every(x => x != '')", timeout=1500)
            cells = await page.evaluate("() => {return [...document.querySelectorAll('"+cell_path+"')].map(x => x.innerText)}")
        for i in range(int(len(cells)//3)):
            s_i = i * 3
            self.inflections[re.sub(r',', "", cells[s_i])] = cells[s_i + 1:s_i + 3]

        close = await page.query_selector("#inflection_modal > a:nth-child(2)")
        if not await close.is_visible():
            await page.wait_for_function("(el) => el.checkVisibility()", arg=close, timeout=1500)
        await close.click()
        await page.wait_for_function("(el) => !el.checkVisibility()", arg=close, timeout=1500)

        return self.inflections


    def getFlattenedListOfInflection(self) -> list[str]:
        if not self.inflections:
            return []
        items = list(self.inflections.values())
        return [infl for tense in items for infl in tense]
    
    def setUsuallyWrittenInKana(self):
        self.usually_kana = any(any(re.match(r"Usually written using kana alone", sup_inf) for sup_inf in  m.supplemental_info) for m in self.meanings)

    async def downloadSound(self, save_cache_callback: Callable | None) -> str:
        if not self.soundlink:
            return None
        download_file_name = f'{self.expression}_{self.uuid}.mp3'
        download_file_path = word_audio_folder + download_file_name
        r = await asyncio.get_event_loop().run_in_executor(None, lambda: requests.get(self.soundlink, timeout=15, stream=False))
        with open(download_file_path, "wb") as file:
            for chunk in r.iter_content():
                file.write(chunk)
        self.soundfile = os.path.abspath(download_file_path)
        # Funky caching stuff
        if save_cache_callback:
            save_cache_callback(self.uuid, self)
        return self.soundfile
    
    def neoCitiesSearchTerm(self) -> str:
        search_terms = [self.expression]+self.getFlattenedListOfInflection()+[self.furigana if self.usually_kana else None]
        return f'{"|".join([st for st in search_terms if st])}'
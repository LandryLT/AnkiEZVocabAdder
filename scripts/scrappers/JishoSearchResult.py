# from selenium.webdriver import Firefox
# from selenium.webdriver.remote.webelement import WebElement
# from selenium.webdriver.common.by import By
# from selenium.common.exceptions import NoSuchElementException
from playwright.async_api import Page, Locator
from re import findall, match
from scripts.utils.furiganaToRomaji import convertToRomaji
import requests
import uuid
import os
import asyncio

audio_folder = "./audio/words/"

class Sentence():
    def __init__(self, japanese, english):
        self.japanese = japanese
        self.english = english

class Meaning():
    def __init__(self, tag:str, meaning:str, sentences: list[Sentence]):
        self.tag = tag
        self.meaning = meaning
        self.sentences = sentences

class JishoSearchResultElement():
    def __init__(self, driver: Page, search_term: str, search_result: Locator):
        self.browser = driver
        self.search_result = search_result
        self.search_term = search_term
    
    async def async_init(self):
        self.expression = await self.search_result.locator(".text").inner_text()
        
        self.kanjis = findall(r'[一-龯]', self.expression)
        self.furigana = await self.parseFurigana(self.search_result)
        self.romaji = convertToRomaji(self.furigana)
        self.is_exact_match = self.search_term in (self.expression, self.furigana, self.romaji) 

        #　Expressions
        meanings_tags_cors = [tag.inner_text() for tag in await self.search_result.locator(".concept_light-meanings").locator(".meaning-tags").all()]
        meanings_tags = await asyncio.gather(*meanings_tags_cors)
        meanings_wrapper = await self.search_result.locator(".concept_light-meanings").locator(".meaning-wrapper").all()
        
        self.meanings: list[Meaning] = []
        for tag, meaning_wrapper in zip(meanings_tags, meanings_wrapper):
            if tag in ("Notes", "Other forms"):
                continue
            japanese_sentences = []
            english_sentences = []
            # try:
            meaning_sentences_locator = meaning_wrapper.locator(".sentences").locator(".sentence")
            if await meaning_sentences_locator.count() > 0:
                meaning_sentences = await meaning_sentences_locator.all()
                japanese_sentences_cors = [s.locator(".japanese").inner_text() for s in meaning_sentences]
                japanese_sentences = await asyncio.gather(*japanese_sentences_cors)
                english_sentences_cors = [s.locator(".english").inner_text() for s in meaning_sentences]
                english_sentences = await asyncio.gather(*english_sentences_cors)
            # except NoSuchElementException as e:
                # pass
            new_meaning = Meaning(tag=tag,
                                  meaning=await meaning_wrapper.locator(".meaning-meaning").inner_text(),
                                  sentences=[Sentence(jap, eng) for jap, eng in zip(japanese_sentences, english_sentences)])

            self.meanings.append(new_meaning)
            all_sentences = self.getAllSentences()
            self.sentence = None if not all_sentences else all_sentences[0]
        
        tags_cors = [t.inner_text() for t in await self.search_result.locator(".concept_light-tag").all()]
        self.tags = await asyncio.gather(*tags_cors)
        self.JLPT = 0
        for tag in self.tags:
            jlpt_tag = match(r'^jlpt n([1-5])$', tag)
            if jlpt_tag:
                self.JLPT = int(jlpt_tag.group(1))
                break
        
        # try:
        soundlink_locator = self.search_result.locator('source[type="audio/mpeg"]')
        if await soundlink_locator.count() == 0:
            self.soundlink = None
        else:
            self.soundlink = "https:" + await soundlink_locator.get_attribute("src")

        # except NoSuchElementException:
        #     self.soundlink = None
        self.soundfile = None

        self.inflections = {}
        # try:
        inflections_link = self.search_result.locator(".show_inflection_table")
        if await inflections_link.count() > 0:
            await inflections_link.click()
            inflection_table = self.browser.locator("#inflection_modal")
            close_button = inflection_table.locator(".close-reveal-modal")
            inflection_tbody = inflection_table.locator("tbody").last
            inflection_rows: list[Locator] = await inflection_tbody.locator("tr").all()
            inflection_cells_cors = [td.inner_text() for td in await inflection_tbody.locator("td").all()]
            inflection_cells = await asyncio.gather(*inflection_cells_cors)
            while any([td == '' for td in inflection_cells]):
                await asyncio.sleep(0.05)
                inflection_rows: list[Locator] = await inflection_tbody.locator("tr").all()
                inflection_cells_cors = [td.inner_text() for td in await inflection_tbody.locator("td").all()]
                inflection_cells = await asyncio.gather(*inflection_cells_cors)
            
            for tr in inflection_rows:
                cells_cors = [td.inner_text() for td in await tr.locator("td").all()]
                cells = await asyncio.gather(*cells_cors)
                self.inflections[cells[0]] = cells[1:]
            await close_button.click()
            while await inflection_table.is_visible():
                await asyncio.sleep(0.05)
        # except (NoSuchElementException, IndexError):
        #     pass

        return self


    def getAllSentences(self) -> list[Sentence]:
        return [m.sentences for m in self.meanings]

    def getFlattenedListOfInflection(self) -> list[str]:
        items = list(self.inflections.values())
        return [infl for tense in items for infl in tense]
    
    async def parseFurigana(self, search_result: Locator) -> str:        
        # try:
        furigana_locator = search_result.locator(".furigana").locator(".kanji")
        if await furigana_locator.count() == 0:
            return ""
        furiganas_cors = [f.inner_text() for f in await furigana_locator.all()]
        furiganas = await asyncio.gather(*furiganas_cors)
        # except NoSuchElementException:
        #     return self.expression
        output = ""
        for c in self.expression:
            if c in self.kanjis and furiganas:
                output += furiganas.pop(0)
            else:
                output += c
        return output
    
    async def downloadSound(self) -> str:
        if not self.soundlink:
            return
        download_file_name = f'{self.expression}_{str(uuid.uuid1())}.mp3'
        download_file_path = audio_folder + download_file_name
        r = await asyncio.get_event_loop().run_in_executor(None, requests.get, self.soundlink)
        with open(download_file_path, "wb") as file:
            for chunk in r.iter_content():
                file.write(chunk)
        self.soundfile = os.path.abspath(download_file_path)
        return self.soundfile
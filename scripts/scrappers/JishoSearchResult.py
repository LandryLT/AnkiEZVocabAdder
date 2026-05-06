from selenium.webdriver import Firefox
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from re import findall, match
from scripts.utils.furiganaToRomaji import convertToRomaji
import requests
import uuid
import os
from time import sleep

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
    def __init__(self, driver: Firefox, search_result: WebElement, search_term: str):
        self.search_term = search_term
        self.expression = search_result.find_element(By.CLASS_NAME, "text").text
        self.kanjis = findall(r'[一-龯]', self.expression)
        self.furigana = self.parseFurigana(search_result)
        self.romaji = convertToRomaji(self.furigana)
        self.is_exact_match = search_term in (self.expression, self.furigana, self.romaji) 

        #　Expressions
        meanings_tags = search_result.find_element(By.CLASS_NAME, "concept_light-meanings").find_elements(By.CLASS_NAME, "meaning-tags")
        meanings_wrapper = search_result.find_element(By.CLASS_NAME, "concept_light-meanings").find_elements(By.CLASS_NAME, "meaning-wrapper")
        
        self.meanings: list[Meaning] = []
        for tag, meaning_wrapper in zip(meanings_tags, meanings_wrapper):
            if tag.text in ("Notes", "Other forms"):
                continue
            japanese_sentences = []
            english_sentences = []
            try:
                meaning_sentences = meaning_wrapper.find_element(By.CLASS_NAME, "sentences").find_elements(By.CLASS_NAME, "sentence")
                japanese_sentences = [s.find_element(By.CLASS_NAME, "japanese").text for s in meaning_sentences]
                english_sentences = [s.find_element(By.CLASS_NAME, "english").text for s in meaning_sentences]
            except NoSuchElementException as e:
                pass
            new_meaning = Meaning(tag=tag.text,
                                  meaning=meaning_wrapper.find_element(By.CLASS_NAME, "meaning-meaning").text,
                                  sentences=[Sentence(jap, eng) for jap, eng in zip(japanese_sentences, english_sentences)])

            self.meanings.append(new_meaning)
            all_sentences = self.getAllSentences()
            self.sentence = None if not all_sentences else all_sentences[0]
        
        self.tags = [t.text for t in search_result.find_elements(By.CLASS_NAME, "concept_light-tag")]
        self.JLPT = 0
        for tag in self.tags:
            jlpt_tag = match(r'^jlpt n([1-5])$', tag)
            if jlpt_tag:
                self.JLPT = int(jlpt_tag.group(1))
                break
        
        try:
            self.soundlink = search_result.find_element(By.TAG_NAME, "audio").find_element(By.CSS_SELECTOR, '[type="audio/mpeg"]').get_attribute("src")
        except NoSuchElementException:
            self.soundlink = None
        self.soundfile = None

        self.inflections = {}
        try:
            inflections_link = search_result.find_element(By.CLASS_NAME, "show_inflection_table")
            inflections_link.click()
            inflection_table = driver.find_element(By.ID, "inflection_modal")
            close_button = inflection_table.find_element(By.CLASS_NAME, "close-reveal-modal")
            inflection_rows = inflection_table.find_elements(By.TAG_NAME, "tbody")[1].find_elements(By.TAG_NAME, "tr")
            inflection_cells = inflection_table.find_elements(By.TAG_NAME, "tbody")[1].find_elements(By.TAG_NAME, "td")
            while any([td.text == '' for td in inflection_cells]):
                sleep(0.05)
                inflection_rows = inflection_table.find_elements(By.TAG_NAME, "tbody")[1].find_elements(By.TAG_NAME, "tr")
            
            for tr in inflection_rows:
                cells = [td.text for td in tr.find_elements(By.TAG_NAME, "td")]
                self.inflections[cells[0]] = cells[1:]
            close_button.click()
            while inflection_table.is_displayed():
                sleep(0.05)
        except (NoSuchElementException, IndexError):
            pass


    def getAllSentences(self) -> list[Sentence]:
        return [m.sentences for m in self.meanings]

    def getFlattenedListOfInflection(self) -> list[str]:
        items = list(self.inflections.values())
        return [infl for tense in items for infl in tense]
    
    def parseFurigana(self, search_result: WebElement) -> str:        
        try:
            furiganas = [f.text for f in search_result.find_element(By.CLASS_NAME, "furigana").find_elements(By.CLASS_NAME, "kanji")]
        except NoSuchElementException:
            return self.expression
        output = ""
        for c in self.expression:
            if c in self.kanjis and furiganas:
                output += furiganas.pop(0)
            else:
                output += c
        return output
    
    def downloadSound(self) -> str:
        if not self.soundlink:
            return
        download_file_name = f'{self.expression}_{str(uuid.uuid1())}.mp3'
        download_file_path = audio_folder + download_file_name
        r = requests.get(self.soundlink, stream=True)
        with open(download_file_path, "wb") as file:
            for chunk in r.iter_content():
                file.write(chunk)
        self.soundfile = os.path.abspath(download_file_path)
        return self.soundfile
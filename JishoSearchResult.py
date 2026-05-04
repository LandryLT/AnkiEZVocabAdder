from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from re import findall
from furiganaToRomaji import convertToRomaji
class Sentence():
    def __init__(self, japanese, english):
        self.japanese = japanese
        self.english = english
        
class JishoSearchResultElement():
    class Sentence():
        def __init__(self, japanese:str, english: str):
            self.japanese = japanese
            self.english = english

    def __init__(self, search_result: WebElement, search_term: str):
        self.search_term = search_term
        self.expression = search_result.find_element(By.CLASS_NAME, "text").text
        self.kanjis = findall(r'[一-龯]', self.expression)
        self.furigana = self.parseFurigana(search_result)
        self.romaji = convertToRomaji(self.furigana)
        self.is_exact_match = search_term in (self.expression, self.furigana, self.romaji) 
        meanings_tags = search_result.find_element(By.CLASS_NAME, "concept_light-meanings").find_elements(By.CLASS_NAME, "meaning-tags")
        meanings_wrapper = search_result.find_element(By.CLASS_NAME, "concept_light-meanings").find_elements(By.CLASS_NAME, "meaning-wrapper")
        
        self.meanings = []
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
            
            new_meaning = {
                "tag": tag.text,
                "meaning": meaning_wrapper.find_element(By.CLASS_NAME, "meaning-meaning").text,
                "japanese_sentences": japanese_sentences,
                "english_sentences": english_sentences
            }

            self.meanings.append(new_meaning)
            all_sentences = self.getAllSentences()
            self.sentence = None if not all_sentences else all_sentences[0]
        
    def getAllSentences(self):
        output = []
        for m in self.meanings:
            [output.append(Sentence(jap, eng)) for jap, eng in zip(m["japanese_sentences"], m["english_sentences"])]
        return output


    def parseFurigana(self, search_result: WebElement) -> str:        
        try:
            furiganas = [f.text for f in search_result.find_element(By.CLASS_NAME, "furigana").find_elements(By.CLASS_NAME, "kanji")]
        except NoSuchElementException:
            return self.expression
        output = ""
        for c in self.expression:
            if c in self.kanjis:
                output += furiganas.pop(0)
            else:
                output += c
        return output
from selenium.webdriver import Firefox
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from enum import Enum
from re import match
from scripts.utils.printingUtils import grey, bold
import scripts.scrappers as scrappers

class SentenceSelectMode():
    class SelectMode(Enum):
        NONE = -1
        MANUAL = 0
        AUTO = 1 

    class LengthDistribution(Enum):
        NONE = -1
        EVEN = 0
        RANDOM = 1
    
    MAX_QUANTITY = 20
    def __init__(self):
        self.mode: SentenceSelectMode.SelectMode = self.SelectMode.NONE
        self.quantity: int = -1
        self.max_length: int = -1
        self.min_length: int = -1
        self.length_distribution: SentenceSelectMode.LengthDistribution = self.LengthDistribution.NONE

    def setAutoMode(self):
        while self.quantity == -1:
            response = scrappers.VocabScrapper._checkAbortResponse(grey('Max number of sentences per expression ? ') + f"({bold('0-'+str(SentenceSelectMode.MAX_QUANTITY))}) {grey(':')} ")
            if not response:
                self.quantity = SentenceSelectMode.MAX_QUANTITY
                break
            response = match(r'^\d+$', response)
            if not response:
                continue
            response = min(SentenceSelectMode.MAX_QUANTITY, int(response.group(0)))
            self.quantity = response
        
        while self.min_length == -1:
            response = scrappers.VocabScrapper._checkAbortResponse(grey('Minimum number of characters per sentence ? ') + f"({bold('0-n')}) {grey(':')} ")
            if not response:
                self.min_length = 0
                break
            response = match(r'^\d+$', response)
            if not response:
                continue
            response = int(response.group(0))
            self.min_length = response
        
        while self.max_length == -1:
            response = scrappers.VocabScrapper._checkAbortResponse(grey('Maximum number of characters per sentence ? ') + f"({bold(str(self.min_length)+'-n')}) {grey(':')} ")
            if not response:
                self.max_length = 9999999
                break
            response = match(r'^\d+$', response)
            if not response:
                continue
            self.max_length = int(response.group(0))

        print(grey('Select sentence length distribution mode'))
        print("\t1. Even")
        print("\t2. Random")
        while self.length_distribution == SentenceSelectMode.LengthDistribution.NONE:
            response = scrappers.VocabScrapper._checkAbortResponse(grey('Select mode ') + f"({bold('1')+'|'+bold('2')}) {grey(':')} ")
            if not response:
                self.length_distribution = SentenceSelectMode.LengthDistribution.EVEN
                break
            response = match(r'^[1-2]$', response)
            if not response:
                continue
            self.length_distribution = SentenceSelectMode.LengthDistribution(int(response.group(0))-1)


class NeocitiesSearchResultElement():
    def __init__(self, driver: Firefox, search_result: WebElement, expression: str):
        pass
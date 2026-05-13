from enum import Enum
import re
from scripts.utils.printingUtils import grey, bold, clearConsole
from scripts.scrappers.Scrapper import Scrapper, oopsable

class NeocitiesSelectMode():
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
        self.mode: NeocitiesSelectMode.SelectMode = self.SelectMode.NONE
        self.auto_validate_random = None
        self.download_audio = None
        self.quantity: int = -1
        self.max_length: int = -1
        self.min_length: int = -1
        self.length_distribution: NeocitiesSelectMode.LengthDistribution = self.LengthDistribution.NONE

    def setQuantity(self):
        while self.quantity == -1 and self.mode != NeocitiesSelectMode.SelectMode.MANUAL:
            response = Scrapper._checkAbortResponse(grey('Max number of sentences per expression ? ') + f"({bold('0-'+str(NeocitiesSelectMode.MAX_QUANTITY))}) {grey(':')} ")
            if not response:
                self.quantity = NeocitiesSelectMode.MAX_QUANTITY
                break
            response = re.match(r'^\d+$', response)
            if not response:
                continue
            response = min(NeocitiesSelectMode.MAX_QUANTITY, int(response.group(0)))
            self.quantity = response

    def setMinLength(self):
        while self.min_length == -1:
            response = Scrapper._checkAbortResponse(grey('Minimum number of characters per sentence ? ') + f"({bold('0-n')}) {grey(':')} ")
            if not response:
                self.min_length = 0
                break
            response = re.match(r'^\d+$', response)
            if not response:
                continue
            response = int(response.group(0))
            self.min_length = response

    def setMaxLength(self):
        while self.max_length == -1:
            response = Scrapper._checkAbortResponse(grey('Maximum number of characters per sentence ? ') + f"({bold(str(self.min_length)+'-n')}) {grey(':')} ")
            if not response:
                self.max_length = 9999999
                break
            response = re.match(r'^\d+$', response)
            if not response:
                continue
            self.max_length = int(response.group(0))
    
    
    def setDistributionMode(self):
        if self.length_distribution != NeocitiesSelectMode.LengthDistribution.NONE or self.mode == self.SelectMode.MANUAL:
            return
        print(grey('Select sentence length distribution mode'))
        print("\t1. Even")
        print("\t2. Random")
        while self.length_distribution == NeocitiesSelectMode.LengthDistribution.NONE and self.mode != self.SelectMode.MANUAL:
            response = Scrapper._checkAbortResponse(grey('Select mode ') + f"({bold('1')+'|'+bold('2')}) {grey(':')} ")
            if not response:
                self.length_distribution = NeocitiesSelectMode.LengthDistribution.EVEN
                break
            response = re.match(r'^\s?[1-2]\s?$', response)
            if not response:
                continue
            self.length_distribution = NeocitiesSelectMode.LengthDistribution(int(response.group(0))-1)

    def setMode(self):
        while self.mode == NeocitiesSelectMode.SelectMode.NONE:
            if re.match(r'(?i:^y(es)?$)', Scrapper._checkAbortResponse(grey('Enable \033[1mauto-select sentences\033[0m\033[2m ? ') + f"({bold('y')}|{bold('n')}) {grey(':')} ")) != None:
                self.mode = NeocitiesSelectMode.SelectMode.AUTO
            else:
                self.mode = NeocitiesSelectMode.SelectMode.MANUAL
        while self.auto_validate_random == None and self.mode == NeocitiesSelectMode.SelectMode.AUTO:
            self.auto_validate_random = not re.match(r'(?i:^y(es)?$)', Scrapper._checkAbortResponse(grey('Manually validate randomly selected sentences ? ') + f"({bold('y')}|{bold('n')}) {grey(':')} ")) != None

    def setDownloadAudio(self):
        while self.download_audio == None:
            self.download_audio = not re.match(r'(?i:^y(es)?$)', Scrapper._checkAbortResponse(grey('Disable downloading audio for sentences ? ') + f"({bold('y')}|{bold('n')}) {grey(':')} ")) != None

    @oopsable()
    async def setAutoMode(self):
        clearConsole()
        self.setMode()
        self.setQuantity()
        self.setMinLength()
        self.setMaxLength()
        self.setDistributionMode()
        self.setDownloadAudio()


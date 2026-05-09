from enum import Enum
from scripts.utils.printingUtils import bold, italic, grey, clearConsole
from .Scrapper import Scrapper
import re
import logging

class JishoSelectMode():
    logger = logging.getLogger(__name__)
    class SelectMode(Enum):
        NONE = -1
        FIRST = 0
        SELECT = 1
        ALL = 2

    def __init__(self):
        self.autoselect_expression_mode = self.SelectMode.NONE 
        self.is_exact_match_autoselect = None
        self.autoselect_meaning_mode = self.SelectMode.NONE
        self.enable_word_sound_download = True
        self.auto_download_sounds = None

    def setAudioAutoDownload(self):
        clearConsole()
        if self.auto_download_sounds == None:
            self.auto_download_sounds = re.match(r'(?i:^y(es)?$)', Scrapper._checkAbortResponse(grey('\033[1mAuto-download sound\033[0m\033[2m when found ?') + f"({bold('y')}|{bold('n')}) {grey(':')} ")) != None
            self.logger.info(f"Auto-downloading sound is {'en' if self.auto_download_sounds else 'dis'}abled")

    def setAutoselectMeaningMode(self):
        # Auto-select meanings mode
        while self.autoselect_meaning_mode == JishoSelectMode.SelectMode.NONE:
            clearConsole()
            print(grey("Auto-select \033[1mmeaning\033[0m\033[2m mode"))
            print(f"\t{bold('1')}. First only")
            print(f"\t{bold('2')}. Select")
            print(f"\t{bold('3')}. All")
            response = re.match(r'[1-3]', Scrapper._checkAbortResponse(f'{grey("Select mode")} ({bold("1")}|{bold("2")}|{bold("3")}) {grey(": ")}'))
            if response:
                self.autoselect_meaning_mode = JishoSelectMode.SelectMode(int(response.group(0))-1)
                self.logger.info(f"Auto-selecting definition mode is {self.autoselect_meaning_mode.name}")



    def setAutoselectExpressionMode(self):
        # Auto-select expression mode
        clearConsole()
        while self.autoselect_expression_mode == JishoSelectMode.SelectMode.NONE:
            clearConsole()
            print(grey("Auto-select \033[1mexpression\033[0m\033[2m mode"))
            print(f"\t{bold('1')}. First only")
            print(f"\t{bold('2')}. Select")
            print(f"\t{bold('3')}. All")
            response = re.match(r'([1-3]|oops)', Scrapper._checkAbortResponse(f'{grey("Select mode")} ({bold("1")}|{bold("2")}|{bold("3")}) {grey(": ")}'))
            if response:
                self.autoselect_expression_mode = JishoSelectMode.SelectMode(int(response.group(0))-1)
                self.logger.info(f"Auto-selecting expression mode is {self.autoselect_expression_mode.name}")
            # Auto-select exact match
            if self.autoselect_expression_mode == JishoSelectMode.SelectMode.SELECT:
                response = Scrapper._checkAbortResponse(f"\n{grey('Enable auto-selecting only exact matches ?')} ({bold('y')}|{bold('n')}) {grey(':')} ")
                self.is_exact_match_autoselect = re.match(r'(?i:^y(es)?$)', response) != None
                self.logger.info(f"Auto-selecting exact matches is {'en' if self.is_exact_match_autoselect else 'dis'}abled")

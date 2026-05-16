from enum import Enum
from scripts.utils.printingUtils import bold, italic, grey, clearConsole
from .Scrapper import Scrapper, oopsable
import re
import logging

class JishoSelectMode():
    logger = logging.getLogger(__name__)
    class SelectMode(Enum):
        NONE = -1
        SELECT = 1
        ALL = 2

    def __init__(self):
        self.autoselect_expression_mode = self.SelectMode.NONE 
        self.is_exact_match_autoselect = None
        self.autoselect_meaning_mode = self.SelectMode.NONE
        self.enable_word_sound_download = True
        self.auto_download_sounds = None
        self.jlpt_filter = -1

    @oopsable(is_async=False)
    def setAudioAutoDownload(self):
        clearConsole()
        if self.auto_download_sounds == None:
            self.auto_download_sounds = re.match(r'(?i:^y(es)?$)', Scrapper._checkAbortResponse(grey('\033[1mAuto-download sound\033[0m\033[2m when found ?') + f"({bold('y')}|{bold('n')}) {grey(':')} ")) != None
            self.logger.info(f"Auto-downloading sound is {'en' if self.auto_download_sounds else 'dis'}abled")

    @oopsable(is_async=False)
    def setAutoSelectJLPTFilter(self):
        print(grey("Please be aware that JLPT levels go from 5, the lowest level, to 1, the highest."))
        print(grey("You can select level 0 to include all the untaged search results in regards to its JLPT level."))
        while self.jlpt_filter == -1:
            response = re.match(r'^\s?[0-5]\s?$', Scrapper._checkAbortResponse(f'{grey("Filter results higher or equal to JLPT N")} ({bold("0")}-{bold("5")}) {grey(": ")}'))
            if response:
                self.jlpt_filter = int(response.group())


    @oopsable(is_async=False)
    def setAutoselectMeaningMode(self):
        # Auto-select meanings mode
        while self.autoselect_meaning_mode == JishoSelectMode.SelectMode.NONE:
            clearConsole()
            print(grey("Auto-select \033[1mmeaning\033[0m\033[2m mode"))
            print(f"\t{bold('1')}. First {italic('n')} meanings")
            print(f"\t{bold('2')}. Select")
            print(f"\t{bold('3')}. All")
            response = re.match(r'^\s?([1-3])\s?$', Scrapper._checkAbortResponse(f'{grey("Select mode")} ({bold("1")}|{bold("2")}|{bold("3")}) {grey(": ")}'))
            if response:
                if response.group() == '1':
                    response = re.match(r'^\s?(\d+)\s?$', Scrapper._checkAbortResponse(f'{grey("Maximum number of meanings to keep : ")} ({bold("1")}-...) {grey(": ")}'))
                    self.autoselect_meaning_mode = int(response.group())
                else:
                    self.autoselect_meaning_mode = JishoSelectMode.SelectMode(int(response.group(0))-1)
                    self.logger.info(f"Auto-selecting definition mode is {self.autoselect_meaning_mode.name}")



    @oopsable(is_async=False)
    def setAutoselectExpressionMode(self):
        # Auto-select expression mode
        clearConsole()
        while self.autoselect_expression_mode == JishoSelectMode.SelectMode.NONE:
            clearConsole()
            print(grey("Auto-select \033[1mresult\033[0m\033[2m mode"))
            print(f"\t{bold('1')}. First {italic('n')} results")
            print(f"\t{bold('2')}. Select")
            print(f"\t{bold('3')}. All")
            response = re.match(r'^\s?[1-3]\s?$', Scrapper._checkAbortResponse(f'{grey("Select mode")} ({bold("1")}|{bold("2")}|{bold("3")}) {grey(": ")}'))
            if response:
                if response.group() == '1':
                    response = re.match(r'^\s?(\d+)\s?$', Scrapper._checkAbortResponse(f'{grey("Maximum number of results to keep : ")} ({bold("1")}-...) {grey(": ")}'))
                    self.autoselect_expression_mode = int(response.group())
                else:
                    self.autoselect_expression_mode = JishoSelectMode.SelectMode(int(response.group(0))-1)
                    self.logger.info(f"Auto-selecting definition mode is {self.autoselect_expression_mode.name}")
                    # Auto-select exact match
                    if self.autoselect_expression_mode == JishoSelectMode.SelectMode.SELECT:
                        self.autoselect_expression_mode = JishoSelectMode.SelectMode.NONE
                        response = re.match(r'(?i:^y(es)?|n(o)?$)', Scrapper._checkAbortResponse(f"\n{grey('Enable auto-selecting only exact matches ?')} ({bold('y')}|{bold('n')}) {grey(':')} "))
                        if response:
                            self.is_exact_match_autoselect = re.match(r'(?i:^y(es)?$)', response) != None
                            self.logger.info(f"Auto-selecting exact matches is {'en' if self.is_exact_match_autoselect else 'dis'}abled")
                            self.autoselect_expression_mode = JishoSelectMode.SelectMode.SELECT


from re import match
from scripts.scrappers.VocabScrapperClass import VocabScrapper
from scripts.scrappers.NeocitiesSearchResult import SentenceSelectMode

class scrapperConfigParser():
    def __init__(self, filepath: str):
        self.parsedParams = {
            "autoselect_expression_mode": VocabScrapper.SelectMode.NONE,
            "is_exact_match_autoselect": None,
            "autoselect_meaning_mode": VocabScrapper.SelectMode.NONE,
            "autoselect_sentence_mode": SentenceSelectMode(),
            "enable_word_sound_download": True,
            "auto_download_sounds": None
        }
        self.max_results_displayed = 20


        with open(filepath, 'r') as f:
            lines = [l for l in f.readlines() if not match(r'^\#', l)]
            params = {}
            for l in lines:
                param_match = match(r'(^[^=]+)=(.*$)', l)
                if not param_match:
                    continue
                params[param_match.group(1)] = param_match.group(2)
            
            assert isinstance(self.parsedParams["autoselect_sentence_mode"], SentenceSelectMode)
            for key, item in params.items():
                match key:
                    case "max_results_displayed":
                        self.max_results_displayed = self.parseInt(item)
                    case "expression_autoselect":
                        self.parsedParams["autoselect_expression_mode"] = self.parseSelectMode(item)
                    case "exact_match_autoselect":
                        self.parsedParams["is_exact_match_autoselect"] = self.parseBool(item)
                    case "meaning_autoselect":
                        self.parsedParams["autoselect_meaning_mode"] = self.parseSelectMode(item)
                    case "word_audio_download":
                        self.parsedParams["enable_word_sound_download"] = not item == "NO"
                    case "word_audio_auto_download":
                        self.parsedParams["auto_download_sounds"] = self.parseBool(item)
                    case "sentence_select_mode":
                        self.parsedParams["autoselect_sentence_mode"].mode = self.parseSentenceSelectMode(item)
                    case "sentence_quantity":
                        self.parsedParams["autoselect_sentence_mode"].quantity = self.parseInt(item)
                    case "sentence_min_length":
                        self.parsedParams["autoselect_sentence_mode"].min_length = self.parseInt(item)
                    case "sentence_max_length":
                        self.parsedParams["autoselect_sentence_mode"].max_length = self.parseInt(item)
                    case "sentence_len_distribution":
                        self.parsedParams["autoselect_sentence_mode"].length_distribution = self.parseSentenceDistributionMode(item)
    
    @staticmethod
    def parseInt(value: str) -> (int | None):
        value = match(r'^\d+$', value)
        if not value:
            return -1
        return int(value.group(0))
    
    @staticmethod
    def parseBool(value: str) -> (bool | None):
        value = match(r'^(YES|NO)$', value)
        if not value:
            return None
        value = value.group(0)
        return value == "YES"
        
        
    @staticmethod
    def parseSentenceSelectMode(value: str) -> SentenceSelectMode.SelectMode:
        value = match(r'^(MANUAL|AUTO)$', value)
        if not value:
            return SentenceSelectMode.SelectMode.NONE
        value = value.group(0)
        return SentenceSelectMode.SelectMode(["MANUAL", "AUTO"].index(value))
    
    @staticmethod
    def parseSentenceDistributionMode(value: str) -> SentenceSelectMode.LengthDistribution:
        value = match(r'^(RANDOM|EVEN)$', value)
        if not value:
            return SentenceSelectMode.LengthDistribution.NONE
        value = value.group(0)
        return SentenceSelectMode.LengthDistribution(["EVEN", "RANDOM"].index(value))
    
    @staticmethod
    def parseSelectMode(value: str) -> VocabScrapper.SelectMode:
        value = match(r'^(FIRST|SELECT|ALL)$', value)
        if not value:
            return VocabScrapper.SelectMode.NONE
        value = value.group(0)
        return VocabScrapper.SelectMode(["FIRST", "SELECT", "ALL"].index(value))

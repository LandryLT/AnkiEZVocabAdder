from re import match
from scripts.scrappers.JishoSelectMode import JishoSelectMode
from scripts.scrappers.NeocitiesSelectMode import NeocitiesSelectMode
from pathlib import Path

class scrapperConfigParser():
    def __init__(self, filepath: str):
        self.autoselect_definition = JishoSelectMode()
        self.autoselect_sentence = NeocitiesSelectMode()
        self.max_results_displayed = 20
        self.anki_col_path = None
        self.use_cache = None
        self.clear_cache_on_complete = None
        self.clear_vocab_on_complete = None
        with open(filepath, 'r') as f:
            lines = [l for l in f.readlines() if not match(r'^\#', l)]
            params = {}
            for l in lines:
                param_match = match(r'(^[^=]+)=(.*$)', l)
                if not param_match:
                    continue
                params[param_match.group(1)] = param_match.group(2)
            
            assert isinstance(self.autoselect_sentence, NeocitiesSelectMode)
            for key, item in params.items():
                match key:
                    case "max_results_displayed":
                        self.max_results_displayed = self.parseInt(item)
                    case "expression_autoselect":
                        self.autoselect_definition.autoselect_expression_mode = self.parseSelectMode(item)
                    case "jlpt_filter":
                        self.autoselect_definition.jlpt_filter = self.parseInt(item)
                    case "exact_match_autoselect":
                        self.autoselect_definition.is_exact_match_autoselect = self.parseBool(item)
                    case "meaning_autoselect":
                        self.autoselect_definition.autoselect_meaning_mode = self.parseSelectMode(item)
                    case "word_audio_download":
                        self.autoselect_definition.enable_word_sound_download = not item == "NO"
                    case "word_audio_auto_download":
                        self.autoselect_definition.auto_download_sounds = self.parseBool(item)
                    case "sentence_select_mode":
                        self.autoselect_sentence.mode = self.parseSentenceSelectMode(item)
                    case "sentence_quantity":
                        self.autoselect_sentence.quantity = self.parseInt(item)
                    case "sentence_min_length":
                        self.autoselect_sentence.min_length = self.parseInt(item)
                    case "sentence_max_length":
                        self.autoselect_sentence.max_length = self.parseInt(item)
                    case "sentence_len_distribution":
                        self.autoselect_sentence.length_distribution = self.parseSentenceDistributionMode(item)
                    case "auto_validate_random":
                        self.autoselect_sentence.auto_validate_random = self.parseBool(item)
                    case "download_sentence_audio":
                        self.autoselect_sentence.download_audio = self.parseBool(item)
                    case "anki_collection_file_path":
                        self.anki_col_path = self.parsePath(item)
                    case "use_cache":
                        self.use_cache = self.parseBool(item)
                    case "clear_cache_on_complete":
                        self.clear_cache_on_complete = self.parseBool(item)
                    case "clear_vocab2add_complete":
                        self.clear_vocab_on_complete = self.parseBool(item)

        self.parsedParams = {
            "jisho_mode": self.autoselect_definition,
            "neocities_mode": self.autoselect_sentence,
        }
    
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
    def parseSentenceSelectMode(value: str) -> NeocitiesSelectMode.SelectMode:
        value = match(r'^(MANUAL|AUTO)$', value)
        if not value:
            return NeocitiesSelectMode.SelectMode.NONE
        value = value.group(0)
        return NeocitiesSelectMode.SelectMode(["MANUAL", "AUTO"].index(value))
    
    @staticmethod
    def parseSentenceDistributionMode(value: str) -> NeocitiesSelectMode.LengthDistribution:
        value = match(r'^(RANDOM|EVEN)$', value)
        if not value:
            return NeocitiesSelectMode.LengthDistribution.NONE
        value = value.group(0)
        return NeocitiesSelectMode.LengthDistribution(["EVEN", "RANDOM"].index(value))
    
    @staticmethod
    def parseSelectMode(value: str) -> JishoSelectMode.SelectMode:
        value = match(r'^(FIRST|SELECT|ALL)$', value)
        if not value:
            return JishoSelectMode.SelectMode.NONE
        value = value.group(0)
        return JishoSelectMode.SelectMode(["FIRST", "SELECT", "ALL"].index(value))
    
    @staticmethod
    def parsePath(value: str) -> Path:
        value: Path = Path(value)
        if not value.is_file():
            return None
        return value

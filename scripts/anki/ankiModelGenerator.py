from anki.storage import Collection
from typing import NamedTuple
from anki.models import  NotetypeDict
import logging
from scripts.anki.notes_templates import kanji_styles, kanji_resti_front_template, kanji_back_template, kanji_expre_front_template
from scripts.anki.notes_templates import vocab_styles, vocab_resti_front_template, vocab_back_template, vocab_expre_front_template, vocab_back_template
from scripts.anki.ankiConfig import AnkiConfig

EZModels = NamedTuple("EZModels", [("kanji", NotetypeDict), ("vocab", NotetypeDict)])

class AnkiModelGen():
    logger = logging.getLogger(__name__)
    def __init__(self, col: Collection, vocab_model_name: str, kanji_model_name: str, anki_config: AnkiConfig):
        self.col = col
        self.vocab_model_name = vocab_model_name
        self.kanji_model_name = kanji_model_name
        self.show_furigana_timeout = anki_config.furigana_timeout
        self.show_sentence_timeout = anki_config.sentence_timeout
        self.show_resti_readings_timeout = anki_config.resti_readings_timeout
        self.show_expr_readings_timeout = anki_config.expr_readings_timeout
        self.min_meanings = anki_config.min_meanings
        self.min_sentences = anki_config.min_sentences
        self.max_compounds = anki_config.min_compounds
        self.max_compound_meanings = anki_config.min_compound_meanings

    def findModels(self) -> EZModels:
        self.kanji_model = None
        self.vocab_model = None
        models = self.col.models.all()
        for m in models:
            if m['name'] == self.kanji_model_name:
                self.logger.info("Found kanji note model in Anki")
                self.kanji_model = self.col.models.get(m['id'])
                continue
            if m['name'] == self.vocab_model_name:
                self.logger.info("Found vocab note model in Anki")
                self.vocab_model = self.col.models.get(m['id'])
        
        if not self.kanji_model:
            self.logger.info("Kanji note model not found")
            self.kanji_model = self.genKanjiModel()
        else:
            self.updateKanjiModel()

        if not self.vocab_model:
            self.logger.info("Vocab note model not found")
            self.vocab_model = self.genVocabModel()
        else:
            self.updateVocabModel()
        self.col.models.update(self.vocab_model)
        self.col.models.update(self.kanji_model)
        
        return EZModels(self.kanji_model, self.vocab_model)

    def genKanjiModel(self) -> NotetypeDict:
        self.logger.info("Generating kanji note model...")
        anki_models = self.col.models
        model = anki_models.new(self.kanji_model_name)
        anki_models.add_field(model, anki_models.new_field("Kanji"))
        anki_models.add_field(model, anki_models.new_field("Meaning"))
        anki_models.add_field(model, anki_models.new_field("OnYomi"))
        anki_models.add_field(model, anki_models.new_field("KunYomi"))
        anki_models.add_field(model, anki_models.new_field("Stroke Order Image"))
        anki_models.add_field(model, anki_models.new_field("JLPT"))
        anki_models.add_field(model, anki_models.new_field("Ranking"))
        for r in ["OnYomi", "KunYomi"]:
            for i in range(10):
                for t in ["Word", "Furigana", "Meaning"]:
                    anki_models.add_field(model, anki_models.new_field(f"{r} Compound {i+1} {t}"))
        
        restitution_template = anki_models.new_template("Restitution Card")
        expression_template = anki_models.new_template("Expression Card")
        back_templ = kanji_back_template.replace("MAX_SHOW_COMPOUNDS", str(self.max_compounds)).replace("MAX_SHOW_COMPOUND_MEANINGS", str(self.max_compound_meanings))
        restitution_template["qfmt"] = kanji_resti_front_template.replace("SHOW_READING_TIMEOUT", str(self.show_resti_readings_timeout))
        restitution_template["afmt"] = back_templ
        expression_template["qfmt"] = kanji_expre_front_template.replace("SHOW_READING_TIMEOUT", str(self.show_expr_readings_timeout))
        expression_template["afmt"] = back_templ
        model["css"] = kanji_styles

        anki_models.add_template(model, restitution_template)
        anki_models.add_template(model, expression_template)

        anki_models.add_dict(model)
        return anki_models.by_name(self.kanji_model_name)
    
    def genVocabModel(self) -> NotetypeDict:
        self.logger.info("Generating vocab note model...")
        anki_models = self.col.models
        model = anki_models.new(self.vocab_model_name)
        anki_models.add_field(model, anki_models.new_field("Expression"))
        anki_models.add_field(model, anki_models.new_field("Kanjis"))
        anki_models.add_field(model, anki_models.new_field("Furigana"))
        anki_models.add_field(model, anki_models.new_field("Romaji"))
        anki_models.add_field(model, anki_models.new_field("Meanings"))
        anki_models.add_field(model, anki_models.new_field("Audio"))
        anki_models.add_field(model, anki_models.new_field("JLPT"))
        anki_models.add_field(model, anki_models.new_field("Transitivity"))
        for infl in ["Non-past", "Non-past polite", "Past", "Past polite", "Te-form", "Potential", "Passive", "Causative", "Causative Passive", "Imperative"]:
            for m in ["Affirmative", "Negative"]:
                anki_models.add_field(model, anki_models.new_field(f"Inflection - {infl} - {m}"))
        for i in range(20):
            for f in ["Japanese", "English", "Audio"]:
                anki_models.add_field(model, anki_models.new_field(f"Sentence {i+1} {f}"))

        restitution_template = anki_models.new_template("Restitution Card")
        expression_template = anki_models.new_template("Expression Card")
        back_templ = vocab_back_template.replace("MIN_SHOW_MEANINGS", str(self.min_meanings)).replace("MIN_SHOW_SENTENCES", str(self.min_sentences))
        
        restitution_template["qfmt"] = vocab_resti_front_template.replace("SHOW_FURIGANA_TIMEOUT", str(self.show_furigana_timeout))
        restitution_template["afmt"] = back_templ
        expression_template["qfmt"] = vocab_expre_front_template.replace("SHOW_SENTENCE_TIMEOUT", str(self.show_sentence_timeout))
        expression_template["afmt"] = back_templ
        model["css"] = vocab_styles

        anki_models.add_template(model, restitution_template)
        anki_models.add_template(model, expression_template)

        anki_models.add_dict(model)
        return anki_models.by_name(self.vocab_model_name)
    
    def updateKanjiModel(self):
        resti_template = self.kanji_model["tmpls"][0]
        expre_template = self.kanji_model["tmpls"][1]
        back_templ = kanji_back_template.replace("MAX_SHOW_COMPOUNDS", str(self.max_compounds)).replace("MAX_SHOW_COMPOUND_MEANINGS", str(self.max_compound_meanings))
        resti_template["qfmt"] = kanji_resti_front_template.replace("SHOW_READING_TIMEOUT", str(self.show_resti_readings_timeout))
        resti_template["afmt"] = back_templ
        expre_template["qfmt"] = kanji_expre_front_template.replace("SHOW_READING_TIMEOUT", str(self.show_expr_readings_timeout))
        expre_template["afmt"] = back_templ
        self.kanji_model["css"] = kanji_styles
        self.col.models.update_dict(self.kanji_model)
    
    def updateVocabModel(self):
        resti_template = self.vocab_model["tmpls"][0]
        expre_template = self.vocab_model["tmpls"][1]
        resti_template["qfmt"] = vocab_resti_front_template.replace("SHOW_FURIGANA_TIMEOUT", str(self.show_furigana_timeout))
        back_templ = vocab_back_template.replace("MIN_SHOW_MEANINGS", str(self.min_meanings)).replace("MIN_SHOW_SENTENCES", str(self.min_sentences))
        resti_template["afmt"] = back_templ
        expre_template["qfmt"] = vocab_expre_front_template.replace("MIN_SHOW_MEANINGS", str(self.min_meanings)).replace("MIN_SHOW_SENTENCES", str(self.min_sentences)).replace("SHOW_SENTENCE_TIMEOUT", str(self.show_sentence_timeout))
        expre_template["afmt"] = back_templ
        self.vocab_model["css"] = vocab_styles
        self.col.models.update_dict(self.vocab_model)

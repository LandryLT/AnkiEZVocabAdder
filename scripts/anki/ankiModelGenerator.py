from anki.storage import Collection
from typing import NamedTuple
from anki.models import  NotetypeDict
import logging

EZModels = NamedTuple("EZModels", [("kanji", NotetypeDict), ("vocab", NotetypeDict)])

class AnkiModelGen():
    logger = logging.getLogger(__name__)
    def __init__(self, col: Collection, vocab_model_name: str, kanji_model_name: str):
        self.col = col
        self.vocab_model_name = vocab_model_name
        self.kanji_model_name = kanji_model_name

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
        if not self.vocab_model:
            self.logger.info("Vocab note model not found")
            self.vocab_model = self.genVocabModel()
        
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

        restitution_template["qfmt"] = "{{Kanji}}"
        restitution_template["afmt"] = "{{FrontSide}}<hr id='answer'>{{Meaning}}"
        expression_template["qfmt"] = "{{Meaning}}"
        expression_template["afmt"] = "{{FrontSide}}<hr id='answer'>{{Kanji}}"

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
                
        restitution_template["qfmt"] = "{{Expression}}"
        restitution_template["afmt"] = "{{FrontSide}}<hr id='answer'>{{Meanings}}"
        expression_template["qfmt"] = "{{Meanings}}"
        expression_template["afmt"] = "{{FrontSide}}<hr id='answer'>{{Expression}}"

        anki_models.add_template(model, restitution_template)
        anki_models.add_template(model, expression_template)

        anki_models.add_dict(model)
        return anki_models.by_name(self.vocab_model_name)

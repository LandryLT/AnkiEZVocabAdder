from importlib.resources import files
# from importlib.resources.abc import Traversable


templates = files("scripts").joinpath("anki", "notes_templates")
# assert isinstance(templates, Traversable)
kanji = templates.joinpath("kanji_notes")
vocab = templates.joinpath("vocab_notes")

kanji_back_template = kanji.joinpath("back.html").read_text(encoding="utf-8")
kanji_resti_front_template = kanji.joinpath("resti_front.html").read_text(encoding="utf-8")
kanji_expre_front_template = kanji.joinpath("expre_front.html").read_text(encoding="utf-8")
kanji_styles = kanji.joinpath("styles.css").read_text(encoding="utf-8")


vocab_back_template = vocab.joinpath("back.html").read_text(encoding="utf-8")
vocab_resti_front_template = vocab.joinpath("resti_front.html").read_text(encoding="utf-8")
vocab_expre_front_template = vocab.joinpath("expre_front.html").read_text(encoding="utf-8")
vocab_styles = vocab.joinpath("styles.css").read_text(encoding="utf-8")
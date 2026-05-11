from anki.storage import Collection
from anki.decks import Deck
import logging
from copy import deepcopy
from typing import NamedTuple

VocabVerb = NamedTuple("VocabVerb", [("deck", Deck), ("transitive", Deck), ("intransitive", Deck)])
VocabAdj = NamedTuple("VocabAdj", [("deck", Deck), ("i", Deck), ("a", Deck)])
VocabJLPTDeck = NamedTuple("VocabJLPTDeck", [("deck", Deck), ("verbs", VocabVerb), ("ajectives", VocabAdj), ("nouns", Deck), ("expression", Deck), ("others", Deck)])

VocabDecks = NamedTuple("VocabDecks", [("deck", Deck), ("n1", VocabJLPTDeck), ("n2", VocabJLPTDeck), ("n3", VocabJLPTDeck), ("n4", VocabJLPTDeck), ("n5", VocabJLPTDeck)])
KanjiDecks = NamedTuple("KanjiDecks", [("deck", Deck), ("n1", Deck), ("n2", Deck), ("n3", Deck), ("n4", Deck), ("n5", Deck)])
EZDecks = NamedTuple("EZDecks", [("deck", Deck), ("vocab", VocabDecks), ("kanji", KanjiDecks)])

class AnkiDeckGen():
    logger = logging.getLogger(__name__)
    def __init__(self, col: Collection):
        self.col = col

    def findDecks(self) -> EZDecks:
        deck_tree = self._deckTreeBuilder()
        flattened_deck_names = self._getDeckTreePaths(deck_tree)
        all_decks = self.col.decks.all_names_and_ids()
        for deck_name in flattened_deck_names:
            if deck_name not in [d.name for d in all_decks]:
                self.logger.info(f'{deck_name} not found, creating new deck')
                new_deck = self.col.decks.new_deck()
                new_deck.name = deck_name
                self.col.decks.add_deck(new_deck)
        
        v_d = self._getVocabDecks()
        k_d = self._getKanjiDecks()
        return EZDecks(self.col.decks.by_name("EZAnki"), v_d, k_d)
        
    def _getKanjiDecks(self) -> KanjiDecks:
        base_path = "EZAnki::Kanji::_JLPT N1_::_JLPT N2_::_JLPT N3_::_JLPT N4_::_JLPT N5_"
        split_path = base_path.split("::")
        kanji_deck = self.col.decks.by_name('::'.join(split_path[:2]))
        jlpt_decks = []
        for i in range(5):
            jlpt_decks.append(self.col.decks.by_name('::'.join(split_path[:3+i])))
        return KanjiDecks(kanji_deck, *jlpt_decks)
        
    def _getVocabDecks(self) -> VocabDecks:
        base_path = "EZAnki::Vocabulary::_JLPT N1_::_JLPT N2_::_JLPT N3_::_JLPT N4_::_JLPT N5_"
        split_path = base_path.split("::")
        kanji_deck = self.col.decks.by_name('::'.join(split_path[:2]))
        jlpt_decks = []
        for i in range(5):
            curr_branch = '::'.join(split_path[:3+i])
            jlpt_d = self.col.decks.by_name(curr_branch)
            verb_branch = curr_branch + "::Verbs"
            verb_d = VocabVerb(self.col.decks.by_name(verb_branch),
                               self.col.decks.by_name(verb_branch+"::Transitive"),
                               self.col.decks.by_name(verb_branch+"::Intransitive"),)
            adj_branch = curr_branch + "::Adjectives"
            adj_d = VocabAdj(self.col.decks.by_name(adj_branch),
                             self.col.decks.by_name(adj_branch+"::I-Adjective"),
                             self.col.decks.by_name(adj_branch+"::Na-Adjective"),)
            noun_d = self.col.decks.by_name(curr_branch+"::Nouns")
            expr_d = self.col.decks.by_name(curr_branch+"::Expressions")
            other_d = self.col.decks.by_name(curr_branch+"::Others")
            jlpt_decks.append(VocabJLPTDeck(jlpt_d, verb_d, adj_d, noun_d, expr_d, other_d))
            
        return VocabDecks(kanji_deck, *jlpt_decks)
    
    @staticmethod
    def _getDeckTreePaths(deck_tree: dict, join_with: str = "::") -> list[str]:
        output = []
        def recursive_branch_finder(tree: dict, c_branch: list):
            for k, v in tree.items():
                new_branch = c_branch.copy()
                new_branch.append(k)
                if isinstance(v, dict):
                    if not v.keys():
                        output.append(join_with.join(new_branch))
                    else:
                        recursive_branch_finder(v ,new_branch)
        recursive_branch_finder(deck_tree, [])
        return output

    @staticmethod
    def _deckTreeBuilder() -> dict:
        jlpts = { "_JLPT N1_": { "_JLPT N2_": { "_JLPT N3_": { "_JLPT N4_": { "_JLPT N5_": {}}}}}}
        word_types = {
            "Verbs": {
                "Transitive":{},
                "Intransitive":{},
            },
            "Adjectives":{
                "I-Adjective":{},
                "Na-Adjective":{}
            },
            "Nouns":{},
            "Expressions":{},
            "Others":{}
        }
        deck_tree = {
            "EZAnki":{
                "Kanji": deepcopy(jlpts),
                "Vocabulary": deepcopy(jlpts),
            }
        }
        
        def _inject_word_types(tree: dict, template: dict):
            for value in tree.values():
                if isinstance(value, dict):
                    for wt_key, wt_value in template.items():
                        value.setdefault(wt_key, deepcopy(wt_value))
                    for child_key, child_value in value.items():
                        assert isinstance(child_key, str)
                        if child_key.startswith("_JLPT N"):
                            _inject_word_types({child_key: child_value}, template)
        _inject_word_types(deck_tree["EZAnki"]["Vocabulary"], word_types)
        return deck_tree

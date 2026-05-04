import re

rawCharText = """あ ア a	い イ i	う ウ u	え エ e	お オ o
か カ ka	き キ ki	く ク ku	け ケ ke	こ コ ko	きゃ キャ kya	きゅ キュ kyu	きょ キョ kyo
さ サ sa	し シ shi	す ス su	せ セ se	そ ソ so	しゃ シャ sha	しゅ シュ shu	しょ ショ sho
た タ ta	ち チ chi	つ ツ tsu	て テ te	と ト to	ちゃ チャ cha	ちゅ チュ chu	ちょ チョ cho
な ナ na	に ニ ni	ぬ ヌ nu	ね ネ ne	の ノ no	にゃ ニャ nya	にゅ ニュ nyu	にょ ニョ nyo
は ハ ha	ひ ヒ hi	ふ フ fu	へ ヘ he	ほ ホ ho	ひゃ ヒャ hya	ひゅ ヒュ hyu	ひょ ヒョ hyo
ま マ ma	み ミ mi	む ム mu	め メ me	も モ mo	みゃ ミャ mya	みゅ ミュ myu	みょ ミョ myo
や ヤ ya		ゆ ユ yu		よ ヨ yo	
ら ラ ra	り リ ri	る ル ru	れ レ re	ろ ロ ro	りゃ リャ rya	りゅ リュ ryu	りょ リョ ryo
わ ワ wa	ゐ ヰ i †		ゑ ヱ e †	を ヲ o ‡	
ん ン n	
が ガ ga	ぎ ギ gi	ぐ グ gu	げ ゲ ge	ご ゴ go	ぎゃ ギャ gya	ぎゅ ギュ gyu	ぎょ ギョ gyo
ざ ザ za	じ ジ ji	ず ズ zu	ぜ ゼ ze	ぞ ゾ zo	じゃ ジャ ja	じゅ ジュ ju	じょ ジョ jo
だ ダ da	ぢ ヂ ji	づ ヅ zu	で デ de	ど ド do	ぢゃ ヂャ ja	ぢゅ ヂュ ju	ぢょ ヂョ jo
ば バ ba	び ビ bi	ぶ ブ bu	べ ベ be	ぼ ボ bo	びゃ ビャ bya	びゅ ビュ byu	びょ ビョ byo
ぱ パ pa	ぴ ピ pi	ぷ プ pu	ぺ ペ pe	ぽ ポ po	ぴゃ ピャ pya	ぴゅ ピュ pyu	ぴょ ピョ pyo """
rawChartText_extended = """
イィ yi		イェ ye	
ウァ wa*	ウィ wi	ウゥ wu*	ウェ we	ウォ wo
ウュ wyu	
ヴァ va	ヴィ vi	ヴ vu⁑	ヴェ ve	ヴォ vo
ヴャ vya		ヴュ vyu	ヴィェ vye	ヴョ vyo
キェ kye	
ギェ gye	
クァ kwa	クィ kwi		クェ kwe	クォ kwo
クヮ kwa	
グァ gwa	グィ gwi		グェ gwe	グォ gwo
グヮ gwa	
シェ she	
ジェ je	
スィ si	
ズィ zi	
チェ che	
ツァ tsa	ツィ tsi		ツェ tse	ツォ tso
ツュ tsyu	
ティ ti	トゥ tu	
テュ tyu	
ディ di	ドゥ du	
デュ dyu	
ニェ nye	
ヒェ hye	
ビェ bye	
ピェ pye	
ファ fa	フィ fi		フェ fe	フォ fo
フャ fya		フュ fyu	フィェ fye	フョ fyo
ホゥ hu	
ミェ mye	
リェ rye	
ラ゜ la	リ゜ li	ル゜ lu	レ゜ le	ロ゜ lo
リ゜ャ lya		リ゜ュ lyu	リ゜ェ lye	リ゜ョ lyo
ヷ va⁂	ヸ vi⁂		ヹ ve⁂	ヺ vo⁂
"""

mappingTexts = re.findall(r'(\S{1,2})\s(\S{1,2})\s([a-z]+)\s', rawCharText)
mappingTextsExtended = re.findall(r'(\S{1,3})\s([a-z]+)[*⁑⁂]?\s', rawChartText_extended)
class Mapping():
    def __init__(self, hiragana, katakana, romaji):
        self.hiragana = hiragana
        self.katakana = katakana
        self.romaji = romaji

mappings = [Mapping(h, k, r) for h, k, r in mappingTexts]

for k, r in mappingTextsExtended:
    h = None if k != "ヴ" else "ゔ"
    mappings.append(Mapping(h, k, r))

mappings.reverse()

def convertToRomaji(text: str):
    for mapping in mappings:
        text = text.replace(mapping.katakana, mapping.romaji)
        if mapping.hiragana:
            text = text.replace(mapping.hiragana, mapping.romaji)

    for i, c in enumerate(text):
        if c in ("ッ", "っ"):
            if i == len(text) - 1:
                text += "'"
                continue
            text = text[:i] + text[i+1] + text[i+1:]

    for i, c in enumerate(text):
        if c in ("ー",):
            if i == 0:
                continue
            text = text[:i] + text[i-1] + text[i+1:]
    
    return text


if __name__ == "__main__":
    print(convertToRomaji("あえーあーっと"))
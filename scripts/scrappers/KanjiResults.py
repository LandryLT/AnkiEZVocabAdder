from collections import namedtuple
import re
import uuid
import asyncio
import requests
import os
image_folder = './images/'
KanjiResultsRaw = namedtuple("KanjiResultsRaw", ["meaning", "on_yomi", "kun_yomi", "jlpt", "ranking", "compounds"], defaults=[str, list[str], list[str], int, str, list[str]])
class KanjiResults():
    def __init__(self, kanji: str, raw: KanjiResultsRaw):
        self.kanji = kanji
        self.meaning = raw.meaning
        self.on_yomi = raw.on_yomi
        self.kun_yomi = raw.kun_yomi
        self.jlpt = raw.jlpt
        ranking_match = re.findall(r'\d+\b', raw.ranking) if raw.ranking else [-1, 1]
        self.ranking = int(ranking_match[0])/int(ranking_match[1])
        self.compounds = raw.compounds
        self.img_file = ''
    
    async def downloadImage(self):
        img_url = 'https://kanji.sljfaq.org/kanjivg/memory.cgi?c='+hex(ord(self.kanji))
        download_file_name = f'{self.kanji}_{str(uuid.uuid1())}.png'
        download_file_path = image_folder + download_file_name

        r = await asyncio.get_event_loop().run_in_executor(None, requests.get, img_url)
        with open(download_file_path, "wb") as file:
            for chunk in r.iter_content():
                file.write(chunk)
        self.img_file = os.path.abspath(download_file_path)
        return self.img_file
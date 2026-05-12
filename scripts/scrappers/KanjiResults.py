from typing import NamedTuple
import re
import uuid
import asyncio
import requests
import os
from scripts.caching.cacheSearch import SearchCache
from scripts.scrappers.Scrapper import cacheable
kanji_img_cache = SearchCache("./caches/kanjis/strokecache")
image_folder = './caches/images/'
KanjiResultsRaw = NamedTuple("KanjiResultsRaw", [("meaning", str), ("on_yomi", list[str]), ("kun_yomi", list[str]), ("jlpt", int), ("ranking", str), ("compounds", dict[str, list[str]])])
class KanjiResult():
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
    
    @cacheable(kanji_img_cache)
    async def downloadImage(self):
        if self.kanji in kanji_img_cache.cache.keys() and os.path.isfile(kanji_img_cache.cache[self.kanji][0]):
            self.img_file = os.path.abspath(kanji_img_cache.cache[self.kanji][0])
            return self.img_file
        img_url = 'https://kanji.sljfaq.org/kanjivg/memory.cgi?c='+hex(ord(self.kanji))
        download_file_name = f'{self.kanji}_{str(uuid.uuid1())}.png'
        download_file_path = image_folder + download_file_name

        r = await asyncio.get_event_loop().run_in_executor(None, requests.get, img_url)
        with open(download_file_path, "wb") as file:
            for chunk in r.iter_content():
                file.write(chunk)
        self.img_file = os.path.abspath(download_file_path)
        kanji_img_cache.addToCache(self.kanji, self.img_file)
        return self.img_file
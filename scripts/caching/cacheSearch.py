from pathlib import Path
from typing import Any
import pickle
import os
from collections import defaultdict

SearchCacheData = dict[str, list[Any]]
class SearchCache():
    def __init__(self, cache_path: Path | str):
        if isinstance(cache_path, str):
            cache_path = Path(cache_path)
        self.cache_path: Path = cache_path
        self.cache = defaultdict(list, self.load_pickled_cache())

    def clearCache(self):
        self.cache = defaultdict(list)
        if self.cache_path.is_file():
            os.remove(self.cache_path)

    def addToCache(self, key: str, value: Any):
        self.cache[key].append(value)

    def save_pickled_cache(self, cache_data: SearchCacheData | None = None):
        cache_data = self.cache if not cache_data else cache_data
        prev_data = self.load_pickled_cache()
        combined_data = prev_data | cache_data
        with open(self.cache_path, 'wb') as f:
            pickle.dump(combined_data, f)
            
    def load_pickled_cache(self) -> SearchCacheData:
        if not self.cache_path.is_file():
            with open(self.cache_path, 'wb')as f:
                empty_data = SearchCacheData({})
                pickle.dump(empty_data, f)
            return empty_data
        with open(self.cache_path, 'rb') as f:
            s_data = pickle.load(f)
        return s_data
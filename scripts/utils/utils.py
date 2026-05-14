from collections import defaultdict
from typing import Any
def list_duplicates(seq) -> tuple[tuple[Any, int]]:
    tally = defaultdict(list)
    for i,item in enumerate(seq):
        tally[item].append(i)
    return ((key,locs) for key,locs in tally.items() 
                            if len(locs)>1)

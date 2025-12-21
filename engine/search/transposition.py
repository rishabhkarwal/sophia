from dataclasses import dataclass
from typing import Optional, Any
import sys

# flag types
FLAG_EXACT = 0 # know the exact score
FLAG_LOWERBOUND = 1 # alpha cutoff: score is at least this value (beta cutoff in search)
FLAG_UPPERBOUND = 2 # beta cutoff: score is at most this value (failed low)

@dataclass(slots=True)
class TTEntry:
    key: int # zobrist hash key
    depth: int # depth searched
    score: int # evaluation
    flag: int # exact, lower, upper
    best_move: Any # the best move found

# sample entry to measure its actual size in memory
sample_key = 0xFFFFFFFFFFFFFFFF # max 64-bit integer to assume the full size of the hash
sample_entry = TTEntry(sample_key, 0, 0, 0, None)
BYTES_PER_ENTRY = sys.getsizeof(sample_entry) + sys.getsizeof(sample_key) + 8

class TranspositionTable:
    def __init__(self, size_mb: int = 64):
        """Initialise TT with a fixed size"""
        total_bytes = size_mb * 1024 * 1024
        self.size = total_bytes // BYTES_PER_ENTRY
        
        self.table = [None] * self.size
        self.entries_count = 0

    def _get_index(self, key: int) -> int:
        return key % self.size

    def store(self, key: int, depth: int, score: int, flag: int, best_move):
        index = self._get_index(key)
        existing: Optional[TTEntry] = self.table[index]
        # replacement: if empty or if new search is deeper / same depth
        if existing is None or depth >= existing.depth:
            self.table[index] = TTEntry(key, depth, score, flag, best_move)
            self.entries_count += 1

    def probe(self, key: int) -> Optional[TTEntry]:
        index = self._get_index(key)
        entry = self.table[index]
        
        if entry and entry.key == key: return entry
        
        return None
    
    def clear(self):
        self.table = [None] * self.size

    def get_hashfull(self) -> int:
        """Returns occupancy in permill (0-1000)"""
        return int(self.entries_count / self.size * 1000)
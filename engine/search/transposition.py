from dataclasses import dataclass
from typing import Optional, Any

# flag types
FLAG_EXACT = 0 # know the exact score
FLAG_LOWERBOUND = 1 # alpha cutoff: score is at least this value (beta cutoff in search)
FLAG_UPPERBOUND = 2 # beta cutoff: score is at most this value (failed low)

@dataclass(slots=True)
class TTEntry:
    key: int # Zobrist hash key
    depth: int # depth searched
    score: int # evaluation
    flag: int # EXACT, LOWERBOUND, UPPERBOUND
    best_move: Any # the best move found

class TranspositionTable:
    def __init__(self, size_mb: int = 64):
        """Initialise TT with a fixed size"""
        # using a safe estimate of ~128 bytes per entry 
        self.size = (size_mb * 1024 * 1024) // 128
        self.table = [None] * self.size

    def _get_index(self, key: int) -> int:
        return key % self.size

    def store(self, key: int, depth: int, score: int, flag: int, best_move):
        index = self._get_index(key)
        existing: Optional[TTEntry] = self.table[index]
        
        # replacement: if empty or if new search is deeper/same depth
        if existing is None or depth >= existing.depth:
            self.table[index] = TTEntry(key, depth, score, flag, best_move)

    def probe(self, key: int) -> Optional[TTEntry]:
        index = self._get_index(key)
        entry = self.table[index]
        
        if entry and entry.key == key:
            return entry
        return None
    
    def clear(self):
        self.table = [None] * self.size
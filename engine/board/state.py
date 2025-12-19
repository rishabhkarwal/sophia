from dataclasses import dataclass
from typing import Dict, List, Tuple, Any, Optional

from engine.core.constants import ALL_PIECES

@dataclass(frozen=False, slots=True)
class State:
    bitboards: Dict[str, int]
    player: int
    castling: int
    en_passant: int
    halfmove_clock: int
    fullmove_number: int
    history: List[Tuple[Any, ...]]
    hash: Optional[int] = None 

    def __post_init__(self):
        """Automatically compute hash if it wasn't provided during initialisation"""
        if self.hash is None:
            from engine.core.zobrist import compute_hash
            self.hash = compute_hash(self)

    def get_piece_at(self, square):
        """Find which piece occupies a square"""
        mask = 1 << square
        for piece in ALL_PIECES:
            if self.bitboards.get(piece, 0) & mask: return piece
        return None
from dataclasses import dataclass
from typing import Dict, List, Optional

from engine.core.constants import ALL_PIECES
from engine.core.zobrist import compute_hash

@dataclass(frozen=False, slots=True)
class State:
    bitboards: Dict[str, int]
    is_white: bool
    castling_rights: int
    en_passant_square: int
    halfmove_clock: int
    fullmove_number: int
    history: List[int]
    hash: Optional[int] = None 
    # incremental evaluation fields
    mg_score: int = 0
    eg_score: int = 0
    phase: int = 0

    def __post_init__(self):
        """Automatically compute hash if it wasn't provided during initialisation"""
        if self.hash is None: self.hash = compute_hash(self)

    def get_piece_at(self, square):
        """Find which piece occupies a square"""
        mask = 1 << square
        for piece in ALL_PIECES:
            if self.bitboards.get(piece, 0) & mask: return piece
        return None
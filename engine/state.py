from dataclasses import dataclass
from typing import Dict, List, Tuple, Any

from .constants import ALL_PIECES, WHITE_PIECES, BLACK_PIECES

@dataclass(frozen=False, slots=True)
class State:
    bitboards: Dict[str, int]
    player: int
    castling: int
    en_passant: int
    halfmove_clock: int
    fullmove_number: int
    history: List[Tuple[Any, ...]]

    def get_piece_at(self, square):
        """Find which piece occupies a square"""
        mask = 1 << square
        for piece in ALL_PIECES:
            if self.bitboards.get(piece, 0) & mask: return piece
        return None
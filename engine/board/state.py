from dataclasses import dataclass
from typing import List
from engine.core.constants import NULL

@dataclass(slots=True)
class State:
    bitboards: List[int]
    board: List[int]
    is_white: bool
    castling_rights: int
    en_passant_square: int
    halfmove_clock: int
    fullmove_number: int
    history: List[int]
    hash: int = 0
    
    mg_score: int = 0
    eg_score: int = 0
    phase: int = 0
    
    def get_piece_at(self, square):
        p = self.board[square]
        return p if p != NULL else None
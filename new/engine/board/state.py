from dataclasses import dataclass, field
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
    
    piece_counts: List[int]

    context_stack: List[tuple] = field(default_factory=list) # stack for undo information

    hash: int = 0
    mg_score: int = 0
    eg_score: int = 0
    phase: int = 0
    
    # incremental evaluation tracking for performance
    white_passed_pawns: int = 0  # bitboard of white passed pawns
    black_passed_pawns: int = 0  # bitboard of black passed pawns
    
    # track last moved piece for repetition detection
    last_moved_piece_sq: int = NULL
    
    def get_piece_at(self, square):
        p = self.board[square]
        return p if p != NULL else None
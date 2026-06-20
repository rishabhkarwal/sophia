import random
from typing import List
from dataclasses import dataclass

from engine.core.constants import NULL as _NULL

@dataclass(slots=True)
class ZobristKeys:
    pieces: List[List[int]]
    castling: List[int]
    en_passant: List[int]
    black_to_move: int

def init_zobrist():
    random.seed(42)

    pieces = [[random.getrandbits(64) for _ in range(64)] for _ in range(16)]
    castling = [random.getrandbits(64) for _ in range(16)]
    ep = [random.getrandbits(64) for _ in range(9)]
    black_to_move = random.getrandbits(64)

    return pieces, castling, ep, black_to_move


ZOBRIST_KEYS = ZobristKeys(*init_zobrist())

def compute_hash(state) -> int:
    h = 0

    for sq in range(64):
        piece = state.board[sq]
        if piece != _NULL: h ^= ZOBRIST_KEYS.pieces[piece][sq]

    h ^= ZOBRIST_KEYS.castling[state.castling_rights]

    if state.en_passant_square != _NULL:
        file = state.en_passant_square % 8
        h ^= ZOBRIST_KEYS.en_passant[file]
    else:
        h ^= ZOBRIST_KEYS.en_passant[8]

    if not state.is_white: h ^= ZOBRIST_KEYS.black_to_move

    return h

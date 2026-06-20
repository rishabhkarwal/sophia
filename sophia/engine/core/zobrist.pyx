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

cdef unsigned long long ZOBRIST_PIECES[16][64]
cdef unsigned long long ZOBRIST_CASTLING[16]
cdef unsigned long long ZOBRIST_EN_PASSANT[9]
cdef unsigned long long ZOBRIST_BLACK_TO_MOVE = <unsigned long long>ZOBRIST_KEYS.black_to_move


cdef void init_zobrist_c_tables():
    cdef int piece, sq, idx

    for piece in range(16):
        for sq in range(64):
            ZOBRIST_PIECES[piece][sq] = <unsigned long long>ZOBRIST_KEYS.pieces[piece][sq]

    for idx in range(16):
        ZOBRIST_CASTLING[idx] = <unsigned long long>ZOBRIST_KEYS.castling[idx]

    for idx in range(9):
        ZOBRIST_EN_PASSANT[idx] = <unsigned long long>ZOBRIST_KEYS.en_passant[idx]


init_zobrist_c_tables()


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

from typing import List
from engine.core.constants import (
    WHITE, BLACK,
    FILE_A, FILE_H, FILE_AB, FILE_GH,
    FULL_BOARD, NORTH
)
from engine.uci.utils import send_info_string

KNIGHT_ATTACKS: List[int] = [0] * 64
KING_ATTACKS: List[int]   = [0] * 64
WHITE_PAWN_ATTACKS: List[int] = [0] * 64
BLACK_PAWN_ATTACKS: List[int] = [0] * 64

# [square][blockers]
ROOK_TABLE: List[List[int]] = []
BISHOP_TABLE: List[List[int]] = []

ROOK_MASKS: List[int] = [0] * 64
BISHOP_MASKS: List[int] = [0] * 64

def generate_knight_attacks(square: int) -> int:
    attacks = 0
    bb = 1 << square
    if not (bb & FILE_H):  attacks |= (bb << 17)
    if not (bb & FILE_A):  attacks |= (bb << 15)
    if not (bb & FILE_GH): attacks |= (bb << 10)
    if not (bb & FILE_GH): attacks |= (bb >> 6)
    if not (bb & FILE_A):  attacks |= (bb >> 17)
    if not (bb & FILE_H):  attacks |= (bb >> 15)
    if not (bb & FILE_AB): attacks |= (bb << 6)
    if not (bb & FILE_AB): attacks |= (bb >> 10)
    return attacks & FULL_BOARD

def generate_king_attacks(square: int) -> int:
    attacks = 0
    bb = 1 << square
    if not (bb & FILE_H): attacks |= (bb << 1) | (bb << 9) | (bb >> 7)
    if not (bb & FILE_A): attacks |= (bb >> 1) | (bb >> 9) | (bb << 7)
    attacks |= (bb << NORTH) | (bb >> NORTH)
    return attacks & FULL_BOARD

def generate_pawn_attacks(square: int, colour: bool) -> int:
    attacks = 0
    bb = 1 << square
    if colour == WHITE:
        if not (bb & FILE_A): attacks |= (bb << 7)
        if not (bb & FILE_H): attacks |= (bb << 9)
    else:
        if not (bb & FILE_H): attacks |= (bb >> 7)
        if not (bb & FILE_A): attacks |= (bb >> 9)
    return attacks & FULL_BOARD

def generate_sliding_masks(deltas: List[tuple]) -> List[int]:
    masks = []
    for square in range(64):
        mask = 0
        rank, file = square // 8, square % 8
        for d_rank, d_file in deltas:
            r, f = rank + d_rank, file + d_file
            while 0 <= r <= 7 and 0 <= f <= 7:
                mask |= (1 << (r * 8 + f))
                r += d_rank
                f += d_file
        masks.append(mask)
    return masks

def generate_sliding_attacks(square: int, block: int, deltas: List[tuple]) -> int:
    attacks = 0
    rank, file = square // 8, square % 8
    for d_rank, d_file in deltas:
        r, f = rank + d_rank, file + d_file
        while 0 <= r <= 7 and 0 <= f <= 7:
            bit = 1 << (r * 8 + f)
            attacks |= bit
            if bit & block:
                break
            r += d_rank
            f += d_file
    return attacks

def init_sliders(table: List[List[int]], masks_list: List[int], deltas: List[tuple]):
    generated_masks = generate_sliding_masks(deltas)
    for i in range(64): 
        masks_list[i] = generated_masks[i]
    
    for square in range(64):
        mask = masks_list[square]
        bit_indices = [i for i in range(64) if (mask >> i) & 1]
        num_patterns = 1 << len(bit_indices)

        square_table = {}
        
        for i in range(num_patterns):
            blocker = 0
            for bit_index, pos in enumerate(bit_indices):
                if (i >> bit_index) & 1:
                    blocker |= (1 << pos)
            attacks = generate_sliding_attacks(square, blocker, deltas)
            square_table[blocker] = attacks
        
        table.append(square_table)

def init_tables():
    for square in range(64):
        KNIGHT_ATTACKS[square] = generate_knight_attacks(square)
        KING_ATTACKS[square] = generate_king_attacks(square)
        WHITE_PAWN_ATTACKS[square] = generate_pawn_attacks(square, WHITE)
        BLACK_PAWN_ATTACKS[square] = generate_pawn_attacks(square, BLACK)
    
    bishop_deltas = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
    BISHOP_TABLE = []
    init_sliders(BISHOP_TABLE, BISHOP_MASKS, bishop_deltas)
    
    rook_deltas = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    ROOK_TABLE = []
    init_sliders(ROOK_TABLE, ROOK_MASKS, rook_deltas)

    return BISHOP_TABLE, ROOK_TABLE

BISHOP_TABLE, ROOK_TABLE = init_tables()
send_info_string('initialised lookup tables')
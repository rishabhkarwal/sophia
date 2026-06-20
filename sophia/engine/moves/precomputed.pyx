from engine.core.constants import (
    WHITE, BLACK,
    FILE_A, FILE_H, FILE_AB, FILE_GH,
    FULL_BOARD, NORTH, EAST, WEST, SQUARE_TO_BB as _SQUARE_TO_BB
)
from engine.uci.utils import send_info_string

cdef unsigned long long KNIGHT_ATTACKS[64]
cdef unsigned long long KING_ATTACKS[64]
cdef unsigned long long WHITE_PAWN_ATTACKS[64]
cdef unsigned long long BLACK_PAWN_ATTACKS[64]
cdef unsigned long long BISHOP_MASKS[64]
cdef unsigned long long ROOK_MASKS[64]

BISHOP_TABLE = []
ROOK_TABLE = []

cdef int _NORTH = NORTH
cdef int _EAST  = EAST
cdef int _WEST  = WEST


cdef unsigned long long _knight_attacks(int sq):
    cdef unsigned long long bb = (<unsigned long long>1) << sq
    cdef unsigned long long attacks = 0
    cdef unsigned long long file_h_mask = FILE_H
    cdef unsigned long long file_a_mask = FILE_A
    cdef unsigned long long file_gh_mask = FILE_GH
    cdef unsigned long long file_ab_mask = FILE_AB
    cdef unsigned long long full_board_mask = FULL_BOARD
    if not (bb & file_h_mask):  attacks |= (bb << (_NORTH + _NORTH + _EAST))
    if not (bb & file_a_mask):  attacks |= (bb << (_NORTH + _NORTH + _WEST))
    if not (bb & file_gh_mask): attacks |= (bb << (_NORTH + _EAST + _EAST))
    if not (bb & file_gh_mask): attacks |= (bb >> (_NORTH + _WEST + _WEST))
    if not (bb & file_a_mask):  attacks |= (bb >> (_NORTH + _NORTH + _EAST))
    if not (bb & file_h_mask):  attacks |= (bb >> (_NORTH + _NORTH + _WEST))
    if not (bb & file_ab_mask): attacks |= (bb << (_NORTH + _WEST + _WEST))
    if not (bb & file_ab_mask): attacks |= (bb >> (_NORTH + _EAST + _EAST))
    return attacks & full_board_mask


cdef unsigned long long _king_attacks(int sq):
    cdef unsigned long long bb = (<unsigned long long>1) << sq
    cdef unsigned long long attacks = 0
    cdef unsigned long long file_h_mask = FILE_H
    cdef unsigned long long file_a_mask = FILE_A
    cdef unsigned long long full_board_mask = FULL_BOARD
    if not (bb & file_h_mask): attacks |= (bb << _EAST) | (bb << (_NORTH + _EAST)) | (bb >> (_NORTH + _WEST))
    if not (bb & file_a_mask): attacks |= (bb >> _EAST) | (bb >> (_NORTH + _EAST)) | (bb << (_NORTH + _WEST))
    attacks |= (bb << _NORTH) | (bb >> _NORTH)
    return attacks & full_board_mask


cdef unsigned long long _pawn_attacks(int sq, bint is_white):
    cdef unsigned long long bb = (<unsigned long long>1) << sq
    cdef unsigned long long attacks = 0
    cdef unsigned long long file_a_mask = FILE_A
    cdef unsigned long long file_h_mask = FILE_H
    cdef unsigned long long full_board_mask = FULL_BOARD
    if is_white:
        if not (bb & file_a_mask): attacks |= (bb << (_NORTH + _WEST))
        if not (bb & file_h_mask): attacks |= (bb << (_NORTH + _EAST))
    else:
        if not (bb & file_h_mask): attacks |= (bb >> (_NORTH + _WEST))
        if not (bb & file_a_mask): attacks |= (bb >> (_NORTH + _EAST))
    return attacks & full_board_mask


def _build_sliding_masks(deltas):
    masks = []
    for square in range(64):
        mask = 0
        rank, file_ = square // 8, square % 8
        for d_rank, d_file in deltas:
            r, f = rank + d_rank, file_ + d_file
            while 0 <= r <= 7 and 0 <= f <= 7:
                mask |= _SQUARE_TO_BB[r * 8 + f]
                r += d_rank
                f += d_file
        masks.append(mask)
    return masks


def _build_sliding_attacks(square, block, deltas):
    attacks = 0
    rank, file_ = square // 8, square % 8
    for d_rank, d_file in deltas:
        r, f = rank + d_rank, file_ + d_file
        while 0 <= r <= 7 and 0 <= f <= 7:
            bit = 1 << (r * 8 + f)
            attacks |= bit
            if bit & block:
                break
            r += d_rank
            f += d_file
    return attacks


def _build_slider_table(deltas):
    """returns (table, masks) as python lists"""
    masks = _build_sliding_masks(deltas)
    table = []
    for square in range(64):
        mask = masks[square]
        bit_indices = [i for i in range(64) if (mask >> i) & 1]
        num_patterns = 1 << len(bit_indices)
        sq_table = {}
        for i in range(num_patterns):
            blocker = 0
            for bit_index, pos in enumerate(bit_indices):
                if (i >> bit_index) & 1:
                    blocker |= _SQUARE_TO_BB[pos]
            sq_table[blocker] = _build_sliding_attacks(square, blocker, deltas)
        table.append(sq_table)
    return table, masks


cdef void _init_all():
    cdef int sq

    for sq in range(64):
        KNIGHT_ATTACKS[sq]      = _knight_attacks(sq)
        KING_ATTACKS[sq]        = _king_attacks(sq)
        WHITE_PAWN_ATTACKS[sq]  = _pawn_attacks(sq, True)
        BLACK_PAWN_ATTACKS[sq]  = _pawn_attacks(sq, False)

    bishop_table, bishop_masks = _build_slider_table([(1, 1), (1, -1), (-1, 1), (-1, -1)])
    rook_table,   rook_masks   = _build_slider_table([(1, 0), (-1, 0), (0, 1), (0, -1)])

    BISHOP_TABLE[:] = bishop_table
    ROOK_TABLE[:]   = rook_table

    for sq in range(64):
        BISHOP_MASKS[sq] = bishop_masks[sq]
        ROOK_MASKS[sq]   = rook_masks[sq]


_init_all()
send_info_string('initialised lookup tables')

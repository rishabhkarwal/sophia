from engine.core.constants import (
    WHITE, BLACK,
    FILE_A, FILE_H, FILE_AB, FILE_GH,
    FULL_BOARD, NORTH, EAST, WEST, SQUARE_TO_BB as _SQUARE_TO_BB
)
from engine.uci.utils import send_info_string
from libc.stdlib cimport malloc, free

cdef enum:
    _SLIDER_MAX_BITS = 14

cdef unsigned long long KNIGHT_ATTACKS[64]
cdef unsigned long long KING_ATTACKS[64]
cdef unsigned long long WHITE_PAWN_ATTACKS[64]
cdef unsigned long long BLACK_PAWN_ATTACKS[64]
cdef unsigned long long BISHOP_MASKS[64]
cdef unsigned long long ROOK_MASKS[64]
cdef unsigned long long SQUARE_TO_BB[64]
cdef unsigned long long* BISHOP_ATTACKS = NULL
cdef unsigned long long* ROOK_ATTACKS = NULL
cdef int BISHOP_OFFSETS[64]
cdef int ROOK_OFFSETS[64]
cdef unsigned char BISHOP_BIT_COUNTS[64]
cdef unsigned char ROOK_BIT_COUNTS[64]
cdef unsigned char BISHOP_BIT_INDICES[64][_SLIDER_MAX_BITS]
cdef unsigned char ROOK_BIT_INDICES[64][_SLIDER_MAX_BITS]

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
    masks = _build_sliding_masks(deltas)
    table = []
    bits = []
    for square in range(64):
        mask = masks[square]
        bit_indices = [i for i in range(64) if (mask >> i) & 1]
        bits.append(bit_indices)
        num_patterns = 1 << len(bit_indices)
        sq_table = [0] * num_patterns
        for i in range(num_patterns):
            blocker = 0
            for bit_index, pos in enumerate(bit_indices):
                if (i >> bit_index) & 1:
                    blocker |= _SQUARE_TO_BB[pos]
            sq_table[i] = _build_sliding_attacks(square, blocker, deltas)
        table.append(sq_table)
    return table, masks, bits


cdef inline unsigned int _slider_index(unsigned long long occupied,
                                       unsigned char* bit_indices,
                                       int bit_count) noexcept:
    cdef unsigned int idx = 0
    cdef int i
    for i in range(bit_count):
        if occupied & ((<unsigned long long>1) << bit_indices[i]):
            idx |= (<unsigned int>1) << i
    return idx


cdef unsigned long long bishop_attacks(int sq, unsigned long long all_pieces) noexcept:
    return BISHOP_ATTACKS[BISHOP_OFFSETS[sq] + _slider_index(
        all_pieces, &BISHOP_BIT_INDICES[sq][0], BISHOP_BIT_COUNTS[sq]
    )]


cdef unsigned long long rook_attacks(int sq, unsigned long long all_pieces) noexcept:
    return ROOK_ATTACKS[ROOK_OFFSETS[sq] + _slider_index(
        all_pieces, &ROOK_BIT_INDICES[sq][0], ROOK_BIT_COUNTS[sq]
    )]


cdef void _init_all():
    global BISHOP_ATTACKS, ROOK_ATTACKS

    cdef int sq, i, bit_count
    cdef int bishop_total = 0
    cdef int rook_total = 0
    cdef object bishop_table, bishop_masks, bishop_bits
    cdef object rook_table, rook_masks, rook_bits
    cdef object sq_table

    for sq in range(64):
        SQUARE_TO_BB[sq]        = (<unsigned long long>1) << sq
        KNIGHT_ATTACKS[sq]      = _knight_attacks(sq)
        KING_ATTACKS[sq]        = _king_attacks(sq)
        WHITE_PAWN_ATTACKS[sq]  = _pawn_attacks(sq, True)
        BLACK_PAWN_ATTACKS[sq]  = _pawn_attacks(sq, False)

    bishop_table, bishop_masks, bishop_bits = _build_slider_table([(1, 1), (1, -1), (-1, 1), (-1, -1)])
    rook_table,   rook_masks,   rook_bits   = _build_slider_table([(1, 0), (-1, 0), (0, 1), (0, -1)])

    for sq in range(64):
        BISHOP_OFFSETS[sq] = bishop_total
        ROOK_OFFSETS[sq]   = rook_total
        bishop_total      += len(bishop_table[sq])
        rook_total        += len(rook_table[sq])

    if BISHOP_ATTACKS != NULL:
        free(BISHOP_ATTACKS)
    if ROOK_ATTACKS != NULL:
        free(ROOK_ATTACKS)

    BISHOP_ATTACKS = <unsigned long long*>malloc(bishop_total * sizeof(unsigned long long))
    ROOK_ATTACKS   = <unsigned long long*>malloc(rook_total * sizeof(unsigned long long))
    if BISHOP_ATTACKS == NULL or ROOK_ATTACKS == NULL:
        if BISHOP_ATTACKS != NULL:
            free(BISHOP_ATTACKS)
            BISHOP_ATTACKS = NULL
        if ROOK_ATTACKS != NULL:
            free(ROOK_ATTACKS)
            ROOK_ATTACKS = NULL
        raise MemoryError()

    for sq in range(64):
        BISHOP_MASKS[sq] = bishop_masks[sq]
        ROOK_MASKS[sq]   = rook_masks[sq]

        bit_count = len(bishop_bits[sq])
        BISHOP_BIT_COUNTS[sq] = bit_count
        for i in range(bit_count):
            BISHOP_BIT_INDICES[sq][i] = bishop_bits[sq][i]
        for i in range(bit_count, _SLIDER_MAX_BITS):
            BISHOP_BIT_INDICES[sq][i] = 0

        bit_count = len(rook_bits[sq])
        ROOK_BIT_COUNTS[sq] = bit_count
        for i in range(bit_count):
            ROOK_BIT_INDICES[sq][i] = rook_bits[sq][i]
        for i in range(bit_count, _SLIDER_MAX_BITS):
            ROOK_BIT_INDICES[sq][i] = 0

        sq_table = bishop_table[sq]
        for i in range(len(sq_table)):
            BISHOP_ATTACKS[BISHOP_OFFSETS[sq] + i] = sq_table[i]

        sq_table = rook_table[sq]
        for i in range(len(sq_table)):
            ROOK_ATTACKS[ROOK_OFFSETS[sq] + i] = sq_table[i]


_init_all()
send_info_string('initialised lookup tables')

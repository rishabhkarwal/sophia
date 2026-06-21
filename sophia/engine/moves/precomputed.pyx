from engine.core.constants import (
    WHITE, BLACK,
    FILE_A, FILE_H, FILE_AB, FILE_GH,
    FULL_BOARD, NORTH, EAST, WEST, SQUARE_TO_BB as _SQUARE_TO_BB
)
from engine.uci.utils import send_info_string
from libc.stdlib cimport malloc, free

cdef unsigned long long KNIGHT_ATTACKS[64]
cdef unsigned long long KING_ATTACKS[64]
cdef unsigned long long WHITE_PAWN_ATTACKS[64]
cdef unsigned long long BLACK_PAWN_ATTACKS[64]
cdef unsigned long long BISHOP_MASKS[64]
cdef unsigned long long ROOK_MASKS[64]
cdef unsigned long long BISHOP_MAGICS[64]
cdef unsigned long long ROOK_MAGICS[64]
cdef unsigned long long SQUARE_TO_BB[64]
cdef unsigned long long* BISHOP_ATTACKS = NULL
cdef unsigned long long* ROOK_ATTACKS = NULL
cdef int BISHOP_OFFSETS[64]
cdef int ROOK_OFFSETS[64]
cdef unsigned char BISHOP_SHIFTS[64]
cdef unsigned char ROOK_SHIFTS[64]

BISHOP_TABLE = []
ROOK_TABLE = []

cdef int _NORTH = NORTH
cdef int _EAST  = EAST
cdef int _WEST  = WEST

_MASK_64 = 0xFFFFFFFFFFFFFFFF

BISHOP_MAGIC_VALUES = [
    0x1410020244040010, 0x0090100640862800, 0x8848848106000000, 0x10020A0604910000,
    0xC00410448C040000, 0x6400821040880000, 0x000C410860902002, 0x4029041084010800,
    0x8504103421084202, 0x2100082868204040, 0x00180810C5020008, 0x9100080A10240008,
    0x880808584028E000, 0x0088450452403405, 0x2800610101202000, 0x0000042402080420,
    0x4040811011420090, 0x0420040802340065, 0x0210048200260023, 0x0048000892004009,
    0x0002022422010800, 0x9005000020A01001, 0x0004720104022000, 0x2004204242280401,
    0x0283A00140041420, 0x4204100004011800, 0x0080480110008010, 0x0501004084040002,
    0x0000840022020200, 0x1808042106048400, 0x0A41140082020100, 0x0206008844CA4800,
    0x2901080800433000, 0x0911016000108447, 0x2004908880100400, 0x8020040401080210,
    0x02020A0400120082, 0x5A50011044020040, 0x8108408100108811, 0x8001013320D10400,
    0x0048021124005000, 0x0080411821000820, 0x0401040601009204, 0x00000C6124080800,
    0xA000403009030080, 0xD040100400200040, 0x4010040800800060, 0x51A9020481024208,
    0x4001080A02E02008, 0x0421190082200800, 0x8000090400920000, 0x2150168104090080,
    0x0000400550440803, 0x50C0400811011142, 0x0A08082128060E08, 0x0088080080A60110,
    0x0884802101304004, 0x0208010501092020, 0x4040028452080410, 0x2400400003048800,
    0x0100800090820201, 0x4800006034108282, 0x2200208810010048, 0x1002C20808008080,
]

BISHOP_BITS_VALUES = [
    6, 5, 5, 5, 5, 5, 5, 6, 5, 5, 5, 5, 5, 5, 5, 5,
    5, 5, 7, 7, 7, 7, 5, 5, 5, 5, 7, 9, 9, 7, 5, 5,
    5, 5, 7, 9, 9, 7, 5, 5, 5, 5, 7, 7, 7, 7, 5, 5,
    5, 5, 5, 5, 5, 5, 5, 5, 6, 5, 5, 5, 5, 5, 5, 6,
]

ROOK_MAGIC_VALUES = [
    0x0080005481214000, 0x8100102108804002, 0x088008600180D001, 0x0200082040100600,
    0x1200100804020021, 0x0200020004489B10, 0x1480408002003100, 0x0200010042003084,
    0x00468008400080E0, 0x0881002040010080, 0x4803002000410114, 0x1001002009001000,
    0x102A000A00041060, 0x2004800400800200, 0x0022000200040801, 0x0812001200411084,
    0x0080004020004000, 0x005000C040012000, 0x080484801000A000, 0x0508008008100080,
    0x4008808004000800, 0x0004004040020100, 0x0020440010410802, 0x0480260000812844,
    0x0000400080008020, 0x1040002100410088, 0x0020080040401000, 0x4020100080800800,
    0x2802010A00041020, 0x00AC000480020080, 0x2000080400029041, 0x08402C4200040481,
    0x4012401620800084, 0x8010002008400040, 0x002000208080100C, 0x0000800800801000,
    0x4022810010022040, 0x0000800400800200, 0x0A01480144004250, 0x020400488A000104,
    0xA2C2008100420020, 0x0080A01000C0C000, 0x4050002804002000, 0x006020100101000C,
    0x0104080004008080, 0x0014000201004040, 0x4010330610440008, 0x1100004100820004,
    0x4000400080002880, 0xB000200080400080, 0x0022001088244200, 0x4000500180080180,
    0x08A0800400080080, 0x4340800200040080, 0x0090110802508400, 0x4029002200408100,
    0x0080002440801101, 0x0001004880201202, 0x2080814021100A02, 0x00B41000A0090005,
    0x2433000800100205, 0x2102001004010802, 0x04802810070200C4, 0x00000100CC008026,
]

ROOK_BITS_VALUES = [
    12, 11, 11, 11, 11, 11, 11, 12, 11, 10, 10, 10, 10, 10, 10, 11,
    11, 10, 10, 10, 10, 10, 10, 11, 11, 10, 10, 10, 10, 10, 10, 11,
    11, 10, 10, 10, 10, 10, 10, 11, 11, 10, 10, 10, 10, 10, 10, 11,
    11, 10, 10, 10, 10, 10, 10, 11, 12, 11, 11, 11, 11, 11, 11, 12,
]


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
                next_r, next_f = r + d_rank, f + d_file
                if not (0 <= next_r <= 7 and 0 <= next_f <= 7):
                    break
                mask |= _SQUARE_TO_BB[r * 8 + f]
                r, f = next_r, next_f
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


def _build_slider_table(deltas, magic_values, bit_values):
    masks = _build_sliding_masks(deltas)
    table = []
    for square in range(64):
        mask = masks[square]
        bit_indices = [i for i in range(64) if (mask >> i) & 1]
        if bit_values[square] != len(bit_indices):
            raise RuntimeError(f"magic bit count mismatch on square {square}")

        num_patterns = 1 << len(bit_indices)
        sq_table = [0] * num_patterns
        used = [False] * num_patterns
        shift = 64 - bit_values[square]
        for i in range(num_patterns):
            blocker = 0
            for bit_index, pos in enumerate(bit_indices):
                if (i >> bit_index) & 1:
                    blocker |= _SQUARE_TO_BB[pos]
            idx = (((blocker & mask) * magic_values[square]) & _MASK_64) >> shift
            attacks = _build_sliding_attacks(square, blocker, deltas)
            if used[idx] and sq_table[idx] != attacks:
                raise RuntimeError(f"magic collision on square {square}")
            used[idx] = True
            sq_table[idx] = attacks
        table.append(sq_table)
    return table, masks


cdef inline unsigned int _magic_index(unsigned long long occupied,
                                      unsigned long long mask,
                                      unsigned long long magic,
                                      unsigned char shift) noexcept:
    return <unsigned int>(((occupied & mask) * magic) >> shift)


cdef unsigned long long bishop_attacks(int sq, unsigned long long all_pieces) noexcept:
    return BISHOP_ATTACKS[BISHOP_OFFSETS[sq] + _magic_index(all_pieces, BISHOP_MASKS[sq], BISHOP_MAGICS[sq], BISHOP_SHIFTS[sq])]


cdef unsigned long long rook_attacks(int sq, unsigned long long all_pieces) noexcept:
    return ROOK_ATTACKS[ROOK_OFFSETS[sq] + _magic_index(all_pieces, ROOK_MASKS[sq], ROOK_MAGICS[sq], ROOK_SHIFTS[sq])]


cdef void _init_all():
    global BISHOP_ATTACKS, ROOK_ATTACKS

    cdef int sq, i
    cdef int bishop_total = 0
    cdef int rook_total = 0
    cdef object bishop_table, bishop_masks
    cdef object rook_table, rook_masks
    cdef object sq_table

    for sq in range(64):
        SQUARE_TO_BB[sq]        = (<unsigned long long>1) << sq
        KNIGHT_ATTACKS[sq]      = _knight_attacks(sq)
        KING_ATTACKS[sq]        = _king_attacks(sq)
        WHITE_PAWN_ATTACKS[sq]  = _pawn_attacks(sq, True)
        BLACK_PAWN_ATTACKS[sq]  = _pawn_attacks(sq, False)
        BISHOP_MAGICS[sq]       = <unsigned long long>BISHOP_MAGIC_VALUES[sq]
        ROOK_MAGICS[sq]         = <unsigned long long>ROOK_MAGIC_VALUES[sq]
        BISHOP_SHIFTS[sq]       = <unsigned char>(64 - BISHOP_BITS_VALUES[sq])
        ROOK_SHIFTS[sq]         = <unsigned char>(64 - ROOK_BITS_VALUES[sq])

    bishop_table, bishop_masks = _build_slider_table([(1, 1), (1, -1), (-1, 1), (-1, -1)], BISHOP_MAGIC_VALUES, BISHOP_BITS_VALUES)
    rook_table,   rook_masks   = _build_slider_table([(1, 0), (-1, 0), (0, 1), (0, -1)], ROOK_MAGIC_VALUES, ROOK_BITS_VALUES)

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

        sq_table = bishop_table[sq]
        for i in range(len(sq_table)):
            BISHOP_ATTACKS[BISHOP_OFFSETS[sq] + i] = sq_table[i]

        sq_table = rook_table[sq]
        for i in range(len(sq_table)):
            ROOK_ATTACKS[ROOK_OFFSETS[sq] + i] = sq_table[i]


_init_all()
send_info_string('initialised lookup tables')

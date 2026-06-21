# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True

from engine.core.utils import bit_to_algebraic

# flag bit layout: [ Promotion | Capture | Special 1 | Special 0 ]
ZERO        = 0b0000

# flag masks
FLAG_MASK   = 0b1111
PROMOTION   = 0b1000
CAPTURE     = 0b0100

# flag modifiers
SPECIAL_1   = 0b0010
SPECIAL_0   = 0b0001

# move types
QUIET       = ZERO
DOUBLE_PUSH = SPECIAL_0
CASTLE_KS   = SPECIAL_1
CASTLE_QS   = SPECIAL_1 | SPECIAL_0

# capture types
EN_PASSANT  = CAPTURE | SPECIAL_0

# piece identifiers (for promotions)
KNIGHT = ZERO
BISHOP = SPECIAL_0
ROOK   = SPECIAL_1
QUEEN  = SPECIAL_1 | SPECIAL_0

# promotions
PROMOTION_N = PROMOTION | KNIGHT
PROMOTION_B = PROMOTION | BISHOP
PROMOTION_R = PROMOTION | ROOK
PROMOTION_Q = PROMOTION | QUEEN

# promotion captures
PROMO_CAP_N = PROMOTION_N | CAPTURE
PROMO_CAP_B = PROMOTION_B | CAPTURE
PROMO_CAP_R = PROMOTION_R | CAPTURE
PROMO_CAP_Q = PROMOTION_Q | CAPTURE

# field shifts
SHIFT_TARGET = 6
SHIFT_FLAG   = 12

# precomputed flag masks for inline checks
CAPTURE_FLAG   = CAPTURE << SHIFT_FLAG
PROMO_FLAG     = PROMOTION << SHIFT_FLAG
EP_FLAG        = EN_PASSANT << SHIFT_FLAG
CASTLE_KS_FLAG = CASTLE_KS << SHIFT_FLAG
CASTLE_QS_FLAG = CASTLE_QS << SHIFT_FLAG

# square names for UCI
SQUARE_NAMES = [bit_to_algebraic(square) for square in range(64)]

# mapping flag bits to piece types
PROMO_TYPE_LOOKUP = (KNIGHT, BISHOP, ROOK, QUEEN)
PROMO_CHAR_LOOKUP = ('n', 'b', 'r', 'q')


# python-callable wrapper so code that imports as a python symbol
def pack(int start, int target, int flag=0):
    return _pack(start, target, flag)


cpdef str move_to_uci(unsigned int move):
    cdef int start, target, idx
    start  = move_source(move)
    target = move_target(move)
    uci_str = SQUARE_NAMES[start] + SQUARE_NAMES[target]

    if is_promotion(move):
        idx = move_promotion_index(move)
        uci_str += PROMO_CHAR_LOOKUP[idx]

    return uci_str

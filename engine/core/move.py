from engine.core.utils import bit_to_algebraic
from engine.core.constants import MASK_SOURCE, MASK_TARGET, MASK_FLAG

# flag bit layout: [ Promotion | Capture | Special 1 | Special 0 ]
ZERO        = 0b0000

# flag masks
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
KNIGHT      = ZERO
BISHOP      = SPECIAL_0
ROOK        = SPECIAL_1
QUEEN       = SPECIAL_1 | SPECIAL_0

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

# precomputed flag masks
CAPTURE_FLAG = CAPTURE << SHIFT_FLAG
PROMO_FLAG   = PROMOTION << SHIFT_FLAG
EP_FLAG      = EN_PASSANT << SHIFT_FLAG

# square names for UCI
SQUARE_NAMES = [bit_to_algebraic(square) for square in range(64)]

from engine.core.constants import BN, BB, BR, BQ
PROMO_LOOKUP = (BN, BB, BR, BQ)

def _pack(start: int, target: int, flag: int = QUIET) -> int:
    """Internal helper to create a 16-bit integer move"""
    return start | (target << SHIFT_TARGET) | (flag << SHIFT_FLAG)

def get_start(move: int) -> int:
    """Extract source square from move"""
    return move & MASK_SOURCE

def get_target(move: int) -> int:
    """Extract target square from move"""
    return (move >> SHIFT_TARGET) & MASK_SOURCE

def get_flag(move: int) -> int:
    """Extract flag from move"""
    return (move >> SHIFT_FLAG) & 0b1111

def is_capture(move: int) -> bool:
    """Returns True if the move is a capture"""
    return bool(move & CAPTURE_FLAG)

def is_promotion(move: int) -> bool:
    """Returns True if the move is a promotion"""
    return bool(move & PROMO_FLAG)

def is_en_passant(move: int) -> bool:
    """Returns True if the move is en passant"""
    return (move & MASK_FLAG) == EP_FLAG

def is_castle(move: int) -> bool:
    """Returns True if the move is castling"""
    flag = get_flag(move)
    return flag == CASTLE_KS or flag == CASTLE_QS

def get_promo_piece(move: int) -> str:
    """returns promotion piece character using bit manipulation
    
    Extracts the piece type from the flag's lower 2 bits:
    00 (0) -> knight, 01 (1) -> bBishop, 10 (2) -> eook, 11 (3) -> queen
    """
    idx = (move >> SHIFT_FLAG) & (SPECIAL_1 | SPECIAL_0)
    return PROMO_LOOKUP[idx]

def move_to_uci(move: int) -> str:
    """Converts integer move to UCI string"""
    start = get_start(move)
    target = get_target(move)
    uci_str = SQUARE_NAMES[start] + SQUARE_NAMES[target]
    
    if is_promotion(move): uci_str += get_promo_piece(move)
        
    return uci_str
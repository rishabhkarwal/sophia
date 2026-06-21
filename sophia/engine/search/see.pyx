from engine.core.constants import (
    WHITE, BLACK, PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
    NULL as _NULL,
    WP, WN, WB, WR, WQ, WK,
    BP, BN, BB, BR, BQ, BK,
)
from engine.core.parameters import PIECE_VALUES
from engine.core.move import (
    EN_PASSANT,
    PROMOTION, SPECIAL_1, SPECIAL_0
)
from engine.core.move cimport move_source, move_target, move_flag
from engine.core.bits cimport lsb
from engine.board.state cimport State
from engine.moves.precomputed cimport KNIGHT_ATTACKS, KING_ATTACKS, WHITE_PAWN_ATTACKS, BLACK_PAWN_ATTACKS, bishop_attacks, rook_attacks, SQUARE_TO_BB

cdef int _WHITE = WHITE
cdef int _BLACK = BLACK
cdef int _NULL_SQ = _NULL
cdef int _PAWN = PAWN
cdef int _KNIGHT = KNIGHT
cdef int _BISHOP = BISHOP
cdef int _ROOK = ROOK
cdef int _QUEEN = QUEEN
cdef int _KING = KING
cdef int _WP = WP, _WN = WN, _WB = WB, _WR = WR, _WQ = WQ, _WK = WK
cdef int _BP = BP, _BN = BN, _BB = BB, _BR = BR, _BQ = BQ, _BK = BK
cdef int _EN_PASSANT = EN_PASSANT
cdef int _PROMOTION = PROMOTION
cdef int _SP1 = SPECIAL_1
cdef int _SP0 = SPECIAL_0

cdef int[16] _PIECE_VALUES
_PIECE_VALUES[_PAWN]   = PIECE_VALUES[PAWN]
_PIECE_VALUES[_KNIGHT] = PIECE_VALUES[KNIGHT]
_PIECE_VALUES[_BISHOP] = PIECE_VALUES[BISHOP]
_PIECE_VALUES[_ROOK]   = PIECE_VALUES[ROOK]
_PIECE_VALUES[_QUEEN]  = PIECE_VALUES[QUEEN]
_PIECE_VALUES[_KING]   = PIECE_VALUES[KING]

cdef inline int _lsb_sq(unsigned long long bb) noexcept:
    return lsb(bb)


cdef inline int _promo_piece_type(int flag) noexcept:
    cdef int idx = flag & (_SP1 | _SP0)
    if idx == 0: return _KNIGHT
    if idx == _SP0: return _BISHOP
    if idx == _SP1: return _ROOK
    return _QUEEN


cdef int _least_attacker(State state, int sq, int colour,
                         unsigned long long occupied,
                         int* piece_value) noexcept:
    cdef unsigned long long attackers
    cdef unsigned long long diag_attacks
    cdef unsigned long long orth_attacks

    if colour == _WHITE:
        attackers = BLACK_PAWN_ATTACKS[sq] & state.bitboards[_WP] & occupied
        if attackers:
            piece_value[0] = _PIECE_VALUES[_PAWN]
            return _lsb_sq(attackers)

        attackers = KNIGHT_ATTACKS[sq] & state.bitboards[_WN] & occupied
        if attackers:
            piece_value[0] = _PIECE_VALUES[_KNIGHT]
            return _lsb_sq(attackers)

        diag_attacks = bishop_attacks(sq, occupied)
        attackers = diag_attacks & state.bitboards[_WB] & occupied
        if attackers:
            piece_value[0] = _PIECE_VALUES[_BISHOP]
            return _lsb_sq(attackers)

        orth_attacks = rook_attacks(sq, occupied)
        attackers = orth_attacks & state.bitboards[_WR] & occupied
        if attackers:
            piece_value[0] = _PIECE_VALUES[_ROOK]
            return _lsb_sq(attackers)

        attackers = (diag_attacks | orth_attacks) & state.bitboards[_WQ] & occupied
        if attackers:
            piece_value[0] = _PIECE_VALUES[_QUEEN]
            return _lsb_sq(attackers)

        attackers = KING_ATTACKS[sq] & state.bitboards[_WK] & occupied
        if attackers:
            piece_value[0] = _PIECE_VALUES[_KING]
            return _lsb_sq(attackers)
    else:
        attackers = WHITE_PAWN_ATTACKS[sq] & state.bitboards[_BP] & occupied
        if attackers:
            piece_value[0] = _PIECE_VALUES[_PAWN]
            return _lsb_sq(attackers)

        attackers = KNIGHT_ATTACKS[sq] & state.bitboards[_BN] & occupied
        if attackers:
            piece_value[0] = _PIECE_VALUES[_KNIGHT]
            return _lsb_sq(attackers)

        diag_attacks = bishop_attacks(sq, occupied)
        attackers = diag_attacks & state.bitboards[_BB] & occupied
        if attackers:
            piece_value[0] = _PIECE_VALUES[_BISHOP]
            return _lsb_sq(attackers)

        orth_attacks = rook_attacks(sq, occupied)
        attackers = orth_attacks & state.bitboards[_BR] & occupied
        if attackers:
            piece_value[0] = _PIECE_VALUES[_ROOK]
            return _lsb_sq(attackers)

        attackers = (diag_attacks | orth_attacks) & state.bitboards[_BQ] & occupied
        if attackers:
            piece_value[0] = _PIECE_VALUES[_QUEEN]
            return _lsb_sq(attackers)

        attackers = KING_ATTACKS[sq] & state.bitboards[_BK] & occupied
        if attackers:
            piece_value[0] = _PIECE_VALUES[_KING]
            return _lsb_sq(attackers)

    piece_value[0] = 0
    return _NULL_SQ


cdef int see_value(State state, unsigned int move) noexcept:
    cdef int gain[32]
    cdef int start_sq, target_sq, flag, moving_piece, moving_type, moving_colour
    cdef int victim, victim_type, victim_value, current_value
    cdef int promoted_type, capture_sq, side, current_sq, d
    cdef unsigned long long occupied

    start_sq  = move_source(move)
    target_sq = move_target(move)
    flag      = move_flag(move)

    moving_piece = state.board[start_sq]
    if moving_piece == _NULL_SQ:
        return 0

    moving_type   = moving_piece & ~_WHITE
    moving_colour = moving_piece & _WHITE
    victim_value  = 0

    occupied = state.bitboards[_WHITE] | state.bitboards[_BLACK]

    if flag == _EN_PASSANT:
        victim_value = _PIECE_VALUES[_PAWN]
        capture_sq = target_sq - 8 if moving_colour == _WHITE else target_sq + 8
        occupied &= ~SQUARE_TO_BB[capture_sq]
    else:
        victim = state.board[target_sq]
        if victim != _NULL_SQ:
            victim_type = victim & ~_WHITE
            victim_value = _PIECE_VALUES[victim_type]

    current_value = _PIECE_VALUES[moving_type]
    gain[0] = victim_value

    if flag & _PROMOTION:
        promoted_type = _promo_piece_type(flag)
        current_value = _PIECE_VALUES[promoted_type]
        gain[0] += current_value - _PIECE_VALUES[_PAWN]

    side = moving_colour
    current_sq = start_sq
    d = 0

    while d < 31:
        d += 1
        gain[d] = current_value - gain[d - 1]
        occupied &= ~SQUARE_TO_BB[current_sq]
        side = side ^ _WHITE
        current_sq = _least_attacker(state, target_sq, side, occupied, &current_value)
        if current_sq == _NULL_SQ:
            break

    while d > 1:
        d -= 1
        if -gain[d] < gain[d - 1]:
            gain[d - 1] = -gain[d]

    return gain[0]


cdef bint see_ge(State state, unsigned int move, int threshold) noexcept:
    return see_value(state, move) >= threshold


def see_full(State state, unsigned int move):
    return see_value(state, move)


def see_fast(State state, unsigned int move, int threshold=0):
    return see_ge(state, move, threshold)

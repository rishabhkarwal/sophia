# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True

from engine.core.constants import (
    WHITE, BLACK,
    WP, WN, WB, WR, WQ, WK,
    BP, BN, BB, BR, BQ, BK,
    WHITE_PIECES, BLACK_PIECES
)
from engine.moves.precomputed cimport KNIGHT_ATTACKS, KING_ATTACKS, WHITE_PAWN_ATTACKS, BLACK_PAWN_ATTACKS, bishop_attacks, rook_attacks, SQUARE_TO_BB
from engine.core.move cimport move_source, move_target
from engine.core.bits cimport lsb

from engine.board.state cimport State
from engine.board.move_exec cimport make_move, unmake_move

cdef int _WP = WP, _WN = WN, _WB = WB, _WR = WR, _WQ = WQ, _WK = WK
cdef int _BP = BP, _BN = BN, _BB = BB, _BR = BR, _BQ = BQ, _BK = BK
cdef int _WHITE = WHITE, _BLACK = BLACK


cdef bint is_square_attacked(State state, int sq, bint by_white) noexcept:
    cdef unsigned long long all_pieces, queens, bb
    cdef unsigned long long[16] *bbs = &state.bitboards

    if by_white:
        if BLACK_PAWN_ATTACKS[sq] & bbs[0][_WP]: return True
        if KNIGHT_ATTACKS[sq]     & bbs[0][_WN]: return True
        if KING_ATTACKS[sq]       & bbs[0][_WK]: return True

        all_pieces = bbs[0][_WHITE] | bbs[0][_BLACK]
        queens     = bbs[0][_WQ]

        if bishop_attacks(sq, all_pieces) & (bbs[0][_WB] | queens): return True
        if rook_attacks(sq, all_pieces)   & (bbs[0][_WR] | queens): return True
    else:
        if WHITE_PAWN_ATTACKS[sq] & bbs[0][_BP]: return True
        if KNIGHT_ATTACKS[sq]     & bbs[0][_BN]: return True
        if KING_ATTACKS[sq]       & bbs[0][_BK]: return True

        all_pieces = bbs[0][_WHITE] | bbs[0][_BLACK]
        queens     = bbs[0][_BQ]

        if bishop_attacks(sq, all_pieces) & (bbs[0][_BB] | queens): return True
        if rook_attacks(sq, all_pieces)   & (bbs[0][_BR] | queens): return True

    return False


cdef unsigned long long attackers_to_square(State state, int sq, bint colour) noexcept:
    cdef unsigned long long attackers = 0
    cdef unsigned long long all_pieces = state.bitboards[_WHITE] | state.bitboards[_BLACK]
    cdef unsigned long long pawn_attacks, pa, na, ka
    cdef int P, N, B, R, Q, K

    if colour:
        P = _WP; N = _WN; B = _WB; R = _WR; Q = _WQ; K = _WK
        pawn_attacks = BLACK_PAWN_ATTACKS[sq]
    else:
        P = _BP; N = _BN; B = _BB; R = _BR; Q = _BQ; K = _BK
        pawn_attacks = WHITE_PAWN_ATTACKS[sq]

    pa = pawn_attacks & state.bitboards[P]
    if pa: attackers |= pa

    na = KNIGHT_ATTACKS[sq] & state.bitboards[N]
    if na: attackers |= na

    ka = KING_ATTACKS[sq] & state.bitboards[K]
    if ka: attackers |= ka

    attackers |= bishop_attacks(sq, all_pieces) & (state.bitboards[B] | state.bitboards[Q])
    attackers |= rook_attacks(sq, all_pieces)   & (state.bitboards[R] | state.bitboards[Q])
    return attackers


cpdef bint is_in_check(State state, bint colour) noexcept:
    cdef int king_idx, king_sq
    cdef unsigned long long king_bb

    king_idx = _WK if colour else _BK
    king_bb  = state.bitboards[king_idx]
    if not king_bb:
        return False

    # lsb via bit-length (king bitboard always has exactly one bit)
    king_sq = lsb(king_bb)

    return is_square_attacked(state, king_sq, not colour)


cpdef bint is_legal(State state, unsigned int move):
    cdef int start_sq, target_sq
    cdef int king_idx
    cdef unsigned long long start_mask, restore_mask
    cdef bint attacked, in_check

    start_sq  = move_source(move)
    king_idx  = _WK if state.is_white else _BK

    if state.bitboards[king_idx] & SQUARE_TO_BB[start_sq]:
        # king move — remove king from its source, test if destination is safe
        target_sq  = move_target(move)
        start_mask = SQUARE_TO_BB[start_sq]

        state.bitboards[king_idx]            &= ~start_mask
        state.bitboards[<int>state.is_white] &= ~start_mask

        attacked = is_square_attacked(state, target_sq, not state.is_white)

        # restore immediately
        state.bitboards[king_idx]            |= start_mask
        state.bitboards[<int>state.is_white] |= start_mask

        return not attacked

    # non-king move — full make/unmake + in-check test
    make_move(state, move)
    in_check = is_in_check(state, not state.is_white)
    unmake_move(state, move)
    return not in_check


def get_attackers(State state, int sq, bint colour):
    """return bitboard of all pieces of 'colour' that attack 'sq'"""
    return attackers_to_square(state, sq, colour)

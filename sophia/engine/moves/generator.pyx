# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True

from engine.core.constants import (
    NULL as _NULL, PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
    CASTLE_WK, CASTLE_WQ, CASTLE_BK, CASTLE_BQ,
    A8, H1, E1, F1, G1, C1, D1, B1, E8, F8, G8, C8, D8, B8,
    RANK_3, RANK_6,
    WHITE_PIECES, BLACK_PIECES,
    MASK_SOURCE,
    WP, BP, WN, BN, WB, BB, WR, BR, WQ, BQ, WK, BK,
    WHITE, BLACK, NORTH, SOUTH,
    SQUARE_TO_BB
)
from engine.core.move import SHIFT_TARGET
from engine.core.move cimport _pack
from engine.core.move import (
    QUIET, CAPTURE, EN_PASSANT,
    CASTLE_KS, CASTLE_QS,
    PROMOTION_N, PROMOTION_B, PROMOTION_R, PROMOTION_Q,
    PROMO_CAP_N, PROMO_CAP_B, PROMO_CAP_R, PROMO_CAP_Q,
    DOUBLE_PUSH,
    CAPTURE_FLAG, PROMO_FLAG, EP_FLAG,
    CASTLE_KS_FLAG, CASTLE_QS_FLAG,
)
from engine.board.state cimport State
from engine.moves.legality cimport is_legal, is_square_attacked

from engine.moves.precomputed cimport KNIGHT_ATTACKS, KING_ATTACKS, WHITE_PAWN_ATTACKS, BLACK_PAWN_ATTACKS, bishop_attacks, rook_attacks

cdef int _WP = WP, _WN = WN, _WB = WB, _WR = WR, _WQ = WQ, _WK = WK
cdef int _BP = BP, _BN = BN, _BB = BB, _BR = BR, _BQ = BQ, _BK = BK
cdef int _WHITE = WHITE, _BLACK = BLACK
cdef int _NULL_SQ = _NULL

# promotion/rank thresholds
cdef int _A8 = A8, _H1 = H1
cdef unsigned long long _RANK_3 = RANK_3, _RANK_6 = RANK_6
cdef int _NORTH = NORTH, _SOUTH = SOUTH

cdef int _QUIET       = QUIET
cdef int _CAPTURE     = CAPTURE
cdef int _EN_PASSANT  = EN_PASSANT
cdef int _DOUBLE_PUSH = DOUBLE_PUSH
cdef int _CASTLE_KS   = CASTLE_KS
cdef int _CASTLE_QS   = CASTLE_QS
cdef int _PROM_Q = PROMOTION_Q, _PROM_R = PROMOTION_R
cdef int _PROM_B = PROMOTION_B, _PROM_N = PROMOTION_N
cdef int _PCAP_Q = PROMO_CAP_Q, _PCAP_R = PROMO_CAP_R
cdef int _PCAP_B = PROMO_CAP_B, _PCAP_N = PROMO_CAP_N

cdef int _CWK = CASTLE_WK, _CWQ = CASTLE_WQ
cdef int _CBK = CASTLE_BK, _CBQ = CASTLE_BQ

cdef int _E1 = E1, _F1 = F1, _G1 = G1, _C1 = C1, _D1 = D1, _B1 = B1
cdef int _E8 = E8, _F8 = F8, _G8 = G8, _C8 = C8, _D8 = D8, _B8 = B8


cdef inline void _add_promotions(list moves, int from_sq, int to_sq, bint is_capture) noexcept:
    if is_capture:
        moves.append(_pack(from_sq, to_sq, _PCAP_Q))
        moves.append(_pack(from_sq, to_sq, _PCAP_R))
        moves.append(_pack(from_sq, to_sq, _PCAP_B))
        moves.append(_pack(from_sq, to_sq, _PCAP_N))
    else:
        moves.append(_pack(from_sq, to_sq, _PROM_Q))
        moves.append(_pack(from_sq, to_sq, _PROM_R))
        moves.append(_pack(from_sq, to_sq, _PROM_B))
        moves.append(_pack(from_sq, to_sq, _PROM_N))


cdef void _gen_pawn_moves(State state, list moves, int pawn_key,
                          bint is_white, unsigned long long all_pieces,
                          unsigned long long enemy,
                          unsigned long long* attack_table,
                          bint captures_only) noexcept:
    cdef unsigned long long pawns, single_push, double_push, bb, lsb_bb, attacks, t_lsb
    cdef int to_sq, from_sq, direction
    cdef bint is_promo

    pawns = state.bitboards[pawn_key]
    if not pawns:
        return

    if is_white:
        direction      = _NORTH
        single_push    = (pawns << 8) & ~all_pieces
        double_push    = ((single_push & _RANK_3) << 8) & ~all_pieces
    else:
        direction      = _SOUTH
        single_push    = (pawns >> 8) & ~all_pieces
        double_push    = ((single_push & _RANK_6) >> 8) & ~all_pieces

    if not captures_only:
        # single pushes
        bb = single_push
        while bb:
            lsb_bb = bb & -bb
            to_sq  = lsb_bb.bit_length() - 1
            bb    &= bb - 1
            from_sq = to_sq - direction

            is_promo = (is_white and to_sq >= _A8) or (not is_white and to_sq <= _H1)

            if is_promo:
                _add_promotions(moves, from_sq, to_sq, False)
            else:
                moves.append(_pack(from_sq, to_sq, _QUIET))

        # double pushes
        bb = double_push
        while bb:
            lsb_bb  = bb & -bb
            to_sq   = lsb_bb.bit_length() - 1
            bb     &= bb - 1
            from_sq = to_sq - (2 * direction)
            moves.append(_pack(from_sq, to_sq, _DOUBLE_PUSH))

    # captures
    bb = pawns
    while bb:
        lsb_bb  = bb & -bb
        from_sq = lsb_bb.bit_length() - 1
        bb     &= bb - 1

        attacks = attack_table[from_sq] & enemy
        while attacks:
            t_lsb   = attacks & -attacks
            to_sq   = t_lsb.bit_length() - 1
            attacks &= attacks - 1

            is_promo = (is_white and to_sq >= _A8) or (not is_white and to_sq <= _H1)
            if is_promo:
                _add_promotions(moves, from_sq, to_sq, True)
            else:
                moves.append(_pack(from_sq, to_sq, _CAPTURE))

        # en-passant
        if state.en_passant_square != _NULL_SQ:
            if attack_table[from_sq] & SQUARE_TO_BB[state.en_passant_square]:
                moves.append(_pack(from_sq, state.en_passant_square, _EN_PASSANT))


cdef void _gen_knight_moves(unsigned long long pieces, list moves,
                            unsigned long long active, unsigned long long enemy,
                            bint captures_only) noexcept:
    cdef unsigned long long lsb_bb, targets, t_lsb
    cdef int from_sq, to_sq, flag

    while pieces:
        lsb_bb  = pieces & -pieces
        from_sq = lsb_bb.bit_length() - 1
        pieces &= pieces - 1

        targets = KNIGHT_ATTACKS[from_sq] & ~active
        if captures_only:
            targets &= enemy

        while targets:
            t_lsb   = targets & -targets
            to_sq   = t_lsb.bit_length() - 1
            targets &= targets - 1
            flag    = _CAPTURE if SQUARE_TO_BB[to_sq] & enemy else _QUIET
            moves.append(_pack(from_sq, to_sq, flag))


cdef void _gen_king_moves(unsigned long long pieces, list moves,
                          unsigned long long active, unsigned long long enemy,
                          bint captures_only) noexcept:
    cdef unsigned long long lsb_bb, targets, t_lsb
    cdef int from_sq, to_sq, flag

    while pieces:
        lsb_bb  = pieces & -pieces
        from_sq = lsb_bb.bit_length() - 1
        pieces &= pieces - 1

        targets = KING_ATTACKS[from_sq] & ~active
        if captures_only:
            targets &= enemy

        while targets:
            t_lsb   = targets & -targets
            to_sq   = t_lsb.bit_length() - 1
            targets &= targets - 1
            flag    = _CAPTURE if SQUARE_TO_BB[to_sq] & enemy else _QUIET
            moves.append(_pack(from_sq, to_sq, flag))


cdef void _gen_castling_moves(State state, list moves,
                               unsigned long long all_pieces) noexcept:
    cdef bint opp = not state.is_white

    if state.is_white:
        if state.castling_rights & _CWK:
            if not (all_pieces & (SQUARE_TO_BB[_F1] | SQUARE_TO_BB[_G1])):
                if (not is_square_attacked(state, _E1, opp) and
                    not is_square_attacked(state, _F1, opp) and
                    not is_square_attacked(state, _G1, opp)):
                    moves.append(_pack(_E1, _G1, _CASTLE_KS))

        if state.castling_rights & _CWQ:
            if not (all_pieces & (SQUARE_TO_BB[_B1] | SQUARE_TO_BB[_C1] | SQUARE_TO_BB[_D1])):
                if (not is_square_attacked(state, _E1, opp) and
                    not is_square_attacked(state, _D1, opp) and
                    not is_square_attacked(state, _C1, opp)):
                    moves.append(_pack(_E1, _C1, _CASTLE_QS))
    else:
        if state.castling_rights & _CBK:
            if not (all_pieces & (SQUARE_TO_BB[_F8] | SQUARE_TO_BB[_G8])):
                if (not is_square_attacked(state, _E8, opp) and
                    not is_square_attacked(state, _F8, opp) and
                    not is_square_attacked(state, _G8, opp)):
                    moves.append(_pack(_E8, _G8, _CASTLE_KS))

        if state.castling_rights & _CBQ:
            if not (all_pieces & (SQUARE_TO_BB[_B8] | SQUARE_TO_BB[_C8] | SQUARE_TO_BB[_D8])):
                if (not is_square_attacked(state, _E8, opp) and
                    not is_square_attacked(state, _D8, opp) and
                    not is_square_attacked(state, _C8, opp)):
                    moves.append(_pack(_E8, _C8, _CASTLE_QS))


cdef void _gen_bishop_moves(unsigned long long pieces, list moves,
                             unsigned long long all_pieces,
                             unsigned long long active,
                             unsigned long long enemy,
                             bint captures_only) noexcept:
    cdef unsigned long long lsb_bb, targets, t_lsb
    cdef int from_sq, to_sq, flag

    while pieces:
        lsb_bb  = pieces & -pieces
        from_sq = lsb_bb.bit_length() - 1
        pieces &= pieces - 1

        targets = bishop_attacks(from_sq, all_pieces) & ~active
        if captures_only:
            targets &= enemy

        while targets:
            t_lsb   = targets & -targets
            to_sq   = t_lsb.bit_length() - 1
            targets &= targets - 1
            flag    = _CAPTURE if SQUARE_TO_BB[to_sq] & enemy else _QUIET
            moves.append(_pack(from_sq, to_sq, flag))


cdef void _gen_rook_moves(unsigned long long pieces, list moves,
                           unsigned long long all_pieces,
                           unsigned long long active,
                           unsigned long long enemy,
                           bint captures_only) noexcept:
    cdef unsigned long long lsb_bb, targets, t_lsb
    cdef int from_sq, to_sq, flag

    while pieces:
        lsb_bb  = pieces & -pieces
        from_sq = lsb_bb.bit_length() - 1
        pieces &= pieces - 1

        targets = rook_attacks(from_sq, all_pieces) & ~active
        if captures_only:
            targets &= enemy

        while targets:
            t_lsb   = targets & -targets
            to_sq   = t_lsb.bit_length() - 1
            targets &= targets - 1
            flag    = _CAPTURE if SQUARE_TO_BB[to_sq] & enemy else _QUIET
            moves.append(_pack(from_sq, to_sq, flag))


cdef void _gen_queen_moves(unsigned long long pieces, list moves,
                            unsigned long long all_pieces,
                            unsigned long long active,
                            unsigned long long enemy,
                            bint captures_only) noexcept:
    cdef unsigned long long lsb_bb, targets, t_lsb
    cdef int from_sq, to_sq, flag

    while pieces:
        lsb_bb  = pieces & -pieces
        from_sq = lsb_bb.bit_length() - 1
        pieces &= pieces - 1

        targets = (rook_attacks(from_sq, all_pieces) |
                   bishop_attacks(from_sq, all_pieces)) & ~active
        if captures_only:
            targets &= enemy

        while targets:
            t_lsb   = targets & -targets
            to_sq   = t_lsb.bit_length() - 1
            targets &= targets - 1
            flag    = _CAPTURE if SQUARE_TO_BB[to_sq] & enemy else _QUIET
            moves.append(_pack(from_sq, to_sq, flag))


cpdef list generate_pseudo_legal_moves(State state, bint captures_only=False):
    """return list of pseudo-legal moves for the current side to move"""
    cdef list moves = []
    cdef unsigned long long active, opponent, all_pieces
    cdef int P, N, B, R, Q, K
    cdef unsigned long long* pawn_attacks

    if state.is_white:
        active   = state.bitboards[_WHITE]
        opponent = state.bitboards[_BLACK]
        P = _WP; N = _WN; B = _WB; R = _WR; Q = _WQ; K = _WK
        pawn_attacks = WHITE_PAWN_ATTACKS
    else:
        active   = state.bitboards[_BLACK]
        opponent = state.bitboards[_WHITE]
        P = _BP; N = _BN; B = _BB; R = _BR; Q = _BQ; K = _BK
        pawn_attacks = BLACK_PAWN_ATTACKS

    all_pieces = active | opponent

    _gen_pawn_moves(state, moves, P, state.is_white, all_pieces, opponent, pawn_attacks, captures_only)
    _gen_knight_moves(state.bitboards[N], moves, active, opponent, captures_only)
    _gen_king_moves(state.bitboards[K], moves, active, opponent, captures_only)
    if not captures_only:
        _gen_castling_moves(state, moves, all_pieces)
    _gen_bishop_moves(state.bitboards[B], moves, all_pieces, active, opponent, captures_only)
    _gen_rook_moves(state.bitboards[R], moves, all_pieces, active, opponent, captures_only)
    _gen_queen_moves(state.bitboards[Q], moves, all_pieces, active, opponent, captures_only)

    return moves


def get_legal_moves(State state, bint captures_only=False):
    """return list of fully legal move ints (filters pseudo-legal by legality)"""
    pseudo = generate_pseudo_legal_moves(state, captures_only)
    return [move for move in pseudo if is_legal(state, move)]

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
    WP, BP, WN, BN, WB, BB, WR, BR, WQ, BQ, WK, BK,
    WHITE, BLACK, NORTH, SOUTH
)
from engine.core.move cimport (
    _pack, move_source, move_target, move_flag,
    is_capture, is_promotion, is_en_passant, is_castling
)
from engine.core.move import (
    QUIET, CAPTURE, EN_PASSANT,
    CASTLE_KS, CASTLE_QS,
    PROMOTION_N, PROMOTION_B, PROMOTION_R, PROMOTION_Q,
    PROMO_CAP_N, PROMO_CAP_B, PROMO_CAP_R, PROMO_CAP_Q,
    DOUBLE_PUSH,
)
from engine.board.state cimport State
from engine.moves.legality cimport is_legal, is_square_attacked, is_in_check, attackers_to_square

from engine.moves.precomputed cimport KNIGHT_ATTACKS, KING_ATTACKS, WHITE_PAWN_ATTACKS, BLACK_PAWN_ATTACKS, bishop_attacks, rook_attacks, SQUARE_TO_BB
from engine.core.bits cimport lsb, pop_lsb, popcount

cdef int _WP = WP, _WN = WN, _WB = WB, _WR = WR, _WQ = WQ, _WK = WK
cdef int _BP = BP, _BN = BN, _BB = BB, _BR = BR, _BQ = BQ, _BK = BK
cdef int _WHITE = WHITE, _BLACK = BLACK
cdef int _NULL_SQ = _NULL
cdef int _PAWN = PAWN, _KNIGHT = KNIGHT, _BISHOP = BISHOP
cdef int _ROOK = ROOK, _QUEEN = QUEEN, _KING = KING

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


cdef inline void _add_move(MoveList* moves, unsigned int move) noexcept:
    if moves.count < 256:
        moves.moves[moves.count] = move
        moves.count += 1


cdef inline void _add_promotions(MoveList* moves, int from_sq, int to_sq, bint is_capture) noexcept:
    if is_capture:
        _add_move(moves, _pack(from_sq, to_sq, _PCAP_Q))
        _add_move(moves, _pack(from_sq, to_sq, _PCAP_R))
        _add_move(moves, _pack(from_sq, to_sq, _PCAP_B))
        _add_move(moves, _pack(from_sq, to_sq, _PCAP_N))
    else:
        _add_move(moves, _pack(from_sq, to_sq, _PROM_Q))
        _add_move(moves, _pack(from_sq, to_sq, _PROM_R))
        _add_move(moves, _pack(from_sq, to_sq, _PROM_B))
        _add_move(moves, _pack(from_sq, to_sq, _PROM_N))


cdef inline void _add_target_moves(MoveList* moves, int from_sq,
                                   unsigned long long targets,
                                   unsigned long long enemy,
                                   bint captures_only) noexcept:
    cdef unsigned long long bb
    cdef int to_sq

    bb = targets & enemy
    while bb:
        to_sq = lsb(bb)
        bb    = pop_lsb(bb)
        _add_move(moves, _pack(from_sq, to_sq, _CAPTURE))

    if captures_only:
        return

    bb = targets & ~enemy
    while bb:
        to_sq = lsb(bb)
        bb    = pop_lsb(bb)
        _add_move(moves, _pack(from_sq, to_sq, _QUIET))


cdef inline unsigned long long _between_squares(int from_sq, int to_sq) noexcept:
    cdef int from_rank = from_sq >> 3
    cdef int from_file = from_sq & 7
    cdef int to_rank = to_sq >> 3
    cdef int to_file = to_sq & 7
    cdef int rank_delta = to_rank - from_rank
    cdef int file_delta = to_file - from_file
    cdef int abs_rank_delta = rank_delta if rank_delta >= 0 else -rank_delta
    cdef int abs_file_delta = file_delta if file_delta >= 0 else -file_delta
    cdef int step = 0
    cdef int sq
    cdef unsigned long long bb = 0

    if from_rank == to_rank:
        step = 1 if file_delta > 0 else -1
    elif from_file == to_file:
        step = 8 if rank_delta > 0 else -8
    elif abs_rank_delta == abs_file_delta:
        step = (8 if rank_delta > 0 else -8) + (1 if file_delta > 0 else -1)
    else:
        return 0

    sq = from_sq + step
    while sq != to_sq:
        bb |= SQUARE_TO_BB[sq]
        sq += step

    return bb


cdef void _gen_pawn_moves(State state, MoveList* moves, int pawn_key,
                          bint is_white, unsigned long long all_pieces,
                          unsigned long long enemy,
                          unsigned long long* attack_table,
                          bint captures_only) noexcept:
    cdef unsigned long long pawns, single_push, double_push, bb, attacks
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
            to_sq   = lsb(bb)
            bb      = pop_lsb(bb)
            from_sq = to_sq - direction

            is_promo = (is_white and to_sq >= _A8) or (not is_white and to_sq <= _H1)

            if is_promo:
                _add_promotions(moves, from_sq, to_sq, False)
            else:
                _add_move(moves, _pack(from_sq, to_sq, _QUIET))

        # double pushes
        bb = double_push
        while bb:
            to_sq   = lsb(bb)
            bb      = pop_lsb(bb)
            from_sq = to_sq - (2 * direction)
            _add_move(moves, _pack(from_sq, to_sq, _DOUBLE_PUSH))

    # captures
    bb = pawns
    while bb:
        from_sq = lsb(bb)
        bb      = pop_lsb(bb)

        attacks = attack_table[from_sq] & enemy
        while attacks:
            to_sq   = lsb(attacks)
            attacks = pop_lsb(attacks)

            is_promo = (is_white and to_sq >= _A8) or (not is_white and to_sq <= _H1)
            if is_promo:
                _add_promotions(moves, from_sq, to_sq, True)
            else:
                _add_move(moves, _pack(from_sq, to_sq, _CAPTURE))

        # en-passant
        if state.en_passant_square != _NULL_SQ:
            if attack_table[from_sq] & SQUARE_TO_BB[state.en_passant_square]:
                _add_move(moves, _pack(from_sq, state.en_passant_square, _EN_PASSANT))


cdef void _gen_pawn_evasions(State state, MoveList* moves, int pawn_key,
                             bint is_white, unsigned long long all_pieces,
                             unsigned long long enemy,
                             unsigned long long* attack_table,
                             unsigned long long target_mask) noexcept:
    cdef unsigned long long pawns, single_push_all, single_push, double_push, bb, attacks
    cdef unsigned long long ep_mask
    cdef int to_sq, from_sq, direction
    cdef bint is_promo

    pawns = state.bitboards[pawn_key]
    if not pawns:
        return

    if is_white:
        direction       = _NORTH
        single_push_all = (pawns << 8) & ~all_pieces
        single_push     = single_push_all & target_mask
        double_push     = ((single_push_all & _RANK_3) << 8) & ~all_pieces & target_mask
    else:
        direction       = _SOUTH
        single_push_all = (pawns >> 8) & ~all_pieces
        single_push     = single_push_all & target_mask
        double_push     = ((single_push_all & _RANK_6) >> 8) & ~all_pieces & target_mask

    bb = single_push
    while bb:
        to_sq   = lsb(bb)
        bb      = pop_lsb(bb)
        from_sq = to_sq - direction

        is_promo = (is_white and to_sq >= _A8) or (not is_white and to_sq <= _H1)

        if is_promo:
            _add_promotions(moves, from_sq, to_sq, False)
        else:
            _add_move(moves, _pack(from_sq, to_sq, _QUIET))

    bb = double_push
    while bb:
        to_sq   = lsb(bb)
        bb      = pop_lsb(bb)
        from_sq = to_sq - (2 * direction)
        _add_move(moves, _pack(from_sq, to_sq, _DOUBLE_PUSH))

    bb = pawns
    while bb:
        from_sq = lsb(bb)
        bb      = pop_lsb(bb)

        attacks = attack_table[from_sq] & enemy & target_mask
        while attacks:
            to_sq   = lsb(attacks)
            attacks = pop_lsb(attacks)

            is_promo = (is_white and to_sq >= _A8) or (not is_white and to_sq <= _H1)
            if is_promo:
                _add_promotions(moves, from_sq, to_sq, True)
            else:
                _add_move(moves, _pack(from_sq, to_sq, _CAPTURE))

        if state.en_passant_square != _NULL_SQ:
            ep_mask = SQUARE_TO_BB[state.en_passant_square]
            if attack_table[from_sq] & ep_mask:
                _add_move(moves, _pack(from_sq, state.en_passant_square, _EN_PASSANT))


cdef void _gen_knight_moves(unsigned long long pieces, MoveList* moves,
                            unsigned long long active, unsigned long long enemy,
                            bint captures_only) noexcept:
    cdef unsigned long long targets
    cdef int from_sq

    while pieces:
        from_sq = lsb(pieces)
        pieces  = pop_lsb(pieces)

        targets = KNIGHT_ATTACKS[from_sq] & ~active
        _add_target_moves(moves, from_sq, targets, enemy, captures_only)


cdef void _gen_knight_evasions(unsigned long long pieces, MoveList* moves,
                               unsigned long long active, unsigned long long enemy,
                               unsigned long long target_mask) noexcept:
    cdef unsigned long long targets
    cdef int from_sq

    while pieces:
        from_sq = lsb(pieces)
        pieces  = pop_lsb(pieces)

        targets = KNIGHT_ATTACKS[from_sq] & ~active & target_mask
        _add_target_moves(moves, from_sq, targets, enemy, False)


cdef void _gen_king_moves(unsigned long long pieces, MoveList* moves,
                          unsigned long long active, unsigned long long enemy,
                          bint captures_only) noexcept:
    cdef unsigned long long targets
    cdef int from_sq

    while pieces:
        from_sq = lsb(pieces)
        pieces  = pop_lsb(pieces)

        targets = KING_ATTACKS[from_sq] & ~active
        _add_target_moves(moves, from_sq, targets, enemy, captures_only)


cdef void _gen_bishop_evasions(unsigned long long pieces, MoveList* moves,
                               unsigned long long all_pieces,
                               unsigned long long active,
                               unsigned long long enemy,
                               unsigned long long target_mask) noexcept:
    cdef unsigned long long targets
    cdef int from_sq

    while pieces:
        from_sq = lsb(pieces)
        pieces  = pop_lsb(pieces)

        targets = bishop_attacks(from_sq, all_pieces) & ~active & target_mask
        _add_target_moves(moves, from_sq, targets, enemy, False)


cdef void _gen_rook_evasions(unsigned long long pieces, MoveList* moves,
                             unsigned long long all_pieces,
                             unsigned long long active,
                             unsigned long long enemy,
                             unsigned long long target_mask) noexcept:
    cdef unsigned long long targets
    cdef int from_sq

    while pieces:
        from_sq = lsb(pieces)
        pieces  = pop_lsb(pieces)

        targets = rook_attacks(from_sq, all_pieces) & ~active & target_mask
        _add_target_moves(moves, from_sq, targets, enemy, False)


cdef void _gen_queen_evasions(unsigned long long pieces, MoveList* moves,
                              unsigned long long all_pieces,
                              unsigned long long active,
                              unsigned long long enemy,
                              unsigned long long target_mask) noexcept:
    cdef unsigned long long targets
    cdef int from_sq

    while pieces:
        from_sq = lsb(pieces)
        pieces  = pop_lsb(pieces)

        targets = (rook_attacks(from_sq, all_pieces) |
                   bishop_attacks(from_sq, all_pieces)) & ~active & target_mask
        _add_target_moves(moves, from_sq, targets, enemy, False)


cdef void _gen_castling_moves(State state, MoveList* moves,
                               unsigned long long all_pieces) noexcept:
    cdef bint opp = not state.is_white

    if state.is_white:
        if state.castling_rights & _CWK:
            if not (all_pieces & (SQUARE_TO_BB[_F1] | SQUARE_TO_BB[_G1])):
                if (not is_square_attacked(state, _E1, opp) and
                    not is_square_attacked(state, _F1, opp) and
                    not is_square_attacked(state, _G1, opp)):
                    _add_move(moves, _pack(_E1, _G1, _CASTLE_KS))

        if state.castling_rights & _CWQ:
            if not (all_pieces & (SQUARE_TO_BB[_B1] | SQUARE_TO_BB[_C1] | SQUARE_TO_BB[_D1])):
                if (not is_square_attacked(state, _E1, opp) and
                    not is_square_attacked(state, _D1, opp) and
                    not is_square_attacked(state, _C1, opp)):
                    _add_move(moves, _pack(_E1, _C1, _CASTLE_QS))
    else:
        if state.castling_rights & _CBK:
            if not (all_pieces & (SQUARE_TO_BB[_F8] | SQUARE_TO_BB[_G8])):
                if (not is_square_attacked(state, _E8, opp) and
                    not is_square_attacked(state, _F8, opp) and
                    not is_square_attacked(state, _G8, opp)):
                    _add_move(moves, _pack(_E8, _G8, _CASTLE_KS))

        if state.castling_rights & _CBQ:
            if not (all_pieces & (SQUARE_TO_BB[_B8] | SQUARE_TO_BB[_C8] | SQUARE_TO_BB[_D8])):
                if (not is_square_attacked(state, _E8, opp) and
                    not is_square_attacked(state, _D8, opp) and
                    not is_square_attacked(state, _C8, opp)):
                    _add_move(moves, _pack(_E8, _C8, _CASTLE_QS))


cdef void _gen_bishop_moves(unsigned long long pieces, MoveList* moves,
                             unsigned long long all_pieces,
                             unsigned long long active,
                             unsigned long long enemy,
                             bint captures_only) noexcept:
    cdef unsigned long long targets
    cdef int from_sq

    while pieces:
        from_sq = lsb(pieces)
        pieces  = pop_lsb(pieces)

        targets = bishop_attacks(from_sq, all_pieces) & ~active
        _add_target_moves(moves, from_sq, targets, enemy, captures_only)


cdef void _gen_rook_moves(unsigned long long pieces, MoveList* moves,
                           unsigned long long all_pieces,
                           unsigned long long active,
                           unsigned long long enemy,
                           bint captures_only) noexcept:
    cdef unsigned long long targets
    cdef int from_sq

    while pieces:
        from_sq = lsb(pieces)
        pieces  = pop_lsb(pieces)

        targets = rook_attacks(from_sq, all_pieces) & ~active
        _add_target_moves(moves, from_sq, targets, enemy, captures_only)


cdef void _gen_queen_moves(unsigned long long pieces, MoveList* moves,
                            unsigned long long all_pieces,
                            unsigned long long active,
                            unsigned long long enemy,
                            bint captures_only) noexcept:
    cdef unsigned long long targets
    cdef int from_sq

    while pieces:
        from_sq = lsb(pieces)
        pieces  = pop_lsb(pieces)

        targets = (rook_attacks(from_sq, all_pieces) |
                   bishop_attacks(from_sq, all_pieces)) & ~active
        _add_target_moves(moves, from_sq, targets, enemy, captures_only)


cdef void generate_pseudo_legal_move_list(State state, MoveList* moves, bint captures_only) noexcept:
    cdef unsigned long long active, opponent, all_pieces
    cdef int P, N, B, R, Q, K
    cdef unsigned long long* pawn_attacks

    moves.count = 0

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


cdef void generate_check_evasion_move_list(State state, MoveList* moves) noexcept:
    cdef unsigned long long active, opponent, all_pieces, king_bb, checkers, block_mask, target_mask
    cdef unsigned long long* pawn_attacks
    cdef int P, N, B, R, Q, K, king_sq, checker_sq, checker_piece

    moves.count = 0

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

    king_bb = state.bitboards[K]
    if not king_bb:
        return

    king_sq = lsb(king_bb)
    checkers = attackers_to_square(state, king_sq, not state.is_white)
    if not checkers:
        generate_pseudo_legal_move_list(state, moves, False)
        return

    if popcount(checkers) >= 2:
        _gen_king_moves(king_bb, moves, active, opponent, False)
        return

    checker_sq = lsb(checkers)
    checker_piece = state.board[checker_sq]
    block_mask = 0

    if (checker_piece == _WB or checker_piece == _BB or
        checker_piece == _WR or checker_piece == _BR or
        checker_piece == _WQ or checker_piece == _BQ):
        block_mask = _between_squares(king_sq, checker_sq)

    target_mask = checkers | block_mask

    _gen_king_moves(king_bb, moves, active, opponent, False)
    _gen_pawn_evasions(state, moves, P, state.is_white, all_pieces, opponent, pawn_attacks, target_mask)
    _gen_knight_evasions(state.bitboards[N], moves, active, opponent, target_mask)
    _gen_bishop_evasions(state.bitboards[B], moves, all_pieces, active, opponent, target_mask)
    _gen_rook_evasions(state.bitboards[R], moves, all_pieces, active, opponent, target_mask)
    _gen_queen_evasions(state.bitboards[Q], moves, all_pieces, active, opponent, target_mask)


cdef bint is_pseudo_legal_move(State state, unsigned int move) noexcept:
    cdef int from_sq = move_source(move)
    cdef int to_sq = move_target(move)
    cdef int flag = move_flag(move)
    cdef int piece = state.board[from_sq]
    cdef int target_piece = state.board[to_sq]
    cdef int piece_type, direction
    cdef unsigned long long active, opponent, all_pieces, to_mask
    cdef bint target_enemy, promo_target

    if piece == _NULL_SQ:
        return False

    if state.is_white:
        if not (piece & _WHITE): return False
        active   = state.bitboards[_WHITE]
        opponent = state.bitboards[_BLACK]
        direction = _NORTH
        promo_target = to_sq >= _A8
    else:
        if piece & _WHITE: return False
        active   = state.bitboards[_BLACK]
        opponent = state.bitboards[_WHITE]
        direction = _SOUTH
        promo_target = to_sq <= _H1

    to_mask = SQUARE_TO_BB[to_sq]
    if active & to_mask:
        return False

    target_enemy = (opponent & to_mask) != 0
    all_pieces = active | opponent
    piece_type = piece & ~_WHITE

    if piece_type == _PAWN:
        if is_promotion(move) != promo_target:
            return False

        if is_en_passant(move):
            if state.en_passant_square != to_sq: return False
            if target_piece != _NULL_SQ: return False
            if state.is_white:
                return (WHITE_PAWN_ATTACKS[from_sq] & to_mask) != 0
            return (BLACK_PAWN_ATTACKS[from_sq] & to_mask) != 0

        if is_capture(move):
            if not target_enemy: return False
            if state.is_white:
                return (WHITE_PAWN_ATTACKS[from_sq] & to_mask) != 0
            return (BLACK_PAWN_ATTACKS[from_sq] & to_mask) != 0

        if target_piece != _NULL_SQ:
            return False

        if flag == _DOUBLE_PUSH:
            if state.is_white:
                return from_sq >= 8 and from_sq <= 15 and to_sq == from_sq + 16 and not (all_pieces & SQUARE_TO_BB[from_sq + 8])
            return from_sq >= 48 and from_sq <= 55 and to_sq == from_sq - 16 and not (all_pieces & SQUARE_TO_BB[from_sq - 8])

        if flag != _QUIET and not is_promotion(move):
            return False

        return to_sq == from_sq + direction

    if is_promotion(move) or is_en_passant(move):
        return False

    if piece_type == _KNIGHT:
        if flag != (_CAPTURE if target_enemy else _QUIET): return False
        return (KNIGHT_ATTACKS[from_sq] & to_mask) != 0

    if piece_type == _BISHOP:
        if flag != (_CAPTURE if target_enemy else _QUIET): return False
        return (bishop_attacks(from_sq, all_pieces) & to_mask) != 0

    if piece_type == _ROOK:
        if flag != (_CAPTURE if target_enemy else _QUIET): return False
        return (rook_attacks(from_sq, all_pieces) & to_mask) != 0

    if piece_type == _QUEEN:
        if flag != (_CAPTURE if target_enemy else _QUIET): return False
        return ((rook_attacks(from_sq, all_pieces) | bishop_attacks(from_sq, all_pieces)) & to_mask) != 0

    if piece_type == _KING:
        if is_castling(move):
            if target_enemy: return False
            if state.is_white:
                if from_sq != _E1: return False
                if flag == _CASTLE_KS:
                    if to_sq != _G1 or not (state.castling_rights & _CWK): return False
                    if all_pieces & (SQUARE_TO_BB[_F1] | SQUARE_TO_BB[_G1]): return False
                    return (not is_square_attacked(state, _E1, False) and
                            not is_square_attacked(state, _F1, False) and
                            not is_square_attacked(state, _G1, False))
                if flag == _CASTLE_QS:
                    if to_sq != _C1 or not (state.castling_rights & _CWQ): return False
                    if all_pieces & (SQUARE_TO_BB[_B1] | SQUARE_TO_BB[_C1] | SQUARE_TO_BB[_D1]): return False
                    return (not is_square_attacked(state, _E1, False) and
                            not is_square_attacked(state, _D1, False) and
                            not is_square_attacked(state, _C1, False))
            else:
                if from_sq != _E8: return False
                if flag == _CASTLE_KS:
                    if to_sq != _G8 or not (state.castling_rights & _CBK): return False
                    if all_pieces & (SQUARE_TO_BB[_F8] | SQUARE_TO_BB[_G8]): return False
                    return (not is_square_attacked(state, _E8, True) and
                            not is_square_attacked(state, _F8, True) and
                            not is_square_attacked(state, _G8, True))
                if flag == _CASTLE_QS:
                    if to_sq != _C8 or not (state.castling_rights & _CBQ): return False
                    if all_pieces & (SQUARE_TO_BB[_B8] | SQUARE_TO_BB[_C8] | SQUARE_TO_BB[_D8]): return False
                    return (not is_square_attacked(state, _E8, True) and
                            not is_square_attacked(state, _D8, True) and
                            not is_square_attacked(state, _C8, True))
            return False

        if flag != (_CAPTURE if target_enemy else _QUIET): return False
        return (KING_ATTACKS[from_sq] & to_mask) != 0

    return False


cpdef list generate_pseudo_legal_moves(State state, bint captures_only=False):
    """return list of pseudo-legal moves for the current side to move"""
    cdef MoveList move_list
    cdef list moves = []
    cdef int i

    generate_pseudo_legal_move_list(state, &move_list, captures_only)

    for i in range(move_list.count):
        moves.append(move_list.moves[i])

    return moves


def get_legal_moves(State state, bint captures_only=False):
    """return list of fully legal move ints (filters pseudo-legal by legality)"""
    cdef MoveList pseudo
    cdef list legal = []
    cdef int i
    cdef unsigned int move

    if not captures_only and is_in_check(state, state.is_white):
        generate_check_evasion_move_list(state, &pseudo)
    else:
        generate_pseudo_legal_move_list(state, &pseudo, captures_only)

    for i in range(pseudo.count):
        move = pseudo.moves[i]
        if is_legal(state, move):
            legal.append(move)

    return legal

cdef void generate_legal_move_list(State state, MoveList* out, bint captures_only) noexcept:
    """fill out with fully legal moves (pin/check filtered), no Python list"""
    cdef MoveList pseudo
    cdef int i
    cdef unsigned int move

    if not captures_only and is_in_check(state, state.is_white):
        generate_check_evasion_move_list(state, &pseudo)
    else:
        generate_pseudo_legal_move_list(state, &pseudo, captures_only)

    out.count = 0
    for i in range(pseudo.count):
        move = pseudo.moves[i]
        if is_legal(state, move):
            _add_move(out, move)

# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True

from engine.board.state cimport State
from engine.core.bits cimport lsb
from engine.core.move cimport (
    is_capture, is_promotion, is_en_passant, is_castling,
    move_source, move_target, move_promotion_index
)
from engine.core.constants import (
    WHITE, BLACK, NULL as _NULL, PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
    CASTLE_WK, CASTLE_WQ, CASTLE_BK, CASTLE_BQ,
    A1, H1, A8, H8, E1, C1, G1, E8, C8, G8, F1, D1, F8, D8,
    WP, WN, WB, WR, WQ, WK,
    BP, BN, BB, BR, BQ, BK,
    NORTH, SOUTH
)
from engine.moves.precomputed cimport SQUARE_TO_BB
from engine.core.zobrist cimport (
    ZOBRIST_PIECES, ZOBRIST_CASTLING, ZOBRIST_EN_PASSANT, ZOBRIST_BLACK_TO_MOVE
)
from engine.search.evaluation cimport MG_TABLE_C, EG_TABLE_C, PHASE_WEIGHTS_C

# c-level constants to avoid python attribute lookups in hot path
cdef int _NULL_VAL = _NULL
cdef int _WHITE = WHITE, _BLACK = BLACK
cdef int _PAWN = PAWN, _KNIGHT = KNIGHT, _BISHOP = BISHOP
cdef int _ROOK = ROOK, _QUEEN = QUEEN, _KING = KING
cdef int _WP = WP, _WN = WN, _WB = WB, _WR = WR, _WQ = WQ, _WK = WK
cdef int _BP = BP, _BN = BN, _BB = BB, _BR = BR, _BQ = BQ, _BK = BK
cdef int _CWK = CASTLE_WK, _CWQ = CASTLE_WQ, _CBK = CASTLE_BK, _CBQ = CASTLE_BQ
cdef int _A1 = A1, _H1 = H1, _A8 = A8, _H8 = H8
cdef int _E1 = E1, _C1 = C1, _G1 = G1, _E8 = E8, _C8 = C8, _G8 = G8
cdef int _F1 = F1, _D1 = D1, _F8 = F8, _D8 = D8
cdef int _NORTH = NORTH, _SOUTH = SOUTH

def is_repetition(State state):
    cdef unsigned long long current_hash
    cdef int count, i, search_limit

    if not state.history: return False, False

    search_limit = min(state.halfmove_clock, len(state.history))

    # not enough moves played
    if search_limit < 4: return False, False

    current_hash = state.hash
    count = 0

    for i in range(len(state.history) - 2, max(len(state.history) - search_limit - 1, -1), -2):
        if state.history[i] == current_hash:
            count += 1
        if count >= 5: break # over fivefold

    # threefold, fivefold
    return count >= 2, count >= 4


cpdef bint has_insufficient_material(State state):
    cdef int w_knights, w_bishops, b_knights, b_bishops, total_minors
    cdef int w_sq, b_sq
    cdef unsigned long long wb_bb, bb_bb

    # pawns, rooks, queens
    if (state.bitboards[_WP] or state.bitboards[_BP] or
        state.bitboards[_WR] or state.bitboards[_BR] or
        state.bitboards[_WQ] or state.bitboards[_BQ]):
        return False

    w_knights = bin(state.bitboards[_WN]).count('1')
    w_bishops = bin(state.bitboards[_WB]).count('1')
    b_knights = bin(state.bitboards[_BN]).count('1')
    b_bishops = bin(state.bitboards[_BB]).count('1')

    total_minors = w_knights + w_bishops + b_knights + b_bishops

    if total_minors == 0: return True
    if total_minors == 1: return True

    if w_bishops == 1 and b_bishops == 1 and w_knights == 0 and b_knights == 0:
        wb_bb = state.bitboards[_WB]
        bb_bb = state.bitboards[_BB]
        w_sq  = lsb(wb_bb)
        b_sq  = lsb(bb_bb)
        # same-colour bishops?
        if (w_sq // 8 + w_sq % 8) % 2 == (b_sq // 8 + b_sq % 8) % 2: return True

    return False


cpdef void make_null_move(State state):
    cdef int old_ep, old_last_moved
    cdef unsigned long long old_hash

    old_ep          = state.en_passant_square
    old_hash        = state.hash
    old_last_moved  = state.last_moved_piece_sq

    state.context_stack.append((old_ep, old_hash, old_last_moved))

    if old_ep != _NULL_VAL: state.hash ^= ZOBRIST_EN_PASSANT[old_ep % 8]
    else:                   state.hash ^= ZOBRIST_EN_PASSANT[8]

    state.en_passant_square = _NULL_VAL
    state.hash ^= ZOBRIST_EN_PASSANT[8]
    state.is_white = not state.is_white
    state.hash ^= ZOBRIST_BLACK_TO_MOVE
    state.last_moved_piece_sq = _NULL_VAL


cpdef void unmake_null_move(State state):
    old_ep, old_hash, old_last_moved = state.context_stack.pop()
    state.en_passant_square = old_ep
    state.hash = old_hash
    state.is_white = not state.is_white
    state.last_moved_piece_sq = old_last_moved


cpdef void make_move(State state, unsigned int move):
    cdef int start_sq, target_sq
    cdef int moving_piece, active_bb, opponent_bb
    cdef int ep_offset, enemy_pawn
    cdef int captured_piece, capture_sq
    cdef int promo_idx, promo_piece_type, promoted_piece, target_piece
    cdef int piece_type, captured_type
    cdef int rook, r_from, r_to
    cdef int ep_key
    cdef unsigned long long start_mask, target_mask, cap_mask

    cdef unsigned long long old_hash     = state.hash
    cdef int old_castling                = state.castling_rights
    cdef int old_ep                      = state.en_passant_square
    cdef int old_halfmove                = state.halfmove_clock
    cdef int old_mg                      = state.mg_score
    cdef int old_eg                      = state.eg_score
    cdef int old_phase                   = state.phase
    cdef unsigned long long old_w_passed = state.white_passed_pawns
    cdef unsigned long long old_b_passed = state.black_passed_pawns
    cdef int old_last_moved              = state.last_moved_piece_sq

    start_sq  = move_source(move)
    target_sq = move_target(move)

    moving_piece = state.board[start_sq]

    if state.is_white:
        active_bb   = _WHITE
        opponent_bb = _BLACK
        ep_offset   = _SOUTH
        enemy_pawn  = _BP
    else:
        active_bb   = _BLACK
        opponent_bb = _WHITE
        ep_offset   = _NORTH
        enemy_pawn  = _WP

    start_mask  = SQUARE_TO_BB[start_sq]
    target_mask = SQUARE_TO_BB[target_sq]

    state.mg_score -= MG_TABLE_C[moving_piece][start_sq]
    state.eg_score -= EG_TABLE_C[moving_piece][start_sq]

    state.bitboards[moving_piece] &= ~start_mask
    state.bitboards[active_bb]    &= ~start_mask
    state.hash ^= ZOBRIST_PIECES[moving_piece][start_sq]
    state.board[start_sq] = _NULL_VAL

    captured_piece = _NULL_VAL

    # capture
    if is_capture(move):
        # en-passant
        if is_en_passant(move):
            capture_sq     = target_sq + ep_offset
            captured_piece = enemy_pawn
            cap_mask       = SQUARE_TO_BB[capture_sq]

            state.bitboards[captured_piece] &= ~cap_mask
            state.bitboards[opponent_bb]    &= ~cap_mask
            state.hash ^= ZOBRIST_PIECES[captured_piece][capture_sq]
            state.board[capture_sq] = _NULL_VAL

            state.mg_score -= MG_TABLE_C[captured_piece][capture_sq]
            state.eg_score -= EG_TABLE_C[captured_piece][capture_sq]
            state.phase    -= PHASE_WEIGHTS_C[captured_piece]
            state.piece_counts[captured_piece] -= 1

            if not state.is_white:
                state.white_passed_pawns &= ~cap_mask
            else:
                state.black_passed_pawns &= ~cap_mask
        # normal capture
        else:
            captured_piece = state.board[target_sq]

            state.bitboards[captured_piece] &= ~target_mask
            state.bitboards[opponent_bb]    &= ~target_mask
            state.hash ^= ZOBRIST_PIECES[captured_piece][target_sq]

            state.mg_score -= MG_TABLE_C[captured_piece][target_sq]
            state.eg_score -= EG_TABLE_C[captured_piece][target_sq]
            state.phase    -= PHASE_WEIGHTS_C[captured_piece]
            state.piece_counts[captured_piece] -= 1

            # update passed pawn tracking if a pawn was captured
            captured_type = captured_piece & ~_WHITE
            if captured_type == _PAWN:
                if captured_piece & _WHITE:
                    state.white_passed_pawns &= ~target_mask
                else:
                    state.black_passed_pawns &= ~target_mask

    # promotion
    if is_promotion(move):
        promo_idx        = move_promotion_index(move)
        promo_types      = (_KNIGHT, _BISHOP, _ROOK, _QUEEN)
        promo_piece_type = promo_types[promo_idx]

        promoted_piece = (moving_piece & _WHITE) | promo_piece_type
        state.phase   -= PHASE_WEIGHTS_C[moving_piece]
        state.phase   += PHASE_WEIGHTS_C[promoted_piece]
        target_piece   = promoted_piece

        state.piece_counts[moving_piece]   -= 1
        state.piece_counts[promoted_piece] += 1

        if state.is_white:
            state.white_passed_pawns &= ~start_mask
        else:
            state.black_passed_pawns &= ~start_mask
    else:
        target_piece = moving_piece

    state.mg_score += MG_TABLE_C[target_piece][target_sq]
    state.eg_score += EG_TABLE_C[target_piece][target_sq]

    state.bitboards[target_piece] |= target_mask
    state.bitboards[active_bb]    |= target_mask
    state.hash ^= ZOBRIST_PIECES[target_piece][target_sq]
    state.board[target_sq] = target_piece

    # update passed pawn tracking for pawn push
    piece_type = moving_piece & ~_WHITE
    if piece_type == _PAWN and not is_promotion(move):
        if state.is_white:
            state.white_passed_pawns &= ~start_mask
            state.white_passed_pawns |= target_mask
        else:
            state.black_passed_pawns &= ~start_mask
            state.black_passed_pawns |= target_mask

    # castling rook relocation
    if is_castling(move):
        rook = _WR if state.is_white else _BR
        r_from = 0; r_to = 0

        if target_sq == _G1:   r_from = _H1; r_to = _F1
        elif target_sq == _C1: r_from = _A1; r_to = _D1
        elif target_sq == _G8: r_from = _H8; r_to = _F8
        elif target_sq == _C8: r_from = _A8; r_to = _D8

        state.bitboards[rook]     &= ~SQUARE_TO_BB[r_from]
        state.bitboards[rook]     |=  SQUARE_TO_BB[r_to]
        state.bitboards[active_bb] &= ~SQUARE_TO_BB[r_from]
        state.bitboards[active_bb] |=  SQUARE_TO_BB[r_to]

        state.hash ^= ZOBRIST_PIECES[rook][r_from]
        state.hash ^= ZOBRIST_PIECES[rook][r_to]

        state.board[r_from] = _NULL_VAL
        state.board[r_to]   = rook

        state.mg_score -= MG_TABLE_C[rook][r_from]
        state.eg_score -= EG_TABLE_C[rook][r_from]
        state.mg_score += MG_TABLE_C[rook][r_to]
        state.eg_score += EG_TABLE_C[rook][r_to]

    # castling rights update
    state.hash ^= ZOBRIST_CASTLING[state.castling_rights]

    if start_sq == _A1 or target_sq == _A1: state.castling_rights &= ~_CWQ
    if start_sq == _H1 or target_sq == _H1: state.castling_rights &= ~_CWK
    if start_sq == _A8 or target_sq == _A8: state.castling_rights &= ~_CBQ
    if start_sq == _H8 or target_sq == _H8: state.castling_rights &= ~_CBK
    if start_sq == _E1: state.castling_rights &= ~(_CWK | _CWQ)
    if start_sq == _E8: state.castling_rights &= ~(_CBK | _CBQ)

    state.hash ^= ZOBRIST_CASTLING[state.castling_rights]

    # en-passant hash update
    ep_key = old_ep % 8 if old_ep != _NULL_VAL else 8
    state.hash ^= ZOBRIST_EN_PASSANT[ep_key]

    state.en_passant_square = _NULL_VAL

    if piece_type == _PAWN and (target_sq - start_sq) * (1 if state.is_white else -1) == _NORTH + _NORTH:
        state.en_passant_square = (start_sq + target_sq) // 2

    ep_key = state.en_passant_square % 8 if state.en_passant_square != _NULL_VAL else 8
    state.hash ^= ZOBRIST_EN_PASSANT[ep_key]

    if piece_type == _PAWN or is_capture(move):
        state.halfmove_clock = 0
    else:
        state.halfmove_clock += 1

    if not state.is_white:
        state.fullmove_number += 1

    state.last_moved_piece_sq = target_sq
    state.is_white = not state.is_white
    state.hash ^= ZOBRIST_BLACK_TO_MOVE

    state.history.append(old_hash)
    state.context_stack.append((
        captured_piece,
        old_castling,
        old_ep,
        old_halfmove,
        old_hash,
        old_mg,
        old_eg,
        old_phase,
        old_w_passed,
        old_b_passed,
        old_last_moved,
    ))


cpdef void unmake_move(State state, unsigned int move):
    cdef int start_sq, target_sq
    cdef int target_piece, active_bb, opponent_bb
    cdef int rook, r_from, r_to
    cdef int capture_sq, ep_offset
    cdef int captured_piece, old_castling, old_ep, old_halfmove
    cdef int old_mg, old_eg, old_phase, old_last_moved
    cdef int pawn
    cdef unsigned long long old_hash, old_w_passed, old_b_passed
    cdef unsigned long long start_mask, target_mask

    undo_info = state.context_stack.pop()
    (captured_piece, old_castling, old_ep, old_halfmove,
     old_hash, old_mg, old_eg, old_phase,
     old_w_passed, old_b_passed, old_last_moved) = undo_info

    state.history.pop()
    state.hash               = old_hash
    state.castling_rights    = old_castling
    state.en_passant_square  = old_ep
    state.halfmove_clock     = old_halfmove
    state.is_white           = not state.is_white
    state.mg_score           = old_mg
    state.eg_score           = old_eg
    state.phase              = old_phase
    state.white_passed_pawns = old_w_passed
    state.black_passed_pawns = old_b_passed
    state.last_moved_piece_sq = old_last_moved

    if not state.is_white:
        state.fullmove_number -= 1

    if state.is_white:
        active_bb   = _WHITE
        opponent_bb = _BLACK
    else:
        active_bb   = _BLACK
        opponent_bb = _WHITE

    start_sq  = move_source(move)
    target_sq = move_target(move)

    start_mask  = SQUARE_TO_BB[start_sq]
    target_mask = SQUARE_TO_BB[target_sq]

    target_piece = state.board[target_sq]

    if is_promotion(move):
        state.bitboards[target_piece] &= ~target_mask
        state.bitboards[active_bb]    &= ~target_mask
        state.board[target_sq] = _NULL_VAL

        pawn = _WP if state.is_white else _BP
        state.bitboards[pawn]      |= start_mask
        state.bitboards[active_bb] |= start_mask
        state.board[start_sq] = pawn

        state.piece_counts[target_piece] -= 1
        state.piece_counts[pawn]         += 1
    else:
        state.bitboards[target_piece] &= ~target_mask
        state.bitboards[target_piece] |= start_mask
        state.bitboards[active_bb]    &= ~target_mask
        state.bitboards[active_bb]    |= start_mask

        state.board[target_sq] = _NULL_VAL
        state.board[start_sq]  = target_piece

        if is_castling(move):
            rook = _WR if state.is_white else _BR
            r_from = 0; r_to = 0
            if target_sq == _G1:   r_from = _H1; r_to = _F1
            elif target_sq == _C1: r_from = _A1; r_to = _D1
            elif target_sq == _G8: r_from = _H8; r_to = _F8
            elif target_sq == _C8: r_from = _A8; r_to = _D8

            state.bitboards[rook]      &= ~SQUARE_TO_BB[r_to]
            state.bitboards[rook]      |=  SQUARE_TO_BB[r_from]
            state.bitboards[active_bb] &= ~SQUARE_TO_BB[r_to]
            state.bitboards[active_bb] |=  SQUARE_TO_BB[r_from]

            state.board[r_to]   = _NULL_VAL
            state.board[r_from] = rook

    if captured_piece != _NULL_VAL:
        state.piece_counts[captured_piece] += 1

        if is_en_passant(move):
            ep_offset  = _SOUTH if state.is_white else _NORTH
            capture_sq = target_sq + ep_offset
            state.bitboards[captured_piece] |= SQUARE_TO_BB[capture_sq]
            state.bitboards[opponent_bb]    |= SQUARE_TO_BB[capture_sq]
            state.board[capture_sq] = captured_piece
        else:
            state.bitboards[captured_piece] |= target_mask
            state.bitboards[opponent_bb]    |= target_mask
            state.board[target_sq] = captured_piece

from engine.board.state import State
from engine.core.move import (
    CAPTURE_FLAG, PROMO_FLAG, EP_FLAG, CASTLE_KS_FLAG, CASTLE_QS_FLAG,
    SHIFT_TARGET, SHIFT_FLAG, SPECIAL_1, SPECIAL_0
)
from engine.core.constants import (
    WHITE, BLACK, NULL, PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
    CASTLE_WK, CASTLE_WQ, CASTLE_BK, CASTLE_BQ,
    A1, H1, A8, H8, E1, C1, G1, E8, C8, G8, F1, D1, F8, D8,
    MASK_SOURCE,
    WP, WN, WB, WR, WQ, WK,
    BP, BN, BB, BR, BQ, BK,
    WHITE, BLACK,
    NORTH, SOUTH, SQUARE_TO_BB
)
from engine.core.zobrist import ZOBRIST_KEYS
from engine.search.evaluation import MG_TABLE, EG_TABLE, PHASE_WEIGHTS


def is_repetition(state: State):
    if not state.history: 
        return False, False
    
    # an only check positions since last irreversible move (capture / pawn move)
    search_limit = min(state.halfmove_clock, len(state.history))
    
    if search_limit < 4:  # need at least 4 ply for threefold
        return False, False
    
    current_hash = state.hash
    count = 0
    
    for i in range(len(state.history) - 2, max(len(state.history) - search_limit - 1, -1), -2):
        if state.history[i] == current_hash: count += 1
    
    # count is number of previous occurrences, current position is + 1
    threefold = count >= 2
    fivefold = count >= 4
    
    return threefold, fivefold

def has_insufficient_material(state: State):
    bitboards = state.bitboards
    
    # if there are pawns, rooks, or queens, there's sufficient material
    if bitboards[WP] or bitboards[BP] or bitboards[WR] or bitboards[BR] or bitboards[WQ] or bitboards[BQ]: return False
    
    # count pieces
    w_knights = bitboards[WN].bit_count()
    w_bishops = bitboards[WB].bit_count()
    b_knights = bitboards[BN].bit_count()
    b_bishops = bitboards[BB].bit_count()
    
    total_minors = w_knights + w_bishops + b_knights + b_bishops
    
    # king vs king
    if total_minors == 0:
        return True
    
    # king + minor vs king
    if total_minors == 1:
        return True
    
    # king + bishop vs king + bishop (same colour bishops)
    if w_bishops == 1 and b_bishops == 1 and w_knights == 0 and b_knights == 0:
        # check if bishops are on same colour squares
        w_bishop_sq = (bitboards[WB] & -bitboards[WB]).bit_length() - 1
        b_bishop_sq = (bitboards[BB] & -bitboards[BB]).bit_length() - 1
        
        w_bishop_colour = (w_bishop_sq // 8 + w_bishop_sq % 8) % 2
        b_bishop_colour = (b_bishop_sq // 8 + b_bishop_sq % 8) % 2
        
        if w_bishop_colour == b_bishop_colour: return True
    
    return False

def make_null_move(state: State):
    old_ep = state.en_passant_square
    old_hash = state.hash
    old_last_moved = state.last_moved_piece_sq
    
    # store undo info on stack
    state.context_stack.append((old_ep, old_hash, old_last_moved))
    
    if old_ep != NULL:
        ep_key = old_ep % 8
        state.hash ^= ZOBRIST_KEYS.en_passant[ep_key]
    else:
        state.hash ^= ZOBRIST_KEYS.en_passant[8]
    
    state.is_white = not state.is_white
    state.hash ^= ZOBRIST_KEYS.black_to_move
    
    state.last_moved_piece_sq = NULL

def unmake_null_move(state: State):
    # retrieve from stack
    old_ep, old_hash, old_last_moved = state.context_stack.pop()
    
    state.en_passant_square = old_ep
    state.hash = old_hash
    state.is_white = not state.is_white
    state.last_moved_piece_sq = old_last_moved

def make_move(state: State, move: int):
    old_hash = state.hash
    old_castling = state.castling_rights
    old_ep = state.en_passant_square
    old_halfmove = state.halfmove_clock
    
    old_mg = state.mg_score
    old_eg = state.eg_score
    old_phase = state.phase
    
    # save incremental eval state
    old_w_passed = state.white_passed_pawns
    old_b_passed = state.black_passed_pawns
    old_last_moved = state.last_moved_piece_sq
    
    bitboards = state.bitboards
    board = state.board

    start_sq = move & MASK_SOURCE
    target_sq = (move >> SHIFT_TARGET) & MASK_SOURCE
    
    moving_piece = board[start_sq]
    
    if state.is_white:
        active_bb = WHITE
        opponent_bb = BLACK
        ep_offset = SOUTH
        enemy_pawn = BP
    else:
        active_bb = BLACK
        opponent_bb = WHITE
        ep_offset = NORTH
        enemy_pawn = WP
        
    start_mask = SQUARE_TO_BB[start_sq]
    target_mask = SQUARE_TO_BB[target_sq]
    
    state.mg_score -= MG_TABLE[moving_piece][start_sq]
    state.eg_score -= EG_TABLE[moving_piece][start_sq]
    
    bitboards[moving_piece] &= ~start_mask
    bitboards[active_bb] &= ~start_mask
    state.hash ^= ZOBRIST_KEYS.pieces[moving_piece][start_sq]
    board[start_sq] = NULL
    
    captured_piece = NULL

    if move & CAPTURE_FLAG:
        if (move >> SHIFT_FLAG) == EP_FLAG >> SHIFT_FLAG: 
            capture_sq = target_sq + ep_offset
            captured_piece = enemy_pawn
            cap_mask = SQUARE_TO_BB[capture_sq]
            
            bitboards[captured_piece] &= ~cap_mask
            bitboards[opponent_bb] &= ~cap_mask
            state.hash ^= ZOBRIST_KEYS.pieces[captured_piece][capture_sq]
            board[capture_sq] = NULL
            
            state.mg_score -= MG_TABLE[captured_piece][capture_sq]
            state.eg_score -= EG_TABLE[captured_piece][capture_sq]
            state.phase -= PHASE_WEIGHTS[captured_piece]

            state.piece_counts[captured_piece] -= 1
            
            # update passed pawn tracking if pawn captured
            if not state.is_white:
                state.white_passed_pawns &= ~cap_mask
            else:
                state.black_passed_pawns &= ~cap_mask
        else:
            captured_piece = board[target_sq]
            
            bitboards[captured_piece] &= ~target_mask
            bitboards[opponent_bb] &= ~target_mask
            state.hash ^= ZOBRIST_KEYS.pieces[captured_piece][target_sq]
            
            state.mg_score -= MG_TABLE[captured_piece][target_sq]
            state.eg_score -= EG_TABLE[captured_piece][target_sq]
            state.phase -= PHASE_WEIGHTS[captured_piece]
            
            state.piece_counts[captured_piece] -= 1
            
            # update passed pawn tracking if pawn captured
            captured_type = captured_piece & ~WHITE
            if captured_type == PAWN:
                if captured_piece & WHITE:
                    state.white_passed_pawns &= ~target_mask
                else:
                    state.black_passed_pawns &= ~target_mask
            
    if move & PROMO_FLAG:
        promo_idx = (move >> SHIFT_FLAG) & (SPECIAL_1 | SPECIAL_0)
        promo_types = (KNIGHT, BISHOP, ROOK, QUEEN)
        promo_piece_type = promo_types[promo_idx]
        
        promoted_piece = (moving_piece & WHITE) | promo_piece_type
        state.phase -= PHASE_WEIGHTS[moving_piece]
        state.phase += PHASE_WEIGHTS[promoted_piece]
        target_piece = promoted_piece
        
        state.piece_counts[moving_piece] -= 1
        state.piece_counts[promoted_piece] += 1
        
        # remove promoted pawn from passed pawn tracking
        if state.is_white:
            state.white_passed_pawns &= ~start_mask
        else:
            state.black_passed_pawns &= ~start_mask
    else:
        target_piece = moving_piece
        
    state.mg_score += MG_TABLE[target_piece][target_sq]
    state.eg_score += EG_TABLE[target_piece][target_sq]
    
    bitboards[target_piece] |= target_mask
    bitboards[active_bb] |= target_mask
    state.hash ^= ZOBRIST_KEYS.pieces[target_piece][target_sq]
    board[target_sq] = target_piece
    
    # update passed pawn tracking if pawn moved
    piece_type = moving_piece & ~WHITE
    if piece_type == PAWN and not (move & PROMO_FLAG):
        if state.is_white:
            state.white_passed_pawns &= ~start_mask
            state.white_passed_pawns |= target_mask
        else:
            state.black_passed_pawns &= ~start_mask
            state.black_passed_pawns |= target_mask
    
    flag_shifted = move >> SHIFT_FLAG
    if flag_shifted == CASTLE_KS_FLAG >> SHIFT_FLAG or flag_shifted == CASTLE_QS_FLAG >> SHIFT_FLAG:
        rook = WR if state.is_white else BR
        r_from, r_to = 0, 0
        
        if target_sq == G1: r_from, r_to = H1, F1
        elif target_sq == C1: r_from, r_to = A1, D1
        elif target_sq == G8: r_from, r_to = H8, F8
        elif target_sq == C8: r_from, r_to = A8, D8
        
        bitboards[rook] &= ~SQUARE_TO_BB[r_from]
        bitboards[rook] |= SQUARE_TO_BB[r_to]
        bitboards[active_bb] &= ~SQUARE_TO_BB[r_from]
        bitboards[active_bb] |= SQUARE_TO_BB[r_to]
        
        state.hash ^= ZOBRIST_KEYS.pieces[rook][r_from]
        state.hash ^= ZOBRIST_KEYS.pieces[rook][r_to]
        
        board[r_from] = NULL
        board[r_to] = rook
        
        state.mg_score -= MG_TABLE[rook][r_from]
        state.eg_score -= EG_TABLE[rook][r_from]
        state.mg_score += MG_TABLE[rook][r_to]
        state.eg_score += EG_TABLE[rook][r_to]

    state.hash ^= ZOBRIST_KEYS.castling[state.castling_rights]
    
    # castling rights update
    if start_sq == A1 or target_sq == A1: state.castling_rights &= ~CASTLE_WQ
    if start_sq == H1 or target_sq == H1: state.castling_rights &= ~CASTLE_WK
    if start_sq == A8 or target_sq == A8: state.castling_rights &= ~CASTLE_BQ
    if start_sq == H8 or target_sq == H8: state.castling_rights &= ~CASTLE_BK
    if start_sq == E1: state.castling_rights &= ~(CASTLE_WK | CASTLE_WQ)
    if start_sq == E8: state.castling_rights &= ~(CASTLE_BK | CASTLE_BQ)
    
    state.hash ^= ZOBRIST_KEYS.castling[state.castling_rights]
    
    ep_key = old_ep % 8 if old_ep != NULL else 8
    state.hash ^= ZOBRIST_KEYS.en_passant[ep_key]
    
    state.en_passant_square = NULL
    
    if piece_type == PAWN and abs(start_sq - target_sq) == NORTH + NORTH:
        state.en_passant_square = (start_sq + target_sq) // 2
        
    ep_key = state.en_passant_square % 8 if state.en_passant_square != NULL else 8
    state.hash ^= ZOBRIST_KEYS.en_passant[ep_key]
    
    if piece_type == PAWN or (move & CAPTURE_FLAG): state.halfmove_clock = 0
    else: state.halfmove_clock += 1
        
    if not state.is_white: state.fullmove_number += 1
    
    # track last moved piece for repetition penalty
    state.last_moved_piece_sq = target_sq
        
    state.is_white = not state.is_white
    state.hash ^= ZOBRIST_KEYS.black_to_move
    
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
        old_last_moved
    ))

def unmake_move(state: State, move: int):
    undo_info = state.context_stack.pop()
    captured_piece, old_castling, old_ep, old_halfmove, old_hash, old_mg, old_eg, old_phase, old_w_passed, old_b_passed, old_last_moved = undo_info
    
    if old_hash is None: return

    bitboards = state.bitboards
    board = state.board
    
    start_sq = move & MASK_SOURCE
    target_sq = (move >> SHIFT_TARGET) & MASK_SOURCE
    
    state.history.pop()
    state.hash = old_hash
    state.castling_rights = old_castling
    state.en_passant_square = old_ep
    state.halfmove_clock = old_halfmove
    state.is_white = not state.is_white
    
    state.mg_score = old_mg
    state.eg_score = old_eg
    state.phase = old_phase
    
    # restore incremental eval state
    state.white_passed_pawns = old_w_passed
    state.black_passed_pawns = old_b_passed
    state.last_moved_piece_sq = old_last_moved
    
    if not state.is_white: state.fullmove_number -= 1
        
    if state.is_white:
        active_bb = WHITE
        opponent_bb = BLACK
    else:
        active_bb = BLACK
        opponent_bb = WHITE
        
    start_mask = SQUARE_TO_BB[start_sq]
    target_mask = SQUARE_TO_BB[target_sq]
    
    target_piece = board[target_sq]
    
    if move & PROMO_FLAG:
        bitboards[target_piece] &= ~target_mask
        bitboards[active_bb] &= ~target_mask
        board[target_sq] = NULL
        
        pawn = WP if state.is_white else BP
        bitboards[pawn] |= start_mask
        bitboards[active_bb] |= start_mask
        board[start_sq] = pawn

        state.piece_counts[target_piece] -= 1
        state.piece_counts[pawn] += 1
    else:
        bitboards[target_piece] &= ~target_mask
        bitboards[target_piece] |= start_mask
        bitboards[active_bb] &= ~target_mask
        bitboards[active_bb] |= start_mask
        
        board[target_sq] = NULL
        board[start_sq] = target_piece
        
        flag_shifted = move >> SHIFT_FLAG
        if flag_shifted == CASTLE_KS_FLAG >> SHIFT_FLAG or flag_shifted == CASTLE_QS_FLAG >> SHIFT_FLAG:
            rook = WR if state.is_white else BR
            r_from, r_to = 0, 0
            if target_sq == G1: r_from, r_to = H1, F1
            elif target_sq == C1: r_from, r_to = A1, D1
            elif target_sq == G8: r_from, r_to = H8, F8
            elif target_sq == C8: r_from, r_to = A8, D8
            
            bitboards[rook] &= ~SQUARE_TO_BB[r_to]
            bitboards[rook] |= SQUARE_TO_BB[r_from]
            bitboards[active_bb] &= ~SQUARE_TO_BB[r_to]
            bitboards[active_bb] |= SQUARE_TO_BB[r_from]
            
            board[r_to] = NULL
            board[r_from] = rook

    if captured_piece != NULL:
        state.piece_counts[captured_piece] += 1
        
        if (move >> SHIFT_FLAG) == EP_FLAG >> SHIFT_FLAG:
            ep_offset = SOUTH if state.is_white else NORTH
            capture_sq = target_sq + ep_offset
            bitboards[captured_piece] |= SQUARE_TO_BB[capture_sq]
            bitboards[opponent_bb] |= SQUARE_TO_BB[capture_sq]
            board[capture_sq] = captured_piece
        else:
            bitboards[captured_piece] |= target_mask
            bitboards[opponent_bb] |= target_mask
            board[target_sq] = captured_piece
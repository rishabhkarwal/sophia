from engine.board.state import State
from engine.core.move import (
    CAPTURE_FLAG, PROMO_FLAG, EP_FLAG, CASTLE_KS_FLAG, CASTLE_QS_FLAG,
    SHIFT_TARGET, SHIFT_FLAG, SPECIAL_1, SPECIAL_0
)
from engine.core.constants import (
    WHITE, BLACK, NULL, PAWN, KNIGHT, BISHOP, ROOK, QUEEN,
    CASTLE_WK, CASTLE_WQ, CASTLE_BK, CASTLE_BQ,
    A1, H1, A8, H8, E1, C1, G1, E8, C8, G8, F1, D1, F8, D8,
    MASK_SOURCE,
    WP, BP, WR, BR,
    WHITE, BLACK,
    NORTH, SOUTH, SQUARE_TO_BB
)
from engine.core.zobrist import ZOBRIST_KEYS
from engine.search.evaluation import MG_TABLE, EG_TABLE, PHASE_WEIGHTS

def is_threefold_repetition(state: State) -> bool:
    if not state.history: return False
    current_hash = state.hash
    count = 0
    for i in range(len(state.history) - 2, -1, -2):
        if state.history[i] == current_hash:
            count += 1
            if count >= 2: # found 2 previous + 1 current = 3
                return True
    return False

def make_null_move(state: State):
    old_ep = state.en_passant_square
    old_hash = state.hash
    
    ep_key = old_ep % 8 if old_ep != NULL else 8
    state.hash ^= ZOBRIST_KEYS.en_passant[ep_key]
    state.en_passant_square = NULL
    state.hash ^= ZOBRIST_KEYS.en_passant[8]
    
    state.is_white = not state.is_white
    state.hash ^= ZOBRIST_KEYS.black_to_move
    
    return (old_ep, old_hash)

def unmake_null_move(state: State, undo_info):
    old_ep, old_hash = undo_info
    state.en_passant_square = old_ep
    state.hash = old_hash
    state.is_white = not state.is_white

def make_move(state: State, move: int) -> tuple:
    start_sq = move & MASK_SOURCE
    target_sq = (move >> SHIFT_TARGET) & MASK_SOURCE
    
    old_hash = state.hash
    old_castling = state.castling_rights
    old_ep = state.en_passant_square
    old_halfmove = state.halfmove_clock
    
    old_mg = state.mg_score
    old_eg = state.eg_score
    old_phase = state.phase
    
    bitboards = state.bitboards
    board = state.board
    
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
        
    start_mask = 1 << start_sq
    target_mask = 1 << target_sq
    
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
            cap_mask = 1 << capture_sq
            
            bitboards[captured_piece] &= ~cap_mask
            bitboards[opponent_bb] &= ~cap_mask
            state.hash ^= ZOBRIST_KEYS.pieces[captured_piece][capture_sq]
            board[capture_sq] = NULL
            
            state.mg_score -= MG_TABLE[captured_piece][capture_sq]
            state.eg_score -= EG_TABLE[captured_piece][capture_sq]
            state.phase -= PHASE_WEIGHTS[captured_piece]

            state.piece_counts[captured_piece] -= 1
        else:
            captured_piece = board[target_sq]
            
            bitboards[captured_piece] &= ~target_mask
            bitboards[opponent_bb] &= ~target_mask
            state.hash ^= ZOBRIST_KEYS.pieces[captured_piece][target_sq]
            
            state.mg_score -= MG_TABLE[captured_piece][target_sq]
            state.eg_score -= EG_TABLE[captured_piece][target_sq]
            state.phase -= PHASE_WEIGHTS[captured_piece]
            
            state.piece_counts[captured_piece] -= 1
            
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
    else:
        target_piece = moving_piece
        
    state.mg_score += MG_TABLE[target_piece][target_sq]
    state.eg_score += EG_TABLE[target_piece][target_sq]
    
    bitboards[target_piece] |= target_mask
    bitboards[active_bb] |= target_mask
    state.hash ^= ZOBRIST_KEYS.pieces[target_piece][target_sq]
    board[target_sq] = target_piece
    
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
    
    if start_sq == A1 or target_sq == A1: state.castling_rights &= ~CASTLE_WQ
    if start_sq == H1 or target_sq == H1: state.castling_rights &= ~CASTLE_WK
    if start_sq == A8 or target_sq == A8: state.castling_rights &= ~CASTLE_BQ
    if start_sq == H8 or target_sq == H8: state.castling_rights &= ~CASTLE_BK
    if start_sq == E1 or target_sq == E1: state.castling_rights &= ~(CASTLE_WK | CASTLE_WQ)
    if start_sq == E8 or target_sq == E8: state.castling_rights &= ~(CASTLE_BK | CASTLE_BQ)
    
    state.hash ^= ZOBRIST_KEYS.castling[state.castling_rights]
    
    ep_key = old_ep % 8 if old_ep != NULL else 8
    state.hash ^= ZOBRIST_KEYS.en_passant[ep_key]
    
    state.en_passant_square = NULL
    
    piece_type = moving_piece & ~WHITE
    if piece_type == PAWN and abs(start_sq - target_sq) == NORTH + NORTH:
        state.en_passant_square = (start_sq + target_sq) // 2
        
    ep_key = state.en_passant_square % 8 if state.en_passant_square != NULL else 8
    state.hash ^= ZOBRIST_KEYS.en_passant[ep_key]
    
    if piece_type == PAWN or (move & CAPTURE_FLAG): state.halfmove_clock = 0
    else: state.halfmove_clock += 1
        
    if not state.is_white: state.fullmove_number += 1
        
    state.is_white = not state.is_white
    state.hash ^= ZOBRIST_KEYS.black_to_move
    
    state.history.append(old_hash)
    
    return (captured_piece, old_castling, old_ep, old_halfmove, old_hash, old_mg, old_eg, old_phase)

def unmake_move(state: State, move: int, undo_info: tuple):
    captured_piece, old_castling, old_ep, old_halfmove, old_hash, old_mg, old_eg, old_phase = undo_info
    
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
    
    if not state.is_white: state.fullmove_number -= 1
        
    if state.is_white:
        active_bb = WHITE
        opponent_bb = BLACK
    else:
        active_bb = BLACK
        opponent_bb = WHITE
        
    start_mask = 1 << start_sq
    target_mask = 1 << target_sq
    
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
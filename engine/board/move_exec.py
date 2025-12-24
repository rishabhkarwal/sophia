from engine.board.state import State
from engine.core.move import (
    is_capture, is_en_passant, is_promotion, is_castle,
    get_flag, get_promo_piece
)
from engine.core.constants import (
    WHITE, BLACK, NO_SQUARE,
    CASTLE_WK, CASTLE_WQ, CASTLE_BK, CASTLE_BQ,
    WHITE_PIECES, BLACK_PIECES,
    A1, H1, A8, H8, E1, C1, G1, E8, C8, G8, F1, D1, F8, D8,
    MASK_SOURCE, MASK_TARGET,
    WK, BK, WR, BR, WP, BP,
    WHITE_STR, BLACK_STR, ALL_STR,
    NORTH, SOUTH
)
from engine.core.zobrist import ZOBRIST_KEYS, KEY_CASTLING, KEY_EP, KEY_BLACK_TO_MOVE
from engine.search.evaluation import PIECE_INDICES, MG_TABLE, EG_TABLE, PHASE_WEIGHTS

def is_threefold_repetition(state: State) -> bool:
    if not state.history: return False
    current_hash = state.hash
    for i in range(len(state.history) - 2, -1, -2):
        if state.history[i] == current_hash: return True
    return False

def make_null_move(state: State):
    old_ep = state.en_passant_square
    old_hash = state.hash
    state.hash ^= ZOBRIST_KEYS[KEY_EP][old_ep % 8 if old_ep != NO_SQUARE else 8]
    state.en_passant_square = NO_SQUARE
    state.hash ^= ZOBRIST_KEYS[KEY_EP][8]
    state.is_white = not state.is_white
    state.hash ^= ZOBRIST_KEYS[KEY_BLACK_TO_MOVE]
    return (old_ep, old_hash)

def unmake_null_move(state: State, undo_info):
    old_ep, old_hash = undo_info
    state.en_passant_square = old_ep
    state.hash = old_hash
    state.is_white = not state.is_white

def make_move(state: State, move: int) -> tuple:
    start_sq = move & MASK_SOURCE
    target_sq = (move >> 6) & MASK_SOURCE
    flag = get_flag(move)
    
    old_hash = state.hash
    old_castling = state.castling_rights
    old_ep = state.en_passant_square
    old_halfmove = state.halfmove_clock
    
    # store old scores for undo
    old_mg = state.mg_score
    old_eg = state.eg_score
    old_phase = state.phase

    captured_piece = None
    bitboards = state.bitboards
    
    if state.is_white:
        active_pieces = WHITE_PIECES
        opponent_pieces = BLACK_PIECES
        active_colour = WHITE_STR
        opponent_colour = BLACK_STR
        ep_offset = SOUTH
        my_pawn = WP
        enemy_pawn = BP
    else:
        active_pieces = BLACK_PIECES
        opponent_pieces = WHITE_PIECES
        active_colour = BLACK_STR
        opponent_colour = WHITE_STR
        ep_offset = NORTH
        my_pawn = BP
        enemy_pawn = WP
    
    start_mask = 1 << start_sq
    target_mask = 1 << target_sq
    
    moving_piece = None
    for piece in active_pieces:
        if bitboards[piece] & start_mask:
            moving_piece = piece
            break
            
    # if piece not found, return dummy data to prevent crash
    if moving_piece is None: return (None, old_castling, old_ep, old_halfmove, None, 0, 0, 0)

    # remove moving piece from score
    pt_idx = PIECE_INDICES[moving_piece]
    state.mg_score -= MG_TABLE[pt_idx][start_sq]
    state.eg_score -= EG_TABLE[pt_idx][start_sq]

    bitboards[moving_piece] &= ~start_mask
    bitboards[active_colour] &= ~start_mask
    state.hash ^= ZOBRIST_KEYS[moving_piece][start_sq]

    if is_capture(move):
        if is_en_passant(move):
            capture_sq = target_sq + ep_offset
            captured_piece = enemy_pawn
            cap_mask = 1 << capture_sq
            
            bitboards[captured_piece] &= ~cap_mask
            bitboards[opponent_colour] &= ~cap_mask
            state.hash ^= ZOBRIST_KEYS[captured_piece][capture_sq]
            
            # remove captured piece score (EP)
            cap_idx = PIECE_INDICES[captured_piece]
            state.mg_score -= MG_TABLE[cap_idx][capture_sq]
            state.eg_score -= EG_TABLE[cap_idx][capture_sq]
            state.phase -= PHASE_WEIGHTS[cap_idx]
            
        else:
            for piece in opponent_pieces:
                if bitboards[piece] & target_mask:
                    captured_piece = piece
                    bitboards[piece] &= ~target_mask
                    bitboards[opponent_colour] &= ~target_mask
                    state.hash ^= ZOBRIST_KEYS[piece][target_sq]
                    
                    # remove captured piece score
                    cap_idx = PIECE_INDICES[captured_piece]
                    state.mg_score -= MG_TABLE[cap_idx][target_sq]
                    state.eg_score -= EG_TABLE[cap_idx][target_sq]
                    state.phase -= PHASE_WEIGHTS[cap_idx]
                    break

    if is_promotion(move):
        promo_char = get_promo_piece(move)
        target_piece = promo_char.upper() if state.is_white else promo_char.lower()
        
        # promotion phase update
        state.phase -= PHASE_WEIGHTS[pt_idx] # remove pawn
        pt_idx = PIECE_INDICES[target_piece] # switch index to new piece
        state.phase += PHASE_WEIGHTS[pt_idx] # add new piece
        
    else:
        target_piece = moving_piece
    
    # add piece score at target
    state.mg_score += MG_TABLE[pt_idx][target_sq]
    state.eg_score += EG_TABLE[pt_idx][target_sq]

    bitboards[target_piece] |= target_mask
    bitboards[active_colour] |= target_mask
    state.hash ^= ZOBRIST_KEYS[target_piece][target_sq]
    
    if is_castle(move):
        rook_key = WR if state.is_white else BR
        r_from, r_to = 0, 0
        
        if target_sq == G1: r_from, r_to = H1, F1
        elif target_sq == C1: r_from, r_to = A1, D1
        elif target_sq == G8: r_from, r_to = H8, F8
        elif target_sq == C8: r_from, r_to = A8, D8
        
        bitboards[rook_key] &= ~(1 << r_from)
        bitboards[rook_key] |= (1 << r_to)
        bitboards[active_colour] &= ~(1 << r_from)
        bitboards[active_colour] |= (1 << r_to)
        
        state.hash ^= ZOBRIST_KEYS[rook_key][r_from]
        state.hash ^= ZOBRIST_KEYS[rook_key][r_to]
        
        # update rook score
        r_idx = PIECE_INDICES[rook_key]
        state.mg_score -= MG_TABLE[r_idx][r_from]
        state.eg_score -= EG_TABLE[r_idx][r_from]
        state.mg_score += MG_TABLE[r_idx][r_to]
        state.eg_score += EG_TABLE[r_idx][r_to]
        
    state.hash ^= ZOBRIST_KEYS[KEY_CASTLING][state.castling_rights]
    
    if moving_piece == WK: state.castling_rights &= ~(CASTLE_WK | CASTLE_WQ)
    elif moving_piece == BK: state.castling_rights &= ~(CASTLE_BK | CASTLE_BQ)
    
    if start_sq == A1 or target_sq == A1: state.castling_rights &= ~CASTLE_WQ
    if start_sq == H1 or target_sq == H1: state.castling_rights &= ~CASTLE_WK
    if start_sq == A8 or target_sq == A8: state.castling_rights &= ~CASTLE_BQ
    if start_sq == H8 or target_sq == H8: state.castling_rights &= ~CASTLE_BK

    state.hash ^= ZOBRIST_KEYS[KEY_CASTLING][state.castling_rights]

    state.hash ^= ZOBRIST_KEYS[KEY_EP][state.en_passant_square % 8 if state.en_passant_square != NO_SQUARE else 8]
    state.en_passant_square = NO_SQUARE
    
    is_pawn = moving_piece.upper() == WP
    if is_pawn and abs(start_sq - target_sq) == 16:
        state.en_passant_square = (start_sq + target_sq) // 2
        
    state.hash ^= ZOBRIST_KEYS[KEY_EP][state.en_passant_square % 8 if state.en_passant_square != NO_SQUARE else 8]

    if is_pawn or is_capture(move):
        state.halfmove_clock = 0
    else:
        state.halfmove_clock += 1
    
    if not state.is_white:
        state.fullmove_number += 1
    
    state.is_white = not state.is_white
    state.hash ^= ZOBRIST_KEYS[KEY_BLACK_TO_MOVE]
    
    bitboards[ALL_STR] = bitboards[WHITE_STR] | bitboards[BLACK_STR]
    state.history.append(old_hash)
    
    return (captured_piece, old_castling, old_ep, old_halfmove, old_hash, old_mg, old_eg, old_phase)

def unmake_move(state: State, move: int, undo_info: tuple):
    captured_piece, old_castling, old_ep, old_halfmove, old_hash, old_mg, old_eg, old_phase = undo_info
    
    if old_hash is None: return

    bitboards = state.bitboards
    
    start_sq = move & MASK_SOURCE
    target_sq = (move >> 6) & MASK_SOURCE
    flag = get_flag(move)
    
    state.history.pop()
    state.hash = old_hash
    state.castling_rights = old_castling
    state.en_passant_square = old_ep
    state.halfmove_clock = old_halfmove
    state.is_white = not state.is_white
    
    # restore scores
    state.mg_score = old_mg
    state.eg_score = old_eg
    state.phase = old_phase

    if not state.is_white:
        state.fullmove_number -= 1
    
    if state.is_white:
        active_colour, active_pieces = WHITE_STR, WHITE_PIECES
        opponent_colour = BLACK_STR
    else:
        active_colour, active_pieces = BLACK_STR, BLACK_PIECES
        opponent_colour = WHITE_STR
    
    start_mask = 1 << start_sq
    target_mask = 1 << target_sq

    if is_promotion(move):
        promo_char = get_promo_piece(move)
        promoted_piece = promo_char.upper() if state.is_white else promo_char.lower()
        bitboards[promoted_piece] &= ~target_mask
        bitboards[active_colour] &= ~target_mask
        
        pawn = WP if state.is_white else BP
        bitboards[pawn] |= start_mask
        bitboards[active_colour] |= start_mask
    else:
        moving_piece = None
        for piece in active_pieces:
            if bitboards[piece] & target_mask:
                moving_piece = piece
                break
        
        if moving_piece:
            bitboards[moving_piece] &= ~target_mask
            bitboards[moving_piece] |= start_mask
            bitboards[active_colour] &= ~target_mask
            bitboards[active_colour] |= start_mask
        
        if is_castle(move):
            rook_key = WR if state.is_white else BR
            r_from, r_to = 0, 0
            if target_sq == G1: r_from, r_to = H1, F1
            elif target_sq == C1: r_from, r_to = A1, D1
            elif target_sq == G8: r_from, r_to = H8, F8
            elif target_sq == C8: r_from, r_to = A8, D8
            
            bitboards[rook_key] &= ~(1 << r_to)
            bitboards[rook_key] |= (1 << r_from)
            bitboards[active_colour] &= ~(1 << r_to)
            bitboards[active_colour] |= (1 << r_from)

    if captured_piece:
        if is_en_passant(move):
            ep_offset = SOUTH if state.is_white else NORTH
            capture_sq = target_sq + ep_offset
            bitboards[captured_piece] |= (1 << capture_sq)
            bitboards[opponent_colour] |= (1 << capture_sq)
        else:
            bitboards[captured_piece] |= target_mask
            bitboards[opponent_colour] |= target_mask
        
    bitboards[ALL_STR] = bitboards[WHITE_STR] | bitboards[BLACK_STR]
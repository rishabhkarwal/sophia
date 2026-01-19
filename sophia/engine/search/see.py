from engine.core.constants import (
    WHITE, BLACK, PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
    PIECE_VALUES, MASK_SOURCE, SQUARE_TO_BB, NULL,
    WP, WN, WB, WR, WQ, WK,
    BP, BN, BB, BR, BQ, BK
)
from engine.core.move import SHIFT_TARGET, EP_FLAG, SHIFT_FLAG
from engine.moves.precomputed import (
    KNIGHT_ATTACKS, KING_ATTACKS,
    BISHOP_TABLE, BISHOP_MASKS,
    ROOK_TABLE, ROOK_MASKS,
    WHITE_PAWN_ATTACKS, BLACK_PAWN_ATTACKS
)

def get_smallest_attacker(state, square, colour, occupied):
    bitboards = state.bitboards
    
    if colour == WHITE:
        pieces = [
            (PAWN, bitboards[WP], PIECE_VALUES[PAWN]),
            (KNIGHT, bitboards[WN], PIECE_VALUES[KNIGHT]),
            (BISHOP, bitboards[WB], PIECE_VALUES[BISHOP]),
            (ROOK, bitboards[WR], PIECE_VALUES[ROOK]),
            (QUEEN, bitboards[WQ], PIECE_VALUES[QUEEN]),
            (KING, bitboards[WK], PIECE_VALUES[KING])
        ]
        pawn_attacks = BLACK_PAWN_ATTACKS[square]
    else:
        pieces = [
            (PAWN, bitboards[BP], PIECE_VALUES[PAWN]),
            (KNIGHT, bitboards[BN], PIECE_VALUES[KNIGHT]),
            (BISHOP, bitboards[BB], PIECE_VALUES[BISHOP]),
            (ROOK, bitboards[BR], PIECE_VALUES[ROOK]),
            (QUEEN, bitboards[BQ], PIECE_VALUES[QUEEN]),
            (KING, bitboards[BK], PIECE_VALUES[KING])
        ]
        pawn_attacks = WHITE_PAWN_ATTACKS[square]
    
    # check each piece type
    for piece_type, piece_bb, piece_value in pieces:
        attackers_bb = 0
        
        if piece_type == PAWN: attackers_bb = pawn_attacks & piece_bb & occupied
        elif piece_type == KNIGHT: attackers_bb = KNIGHT_ATTACKS[square] & piece_bb & occupied
        elif piece_type == KING: attackers_bb = KING_ATTACKS[square] & piece_bb & occupied
        elif piece_type == BISHOP: attackers_bb = BISHOP_TABLE[square][occupied & BISHOP_MASKS[square]] & piece_bb & occupied
        elif piece_type == ROOK: attackers_bb = ROOK_TABLE[square][occupied & ROOK_MASKS[square]] & piece_bb & occupied
        elif piece_type == QUEEN:
            b_att = BISHOP_TABLE[square][occupied & BISHOP_MASKS[square]]
            r_att = ROOK_TABLE[square][occupied & ROOK_MASKS[square]]
            attackers_bb = (b_att | r_att) & piece_bb & occupied
        
        if attackers_bb:
            attacker_sq = (attackers_bb & -attackers_bb).bit_length() - 1
            return attacker_sq, piece_value, piece_type
    
    return None, 0, None

def see_full(state, move):
    """
    static exchange evaluation for a capture move
    returns the net material gain/loss from the capture sequence
    +ve = good for side making the capture
    """
    start_sq = move & MASK_SOURCE
    target_sq = (move >> SHIFT_TARGET) & MASK_SOURCE
    
    attacker = state.board[start_sq]
    victim = state.board[target_sq]
    
    # en passant captures
    flag = (move >> SHIFT_FLAG) & 0xF
    if flag == EP_FLAG:
        victim_type = PAWN
        victim_value = PIECE_VALUES[PAWN]
    elif victim == NULL:
        return 0  # not a capture
    else:
        victim_type = victim & ~WHITE
        victim_value = PIECE_VALUES[victim_type]
    
    attacker_type = attacker & ~WHITE
    attacker_colour = WHITE if (attacker & WHITE) else BLACK
    attacker_value = PIECE_VALUES[attacker_type]
    
    # start with capturing the victim
    gain = [victim_value]
    
    # simulate the capture sequence
    occupied = (state.bitboards[WHITE] | state.bitboards[BLACK]) & ~SQUARE_TO_BB[start_sq]
    current_attacker_value = attacker_value
    side = not attacker_colour # opponent's turn to recapture
    
    # limit exchanges to prevent infinite loops
    for depth in range(1, 10):
        # find next smallest attacker
        next_sq, next_value, next_type = get_smallest_attacker(state, target_sq, side, occupied)
        
        if next_sq is None:
            break  # no more attackers
        
        # record the gain from capturing the previous attacker
        gain.append(-gain[depth - 1] + current_attacker_value)
        
        # remove this attacker from occupied squares
        occupied &= ~SQUARE_TO_BB[next_sq]
        current_attacker_value = next_value
        side = not side
    
    # minimax backwards through the gain array
    for depth in range(len(gain) - 2, -1, -1):
        gain[depth] = max(-gain[depth + 1], gain[depth])
    
    return gain[0]

def see_fast(state, move, threshold=0):
    """Fast SEE check: used for pruning decisions without full SEE calculation"""
    target_sq = (move >> SHIFT_TARGET) & MASK_SOURCE
    victim = state.board[target_sq]
    
    # handle en passant
    flag = (move >> SHIFT_FLAG) & 0xF
    if flag == EP_FLAG:
        victim_value = PIECE_VALUES[PAWN]
    elif victim == NULL:
        return threshold <= 0  # not a capture
    else:
        victim_type = victim & ~WHITE
        victim_value = PIECE_VALUES[victim_type]
    
    # quick heuristic: if victim value >= threshold, likely good
    if victim_value >= threshold:
        return True
    
    # otherwise do full SEE calculation
    return see_full(state, move) >= threshold
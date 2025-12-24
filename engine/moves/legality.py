from engine.core.constants import (
    WHITE, BLACK,
    WHITE_PIECES, BLACK_PIECES,
    MASK_SOURCE,
    WK, BK,
    ALL_STR
)
from engine.board.state import State
from engine.moves.precomputed import (
    KNIGHT_ATTACKS, KING_ATTACKS,
    ROOK_TABLE, ROOK_MASKS,
    BISHOP_TABLE, BISHOP_MASKS,
    WHITE_PAWN_ATTACKS, BLACK_PAWN_ATTACKS
)
from engine.core.move import get_target
from engine.board.move_exec import make_move, unmake_move

def is_square_attacked(state: State, sq: int, colour: bool) -> bool:
    """Check if a square is attacked by a given colour"""
    bitboards = state.bitboards
    all_pieces = bitboards[ALL_STR]
    
    if colour == WHITE:
        P, N, B, R, Q, K = WHITE_PIECES
        if BLACK_PAWN_ATTACKS[sq] & bitboards[P]: return True
    else:
        P, N, B, R, Q, K = BLACK_PIECES
        if WHITE_PAWN_ATTACKS[sq] & bitboards[P]: return True
    
    if KNIGHT_ATTACKS[sq] & bitboards[N]: return True
    if KING_ATTACKS[sq] & bitboards[K]: return True
    
    if BISHOP_TABLE[(sq, all_pieces & BISHOP_MASKS[sq])] & (bitboards[B] | bitboards[Q]): return True
    if ROOK_TABLE[(sq, all_pieces & ROOK_MASKS[sq])] & (bitboards[R] | bitboards[Q]): return True
    return False

def get_attackers(state: State, sq: int, colour: bool) -> int:
    """Get all pieces of 'colour' that attack the given square"""
    attackers = 0
    bitboards = state.bitboards
    all_pieces = bitboards[ALL_STR]
    
    if colour == WHITE:
        P, N, B, R, Q, K = WHITE_PIECES
        pawn_attacks = BLACK_PAWN_ATTACKS[sq]
    else:
        P, N, B, R, Q, K = BLACK_PIECES
        pawn_attacks = WHITE_PAWN_ATTACKS[sq]
    
    if pawn_attacks & bitboards[P]: attackers |= pawn_attacks & bitboards[P]
    if KNIGHT_ATTACKS[sq] & bitboards[N]: attackers |= KNIGHT_ATTACKS[sq] & bitboards[N]
    if KING_ATTACKS[sq] & bitboards[K]: attackers |= KING_ATTACKS[sq] & bitboards[K]
    
    attackers |= BISHOP_TABLE[(sq, all_pieces & BISHOP_MASKS[sq])] & (bitboards[B] | bitboards[Q])
    attackers |= ROOK_TABLE[(sq, all_pieces & ROOK_MASKS[sq])] & (bitboards[R] | bitboards[Q])
    return attackers

def is_in_check(state: State, colour: bool) -> bool:
    king_key = WK if colour == WHITE else BK
    king_bb = state.bitboards[king_key]
    if not king_bb: return False
    king_sq = (king_bb & -king_bb).bit_length() - 1
    return is_square_attacked(state, king_sq, not colour)

def is_legal(state: State, move: int) -> bool:
    start_sq = move & MASK_SOURCE
    target_sq = get_target(move)
    
    if (1 << start_sq) & (state.bitboards[WK] | state.bitboards[BK]):
        opponent = not state.is_white
        state.bitboards[ALL_STR] &= ~(1 << start_sq)
        is_attacked = is_square_attacked(state, target_sq, opponent)
        state.bitboards[ALL_STR] |= (1 << start_sq)
        return not is_attacked

    undo_info = make_move(state, move)
    in_check = is_in_check(state, not state.is_white)
    unmake_move(state, move, undo_info)
    return not in_check
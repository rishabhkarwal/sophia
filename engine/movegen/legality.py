from engine.core.constants import WHITE, BLACK, WHITE_PIECES, BLACK_PIECES
from engine.board.state import State
from engine.movegen.precomputed import (
    KNIGHT_ATTACKS, KING_ATTACKS,
    ROOK_TABLE, ROOK_MASKS,
    BISHOP_TABLE, BISHOP_MASKS,
    WHITE_PAWN_ATTACKS, BLACK_PAWN_ATTACKS
)
from engine.core.bitboard_utils import BitBoard
from engine.board.move_exec import make_move

def is_square_attacked(state: State, sq: int, colour: int) -> bool:
    """Check if a square is attacked by a given colour"""
    all_pieces = state.bitboards["all"]
    
    if colour == WHITE:
        P, N, B, R, Q, K = WHITE_PIECES
        pawn_attacks = BLACK_PAWN_ATTACKS[sq]
    else:
        P, N, B, R, Q, K = BLACK_PIECES
        pawn_attacks = WHITE_PAWN_ATTACKS[sq]
    
    if pawn_attacks & state.bitboards.get(P, 0): return True
    if KNIGHT_ATTACKS[sq] & state.bitboards.get(N, 0): return True
    if KING_ATTACKS[sq] & state.bitboards.get(K, 0): return True
    
    # check diagonal sliders
    b_mask = BISHOP_MASKS[sq]
    b_attacks = BISHOP_TABLE[(sq, all_pieces & b_mask)]
    if b_attacks & (state.bitboards.get(B, 0) | state.bitboards.get(Q, 0)): return True
    
    # check orthogonal sliders
    r_mask = ROOK_MASKS[sq]
    r_attacks = ROOK_TABLE[(sq, all_pieces & r_mask)]
    if r_attacks & (state.bitboards.get(R, 0) | state.bitboards.get(Q, 0)): return True
    
    return False

def get_attackers(state: State, sq: int, colour: int) -> int:
    """Get all pieces of 'colour' that attack the given square"""
    attackers = 0
    all_pieces = state.bitboards["all"]
    
    if colour == WHITE:
        P, N, B, R, Q, K = WHITE_PIECES
        pawn_attacks = BLACK_PAWN_ATTACKS[sq]
    else:
        P, N, B, R, Q, K = BLACK_PIECES
        pawn_attacks = WHITE_PAWN_ATTACKS[sq]
    
    if pawn_attacks & state.bitboards.get(P, 0):
        attackers |= pawn_attacks & state.bitboards[P]
    
    if KNIGHT_ATTACKS[sq] & state.bitboards.get(N, 0):
        attackers |= KNIGHT_ATTACKS[sq] & state.bitboards[N]
    
    if KING_ATTACKS[sq] & state.bitboards.get(K, 0):
        attackers |= KING_ATTACKS[sq] & state.bitboards[K]
    
    b_mask = BISHOP_MASKS[sq]
    b_pattern = all_pieces & b_mask
    b_attacks = BISHOP_TABLE[(sq, b_pattern)]
    bishops_queens = state.bitboards.get(B, 0) | state.bitboards.get(Q, 0)
    if b_attacks & bishops_queens:
        attackers |= b_attacks & bishops_queens
    
    r_mask = ROOK_MASKS[sq]
    r_pattern = all_pieces & r_mask
    r_attacks = ROOK_TABLE[(sq, r_pattern)]
    rooks_queens = state.bitboards.get(R, 0) | state.bitboards.get(Q, 0)
    if r_attacks & rooks_queens:
        attackers |= r_attacks & rooks_queens
    
    return attackers

def is_in_check(state: State, colour: int) -> bool:
    """Check if the king of the specified colour is under attack"""
    king_key = 'K' if colour == WHITE else 'k'
    king_bb = state.bitboards.get(king_key, 0)
    if not king_bb: return False
    king_sq = next(BitBoard.bit_scan(king_bb))
    attacker_colour = BLACK if colour == WHITE else WHITE
    return is_square_attacked(state, king_sq, attacker_colour)

def is_legal(state: State, move) -> bool:
    """Check if a move is legal"""
    new_state = make_move(state, move)
    return not is_in_check(new_state, state.player)
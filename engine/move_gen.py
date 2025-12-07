"""Move generation module for pseudo-legal moves."""
from typing import List, Dict

from .constants import (
    WHITE, BLACK,
    CASTLE_WK, CASTLE_WQ, CASTLE_BK, CASTLE_BQ,
    A8, H1,
    E1, F1, G1, C1, D1, B1,
    E8, F8, G8, C8, D8, B8,
    RANK_3, RANK_6,
    WHITE_PIECES, BLACK_PIECES
)
from .state import State
from .move import Move, QUIET, CAPTURE, EP_CAPTURE, CASTLE, PROMOTION
from .precomputed import (
    KNIGHT_ATTACKS, KING_ATTACKS,
    ROOK_TABLE, ROOK_MASKS,
    BISHOP_TABLE, BISHOP_MASKS,
    WHITE_PAWN_ATTACKS, BLACK_PAWN_ATTACKS
)
from .utils import BitBoard

def generate_moves(state: State, captures_only=False) -> List[Move]:
    """Generate all pseudo-legal moves for the current position"""
    moves: List[Move] = []
    
    all_pieces = state.bitboards["all"]
    
    # determine active and opponent pieces
    if state.player == WHITE:
        active = state.bitboards["white"]
        opponent = state.bitboards["black"]
        P, N, B, R, Q, K = WHITE_PIECES
        pawn_attacks = WHITE_PAWN_ATTACKS
    else:
        active = state.bitboards["black"]
        opponent = state.bitboards["white"]
        P, N, B, R, Q, K = BLACK_PIECES
        pawn_attacks = BLACK_PAWN_ATTACKS

    # generate moves for each piece type
    _gen_pawn_moves(state, moves, P, state.player, all_pieces, opponent, pawn_attacks, captures_only)
    _gen_knight_moves(state.bitboards[N], moves, active, opponent, captures_only)
    _gen_king_moves(state.bitboards[K], moves, active, opponent, captures_only)
    # castling is never a capture
    if not captures_only: _gen_castling_moves(state, moves, all_pieces)
    _gen_bishop_moves(state.bitboards[B], moves, all_pieces, active, opponent, captures_only)
    _gen_rook_moves(state.bitboards[R], moves, all_pieces, active, opponent, captures_only)
    _gen_queen_moves(state.bitboards[Q], moves, all_pieces, active, opponent, captures_only)
    
    return moves

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
    
    # pawn attacks
    if pawn_attacks & state.bitboards.get(P, 0):
        attackers |= pawn_attacks & state.bitboards[P]
    
    # knight attacks
    if KNIGHT_ATTACKS[sq] & state.bitboards.get(N, 0):
        attackers |= KNIGHT_ATTACKS[sq] & state.bitboards[N]
    
    # king attacks
    if KING_ATTACKS[sq] & state.bitboards.get(K, 0):
        attackers |= KING_ATTACKS[sq] & state.bitboards[K]
    
    # diagonal sliders (bishops and queens)
    b_mask = BISHOP_MASKS[sq]
    b_pattern = all_pieces & b_mask
    b_attacks = BISHOP_TABLE[(sq, b_pattern)]
    bishops_queens = state.bitboards.get(B, 0) | state.bitboards.get(Q, 0)
    if b_attacks & bishops_queens:
        attackers |= b_attacks & bishops_queens
    
    # orthogonal sliders (rooks and queens)
    r_mask = ROOK_MASKS[sq]
    r_pattern = all_pieces & r_mask
    r_attacks = ROOK_TABLE[(sq, r_pattern)]
    rooks_queens = state.bitboards.get(R, 0) | state.bitboards.get(Q, 0)
    if r_attacks & rooks_queens:
        attackers |= r_attacks & rooks_queens
    
    return attackers

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

def _gen_pawn_moves(state: State, moves: List[Move], pawn_key: str, colour: int, all_pieces: int, enemy: int, attack_table: List[int], captures_only: bool):
    """Generate pawn moves including pushes, captures, en passant and promotions"""
    pawns = state.bitboards[pawn_key]
    
    if colour == WHITE:
        direction = 8
        start_rank_mask = RANK_3 # after single push from rank 2
        promotion_rank = A8 # first square of rank 8
        
        # single pushes (move up one rank)
        single_push = (pawns << 8) & ~all_pieces
        
        # double pushes (from rank 2 to rank 4, must pass through rank 3)
        double_push = ((single_push & start_rank_mask) << 8) & ~all_pieces

    else:
        direction = -8
        start_rank_mask = RANK_6 # after single push from rank 7
        promotion_rank = H1 # last square of rank 1
        
        # single pushes (move down one rank)
        single_push = (pawns >> 8) & ~all_pieces
        
        # double pushes (from rank 7 to rank 5, must pass through rank 6)
        double_push = ((single_push & start_rank_mask) >> 8) & ~all_pieces
    
    # process single pushes - SKIP IF CAPTURES ONLY
    if not captures_only:
        for to_sq in BitBoard.bit_scan(single_push):
            from_sq = to_sq - direction
            # check for promotion
            if (colour == WHITE and to_sq >= promotion_rank) or (colour == BLACK and to_sq <= promotion_rank):
                _add_promotions(moves, from_sq, to_sq, QUIET)
            else:
                moves.append(Move(from_sq, to_sq, QUIET))
        
        # process double pushes - SKIP IF CAPTURES ONLY
        for to_sq in BitBoard.bit_scan(double_push):
            from_sq = to_sq - (2 * direction)
            moves.append(Move(from_sq, to_sq, QUIET))
    
    # process captures
    for from_sq in BitBoard.bit_scan(pawns):
        # normal diagonal captures
        attacks = attack_table[from_sq] & enemy
        
        for to_sq in BitBoard.bit_scan(attacks):
            # check for promotion
            if (colour == WHITE and to_sq >= promotion_rank) or (colour == BLACK and to_sq <= promotion_rank):
                _add_promotions(moves, from_sq, to_sq, CAPTURE)
            else:
                moves.append(Move(from_sq, to_sq, CAPTURE))
        
        # en passant capture
        if state.en_passant != -1:
            if attack_table[from_sq] & (1 << state.en_passant):
                moves.append(Move(from_sq, state.en_passant, EP_CAPTURE | CAPTURE))

def _add_promotions(moves: List[Move], from_sq: int, to_sq: int, base_flag: int):
    """Add all four promotion moves"""
    flag = base_flag | PROMOTION
    moves.append(Move(from_sq, to_sq, flag, promo_type='q'))
    moves.append(Move(from_sq, to_sq, flag, promo_type='r'))
    moves.append(Move(from_sq, to_sq, flag, promo_type='b'))
    moves.append(Move(from_sq, to_sq, flag, promo_type='n'))

def _gen_knight_moves(pieces: int, moves: List[Move], active: int, enemy: int, captures_only: bool):
    """Generate knight moves using precomputed attack table"""
    for from_sq in BitBoard.bit_scan(pieces):
        targets = KNIGHT_ATTACKS[from_sq] & ~active
        if captures_only:
            targets &= enemy
        _append_moves(moves, from_sq, targets, enemy)

def _gen_king_moves(pieces: int, moves: List[Move], active: int, enemy: int, captures_only: bool):
    """Generate king moves using precomputed attack table"""
    for from_sq in BitBoard.bit_scan(pieces):
        targets = KING_ATTACKS[from_sq] & ~active
        if captures_only:
            targets &= enemy
        _append_moves(moves, from_sq, targets, enemy)

def _gen_castling_moves(state: State, moves: List[Move], all_pieces: int):
    """Generate pseudo-legal castling moves checking rights and path safety"""
    opponent = BLACK if state.player == WHITE else WHITE
    
    if state.player == WHITE:
        # white kingside
        if state.castling & CASTLE_WK:
            # check F1 and G1 are empty
            if not (all_pieces & ((1 << F1) | (1 << G1))):
                # check E1, F1, G1 are not attacked
                if not is_square_attacked(state, E1, opponent) and not is_square_attacked(state, F1, opponent) and not is_square_attacked(state, G1, opponent):
                    moves.append(Move(E1, G1, CASTLE))
        
        # white queenside
        if state.castling & CASTLE_WQ:
            # check B1, C1, D1 are empty
            if not (all_pieces & ((1 << B1) | (1 << C1) | (1 << D1))):
                # check E1, D1, C1 are not attacked
                # note: B1 does not need to be safe as rook can pass through attack
                if not is_square_attacked(state, E1, opponent) and not is_square_attacked(state, D1, opponent) and not is_square_attacked(state, C1, opponent):
                    moves.append(Move(E1, C1, CASTLE))
    
    else: # black
        # black kingside
        if state.castling & CASTLE_BK:
            # check F8 and G8 are empty
            if not (all_pieces & ((1 << F8) | (1 << G8))):
                # check E8, F8, G8 are not attacked
                if not is_square_attacked(state, E8, opponent) and not is_square_attacked(state, F8, opponent) and not is_square_attacked(state, G8, opponent):
                    moves.append(Move(E8, G8, CASTLE))
        
        # black queenside
        if state.castling & CASTLE_BQ:
            # check B8, C8, D8 are empty
            if not (all_pieces & ((1 << B8) | (1 << C8) | (1 << D8))):
                # check E8, D8, C8 are not attacked
                if not is_square_attacked(state, E8, opponent) and not is_square_attacked(state, D8, opponent) and not is_square_attacked(state, C8, opponent):
                    moves.append(Move(E8, C8, CASTLE))

def _gen_bishop_moves(pieces: int, moves: List[Move], all_pieces: int, active: int, enemy: int, captures_only: bool):
    """Generate bishop moves using precomputed lookup"""
    for from_sq in BitBoard.bit_scan(pieces):
        mask = BISHOP_MASKS[from_sq]
        targets = BISHOP_TABLE[(from_sq, all_pieces & mask)] & ~active
        if captures_only:
            targets &= enemy
        _append_moves(moves, from_sq, targets, enemy)

def _gen_rook_moves(pieces: int, moves: List[Move], all_pieces: int, active: int, enemy: int, captures_only: bool):
    """Generate rook moves using precomputed lookup"""
    for from_sq in BitBoard.bit_scan(pieces):
        mask = ROOK_MASKS[from_sq]
        targets = ROOK_TABLE[(from_sq, all_pieces & mask)] & ~active
        if captures_only:
            targets &= enemy
        _append_moves(moves, from_sq, targets, enemy)

def _gen_queen_moves(pieces: int, moves: List[Move], all_pieces: int, active: int, enemy: int, captures_only: bool):
    """Generate queen moves combining orthogonal and diagonal movement"""
    for from_sq in BitBoard.bit_scan(pieces):
        # combine rook and bishop attacks
        r_mask = ROOK_MASKS[from_sq]
        b_mask = BISHOP_MASKS[from_sq]
        targets = (ROOK_TABLE[(from_sq, all_pieces & r_mask)] | BISHOP_TABLE[(from_sq, all_pieces & b_mask)]) & ~active
        if captures_only:
            targets &= enemy
        _append_moves(moves, from_sq, targets, enemy)

def _append_moves(moves: List[Move], from_sq: int, targets_bb: int, enemy: int):
    """Convert a target bitboard into move objects"""
    for to_sq in BitBoard.bit_scan(targets_bb):
        # determine if move is a capture
        flag = CAPTURE if (1 << to_sq) & enemy else QUIET
        moves.append(Move(from_sq, to_sq, flag))
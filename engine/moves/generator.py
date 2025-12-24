from typing import List
from engine.core.constants import (
    WHITE, BLACK, CASTLE_WK, CASTLE_WQ, CASTLE_BK, CASTLE_BQ,
    A8, H1, E1, F1, G1, C1, D1, B1, E8, F8, G8, C8, D8, B8,
    RANK_3, RANK_6,
    WHITE_PIECES, BLACK_PIECES,
    MASK_SOURCE, MASK_TARGET, NO_SQUARE,
    NORTH, SOUTH,
    WP, BP, WN, BN, WB, BB, WR, BR, WQ, BQ, WK, BK,
    WHITE_STR, BLACK_STR, ALL_STR
)
from engine.board.state import State
from engine.core.move import (
    QUIET, CAPTURE, EN_PASSANT,
    CASTLE_KS, CASTLE_QS,
    PROMOTION_N, PROMOTION_B, PROMOTION_R, PROMOTION_Q,
    PROMO_CAP_N, PROMO_CAP_B, PROMO_CAP_R, PROMO_CAP_Q,
    DOUBLE_PUSH, _pack
)
from engine.moves.legality import is_legal, is_square_attacked

from engine.moves.precomputed import (
    KNIGHT_ATTACKS, KING_ATTACKS,
    ROOK_TABLE, ROOK_MASKS,
    BISHOP_TABLE, BISHOP_MASKS,
    WHITE_PAWN_ATTACKS, BLACK_PAWN_ATTACKS
)

def get_legal_moves(state: State, captures_only=False) -> List[int]:
    """Generate all legal moves (integers)"""
    pseudo_legal = generate_pseudo_legal_moves(state, captures_only)
    return [move for move in pseudo_legal if is_legal(state, move)]

def generate_pseudo_legal_moves(state: State, captures_only=False) -> List[int]:
    """Generate all pseudo-legal moves"""
    moves: List[int] = []
    bitboards = state.bitboards
    all_pieces = bitboards[ALL_STR]
    
    if state.is_white:
        active = bitboards[WHITE_STR]
        opponent = bitboards[BLACK_STR]
        P, N, B, R, Q, K = WHITE_PIECES
        pawn_attacks = WHITE_PAWN_ATTACKS
    else:
        active = bitboards[BLACK_STR]
        opponent = bitboards[WHITE_STR]
        P, N, B, R, Q, K = BLACK_PIECES
        pawn_attacks = BLACK_PAWN_ATTACKS

    _gen_pawn_moves(state, moves, P, state.is_white, all_pieces, opponent, pawn_attacks, captures_only)
    _gen_knight_moves(bitboards[N], moves, active, opponent, captures_only)
    _gen_king_moves(bitboards[K], moves, active, opponent, captures_only)
    if not captures_only: _gen_castling_moves(state, moves, all_pieces)
    _gen_bishop_moves(bitboards[B], moves, all_pieces, active, opponent, captures_only)
    _gen_rook_moves(bitboards[R], moves, all_pieces, active, opponent, captures_only)
    _gen_queen_moves(bitboards[Q], moves, all_pieces, active, opponent, captures_only)
    
    return moves

def _gen_pawn_moves(state: State, moves: List[int], pawn_key: str, colour: bool, all_pieces: int, enemy: int, attack_table: List[int], captures_only: bool):
    pawns = state.bitboards[pawn_key]
    if colour == WHITE:
        direction = NORTH
        start_rank_mask = RANK_3
        promotion_rank = A8
        single_push = (pawns << NORTH) & ~all_pieces
        double_push = ((single_push & start_rank_mask) << NORTH) & ~all_pieces
    else:
        direction = SOUTH
        start_rank_mask = RANK_6
        promotion_rank = H1
        single_push = (pawns >> NORTH) & ~all_pieces
        double_push = ((single_push & start_rank_mask) >> NORTH) & ~all_pieces
    
    # single pushes
    bb = single_push
    while bb:
        lsb = bb & -bb
        to_sq = lsb.bit_length() - 1
        bb &= bb - 1
        
        from_sq = to_sq - direction
        is_promo = (colour == WHITE and to_sq >= promotion_rank) or (colour == BLACK and to_sq <= promotion_rank)
        
        if is_promo: 
            _add_promotions(moves, from_sq, to_sq, False)
        elif not captures_only: 
            moves.append(_pack(from_sq, to_sq, QUIET))
            
    # double pushes
    if not captures_only:
        bb = double_push
        while bb:
            lsb = bb & -bb
            to_sq = lsb.bit_length() - 1
            bb &= bb - 1
            
            from_sq = to_sq - (2 * direction)
            moves.append(_pack(from_sq, to_sq, DOUBLE_PUSH))

    # captures
    bb = pawns
    while bb:
        lsb = bb & -bb
        from_sq = lsb.bit_length() - 1
        bb &= bb - 1
        
        attacks = attack_table[from_sq] & enemy
        while attacks:
            t_lsb = attacks & -attacks
            to_sq = t_lsb.bit_length() - 1
            attacks &= attacks - 1
            
            if (colour == WHITE and to_sq >= promotion_rank) or (colour == BLACK and to_sq <= promotion_rank):
                _add_promotions(moves, from_sq, to_sq, True)
            else:
                moves.append(_pack(from_sq, to_sq, CAPTURE))
        
        if state.en_passant_square != NO_SQUARE:
            if attack_table[from_sq] & (1 << state.en_passant_square):
                moves.append(_pack(from_sq, state.en_passant_square, EN_PASSANT))

def _add_promotions(moves: List[int], from_sq: int, to_sq: int, is_capture: bool):
    if is_capture:
        moves.append(_pack(from_sq, to_sq, PROMO_CAP_Q))
        moves.append(_pack(from_sq, to_sq, PROMO_CAP_R))
        moves.append(_pack(from_sq, to_sq, PROMO_CAP_B))
        moves.append(_pack(from_sq, to_sq, PROMO_CAP_N))
    else:
        moves.append(_pack(from_sq, to_sq, PROMOTION_Q))
        moves.append(_pack(from_sq, to_sq, PROMOTION_R))
        moves.append(_pack(from_sq, to_sq, PROMOTION_B))
        moves.append(_pack(from_sq, to_sq, PROMOTION_N))

def _gen_knight_moves(pieces: int, moves: List[int], active: int, enemy: int, captures_only: bool):
    while pieces:
        lsb = pieces & -pieces
        from_sq = lsb.bit_length() - 1
        pieces &= pieces - 1
        
        targets = KNIGHT_ATTACKS[from_sq] & ~active
        if captures_only: targets &= enemy
        
        while targets:
            t_lsb = targets & -targets
            to_sq = t_lsb.bit_length() - 1
            targets &= targets - 1
            flag = CAPTURE if (1 << to_sq) & enemy else QUIET
            moves.append(_pack(from_sq, to_sq, flag))

def _gen_king_moves(pieces: int, moves: List[int], active: int, enemy: int, captures_only: bool):
    while pieces:
        lsb = pieces & -pieces
        from_sq = lsb.bit_length() - 1
        pieces &= pieces - 1
        
        targets = KING_ATTACKS[from_sq] & ~active
        if captures_only: targets &= enemy
        
        while targets:
            t_lsb = targets & -targets
            to_sq = t_lsb.bit_length() - 1
            targets &= targets - 1
            flag = CAPTURE if (1 << to_sq) & enemy else QUIET
            moves.append(_pack(from_sq, to_sq, flag))

def _gen_castling_moves(state: State, moves: List[int], all_pieces: int):
    opponent = BLACK if state.is_white else WHITE
    if state.is_white:
        if state.castling_rights & CASTLE_WK:
            if not (all_pieces & ((1 << F1) | (1 << G1))):
                if not is_square_attacked(state, E1, opponent) and not is_square_attacked(state, F1, opponent) and not is_square_attacked(state, G1, opponent):
                    moves.append(_pack(E1, G1, CASTLE_KS))
        if state.castling_rights & CASTLE_WQ:
            if not (all_pieces & ((1 << B1) | (1 << C1) | (1 << D1))):
                if not is_square_attacked(state, E1, opponent) and not is_square_attacked(state, D1, opponent) and not is_square_attacked(state, C1, opponent):
                    moves.append(_pack(E1, C1, CASTLE_QS))
    else:
        if state.castling_rights & CASTLE_BK:
            if not (all_pieces & ((1 << F8) | (1 << G8))):
                if not is_square_attacked(state, E8, opponent) and not is_square_attacked(state, F8, opponent) and not is_square_attacked(state, G8, opponent):
                    moves.append(_pack(E8, G8, CASTLE_KS))
        if state.castling_rights & CASTLE_BQ:
            if not (all_pieces & ((1 << B8) | (1 << C8) | (1 << D8))):
                if not is_square_attacked(state, E8, opponent) and not is_square_attacked(state, D8, opponent) and not is_square_attacked(state, C8, opponent):
                    moves.append(_pack(E8, C8, CASTLE_QS))

def _gen_bishop_moves(pieces: int, moves: List[int], all_pieces: int, active: int, enemy: int, captures_only: bool):
    while pieces:
        lsb = pieces & -pieces
        from_sq = lsb.bit_length() - 1
        pieces &= pieces - 1
        
        mask = BISHOP_MASKS[from_sq]
        targets = BISHOP_TABLE[(from_sq, all_pieces & mask)] & ~active
        if captures_only: targets &= enemy
        
        while targets:
            t_lsb = targets & -targets
            to_sq = t_lsb.bit_length() - 1
            targets &= targets - 1
            flag = CAPTURE if (1 << to_sq) & enemy else QUIET
            moves.append(_pack(from_sq, to_sq, flag))

def _gen_rook_moves(pieces: int, moves: List[int], all_pieces: int, active: int, enemy: int, captures_only: bool):
    while pieces:
        lsb = pieces & -pieces
        from_sq = lsb.bit_length() - 1
        pieces &= pieces - 1
        
        mask = ROOK_MASKS[from_sq]
        targets = ROOK_TABLE[(from_sq, all_pieces & mask)] & ~active
        if captures_only: targets &= enemy
        
        while targets:
            t_lsb = targets & -targets
            to_sq = t_lsb.bit_length() - 1
            targets &= targets - 1
            flag = CAPTURE if (1 << to_sq) & enemy else QUIET
            moves.append(_pack(from_sq, to_sq, flag))

def _gen_queen_moves(pieces: int, moves: List[int], all_pieces: int, active: int, enemy: int, captures_only: bool):
    while pieces:
        lsb = pieces & -pieces
        from_sq = lsb.bit_length() - 1
        pieces &= pieces - 1
        
        r_mask = ROOK_MASKS[from_sq]
        b_mask = BISHOP_MASKS[from_sq]
        targets = (ROOK_TABLE[(from_sq, all_pieces & r_mask)] | BISHOP_TABLE[(from_sq, all_pieces & b_mask)]) & ~active
        if captures_only: targets &= enemy
        
        while targets:
            t_lsb = targets & -targets
            to_sq = t_lsb.bit_length() - 1
            targets &= targets - 1
            flag = CAPTURE if (1 << to_sq) & enemy else QUIET
            moves.append(_pack(from_sq, to_sq, flag))
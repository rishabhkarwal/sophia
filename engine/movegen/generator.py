from typing import List
from engine.core.constants import (
    WHITE, BLACK, CASTLE_WK, CASTLE_WQ, CASTLE_BK, CASTLE_BQ,
    A8, H1, E1, F1, G1, C1, D1, B1, E8, F8, G8, C8, D8, B8,
    RANK_3, RANK_6, WHITE_PIECES, BLACK_PIECES
)
from engine.board.state import State
from engine.core.move import Move, QUIET, CAPTURE, EP_CAPTURE, CASTLE, PROMOTION
from engine.movegen.precomputed import (
    KNIGHT_ATTACKS, KING_ATTACKS,
    ROOK_TABLE, ROOK_MASKS,
    BISHOP_TABLE, BISHOP_MASKS,
    WHITE_PAWN_ATTACKS, BLACK_PAWN_ATTACKS
)
from engine.core.bitboard_utils import BitBoard
from engine.movegen.legality import is_legal, is_square_attacked

def get_legal_moves(state: State, captures_only=False) -> List[Move]:
    """Generate all LEGAL moves (filters pseudo-legal)"""
    pseudo_legal = generate_moves(state, captures_only)
    legal = []
    for move in pseudo_legal:
        if is_legal(state, move):
            legal.append(move)
    return legal

def generate_moves(state: State, captures_only=False) -> List[Move]:
    moves: List[Move] = []
    all_pieces = state.bitboards["all"]
    
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

    _gen_pawn_moves(state, moves, P, state.player, all_pieces, opponent, pawn_attacks, captures_only)
    _gen_knight_moves(state.bitboards[N], moves, active, opponent, captures_only)
    _gen_king_moves(state.bitboards[K], moves, active, opponent, captures_only)
    if not captures_only: _gen_castling_moves(state, moves, all_pieces)
    _gen_bishop_moves(state.bitboards[B], moves, all_pieces, active, opponent, captures_only)
    _gen_rook_moves(state.bitboards[R], moves, all_pieces, active, opponent, captures_only)
    _gen_queen_moves(state.bitboards[Q], moves, all_pieces, active, opponent, captures_only)
    
    return moves

def _gen_pawn_moves(state: State, moves: List[Move], pawn_key: str, colour: int, all_pieces: int, enemy: int, attack_table: List[int], captures_only: bool):
    pawns = state.bitboards[pawn_key]
    
    if colour == WHITE:
        direction = 8
        start_rank_mask = RANK_3
        promotion_rank = A8
        single_push = (pawns << 8) & ~all_pieces
        double_push = ((single_push & start_rank_mask) << 8) & ~all_pieces
    else:
        direction = -8
        start_rank_mask = RANK_6
        promotion_rank = H1
        single_push = (pawns >> 8) & ~all_pieces
        double_push = ((single_push & start_rank_mask) >> 8) & ~all_pieces
    
    if not captures_only:
        for to_sq in BitBoard.bit_scan(single_push):
            from_sq = to_sq - direction
            if (colour == WHITE and to_sq >= promotion_rank) or (colour == BLACK and to_sq <= promotion_rank):
                _add_promotions(moves, from_sq, to_sq, QUIET)
            else:
                moves.append(Move(from_sq, to_sq, QUIET))
        
        for to_sq in BitBoard.bit_scan(double_push):
            from_sq = to_sq - (2 * direction)
            moves.append(Move(from_sq, to_sq, QUIET))
    
    for from_sq in BitBoard.bit_scan(pawns):
        attacks = attack_table[from_sq] & enemy
        for to_sq in BitBoard.bit_scan(attacks):
            if (colour == WHITE and to_sq >= promotion_rank) or (colour == BLACK and to_sq <= promotion_rank):
                _add_promotions(moves, from_sq, to_sq, CAPTURE)
            else:
                moves.append(Move(from_sq, to_sq, CAPTURE))
        
        if state.en_passant != -1:
            if attack_table[from_sq] & (1 << state.en_passant):
                moves.append(Move(from_sq, state.en_passant, EP_CAPTURE | CAPTURE))

def _add_promotions(moves: List[Move], from_sq: int, to_sq: int, base_flag: int):
    flag = base_flag | PROMOTION
    moves.append(Move(from_sq, to_sq, flag, promo_type='q'))
    moves.append(Move(from_sq, to_sq, flag, promo_type='r'))
    moves.append(Move(from_sq, to_sq, flag, promo_type='b'))
    moves.append(Move(from_sq, to_sq, flag, promo_type='n'))

def _gen_knight_moves(pieces: int, moves: List[Move], active: int, enemy: int, captures_only: bool):
    for from_sq in BitBoard.bit_scan(pieces):
        targets = KNIGHT_ATTACKS[from_sq] & ~active
        if captures_only: targets &= enemy
        _append_moves(moves, from_sq, targets, enemy)

def _gen_king_moves(pieces: int, moves: List[Move], active: int, enemy: int, captures_only: bool):
    for from_sq in BitBoard.bit_scan(pieces):
        targets = KING_ATTACKS[from_sq] & ~active
        if captures_only: targets &= enemy
        _append_moves(moves, from_sq, targets, enemy)

def _gen_castling_moves(state: State, moves: List[Move], all_pieces: int):
    opponent = BLACK if state.player == WHITE else WHITE
    if state.player == WHITE:
        if state.castling & CASTLE_WK:
            if not (all_pieces & ((1 << F1) | (1 << G1))):
                if not is_square_attacked(state, E1, opponent) and not is_square_attacked(state, F1, opponent) and not is_square_attacked(state, G1, opponent):
                    moves.append(Move(E1, G1, CASTLE))
        if state.castling & CASTLE_WQ:
            if not (all_pieces & ((1 << B1) | (1 << C1) | (1 << D1))):
                if not is_square_attacked(state, E1, opponent) and not is_square_attacked(state, D1, opponent) and not is_square_attacked(state, C1, opponent):
                    moves.append(Move(E1, C1, CASTLE))
    else:
        if state.castling & CASTLE_BK:
            if not (all_pieces & ((1 << F8) | (1 << G8))):
                if not is_square_attacked(state, E8, opponent) and not is_square_attacked(state, F8, opponent) and not is_square_attacked(state, G8, opponent):
                    moves.append(Move(E8, G8, CASTLE))
        if state.castling & CASTLE_BQ:
            if not (all_pieces & ((1 << B8) | (1 << C8) | (1 << D8))):
                if not is_square_attacked(state, E8, opponent) and not is_square_attacked(state, D8, opponent) and not is_square_attacked(state, C8, opponent):
                    moves.append(Move(E8, C8, CASTLE))

def _gen_bishop_moves(pieces: int, moves: List[Move], all_pieces: int, active: int, enemy: int, captures_only: bool):
    for from_sq in BitBoard.bit_scan(pieces):
        mask = BISHOP_MASKS[from_sq]
        targets = BISHOP_TABLE[(from_sq, all_pieces & mask)] & ~active
        if captures_only: targets &= enemy
        _append_moves(moves, from_sq, targets, enemy)

def _gen_rook_moves(pieces: int, moves: List[Move], all_pieces: int, active: int, enemy: int, captures_only: bool):
    for from_sq in BitBoard.bit_scan(pieces):
        mask = ROOK_MASKS[from_sq]
        targets = ROOK_TABLE[(from_sq, all_pieces & mask)] & ~active
        if captures_only: targets &= enemy
        _append_moves(moves, from_sq, targets, enemy)

def _gen_queen_moves(pieces: int, moves: List[Move], all_pieces: int, active: int, enemy: int, captures_only: bool):
    for from_sq in BitBoard.bit_scan(pieces):
        r_mask = ROOK_MASKS[from_sq]
        b_mask = BISHOP_MASKS[from_sq]
        targets = (ROOK_TABLE[(from_sq, all_pieces & r_mask)] | BISHOP_TABLE[(from_sq, all_pieces & b_mask)]) & ~active
        if captures_only: targets &= enemy
        _append_moves(moves, from_sq, targets, enemy)

def _append_moves(moves: List[Move], from_sq: int, targets_bb: int, enemy: int):
    for to_sq in BitBoard.bit_scan(targets_bb):
        flag = CAPTURE if (1 << to_sq) & enemy else QUIET
        moves.append(Move(from_sq, to_sq, flag))
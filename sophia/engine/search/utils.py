import chess
from engine.core.constants import (
    WP, WN, WB, WR, WQ, WK,
    BP, BN, BB, BR, BQ, BK,
    NULL, WHITE, BLACK,
    WHITE, BLACK,
    MAX_DEPTH, INFINITY
)

def state_to_board(state):
    """Convert internal state to python-chess board"""
    board = chess.Board(fen=None)
    board.clear()

    piece_map = {
        WP: chess.PAWN, WN: chess.KNIGHT, WB: chess.BISHOP,
        WR: chess.ROOK, WQ: chess.QUEEN, WK: chess.KING,
        BP: chess.PAWN, BN: chess.KNIGHT, BB: chess.BISHOP,
        BR: chess.ROOK, BQ: chess.QUEEN, BK: chess.KING
    }
    
    for piece_idx in range(2, 16):
        if piece_idx not in piece_map:
            continue
            
        bb = state.bitboards[piece_idx]
        piece_type = piece_map[piece_idx]
        colour = chess.WHITE if (piece_idx & WHITE) else chess.BLACK
        
        while bb:
            lsb = bb & -bb
            sq = lsb.bit_length() - 1
            board.set_piece_at(sq, chess.Piece(piece_type, colour))
            bb &= bb - 1

    board.turn = chess.WHITE if state.is_white else chess.BLACK
    
    board.castling_rights = 0
    from engine.core.constants import CASTLE_WK, CASTLE_WQ, CASTLE_BK, CASTLE_BQ
    from engine.core.constants import A1, H1, A8, H8
    
    if state.castling_rights & CASTLE_WK: board.castling_rights |= chess.BB_H1
    if state.castling_rights & CASTLE_WQ: board.castling_rights |= chess.BB_A1
    if state.castling_rights & CASTLE_BK: board.castling_rights |= chess.BB_H8
    if state.castling_rights & CASTLE_BQ: board.castling_rights |= chess.BB_A8

    if state.en_passant_square != NULL: board.ep_square = state.en_passant_square
    else: board.ep_square = None
    
    board.halfmove_clock = state.halfmove_clock
    board.fullmove_number = state.fullmove_number
    
    return board

def _get_cp_score(score, max_mate_depth=MAX_DEPTH):
    if INFINITY - abs(score) < max_mate_depth:
        if score > 0:
            ply_to_mate = INFINITY - score
            mate_in = (ply_to_mate + 1) // 2
            score_str = f"mate {mate_in}"
        else:
            ply_to_mate = INFINITY + score
            mate_in = (ply_to_mate + 1) // 2
            score_str = f"mate -{mate_in}"
    else:
        score_str = f"cp {int(score)}"
    return score_str
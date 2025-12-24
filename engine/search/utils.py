import chess
from engine.core.constants import (
    WHITE, NO_SQUARE,
    CASTLE_WK, CASTLE_WQ, CASTLE_BK, CASTLE_BQ,
    PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING
)

def state_to_board(state):
    """Converts State to python-chess Board"""
    board = chess.Board.empty()
    
    piece_map = {
        PAWN: chess.PAWN, 
        KNIGHT: chess.KNIGHT, 
        BISHOP: chess.BISHOP,
        ROOK: chess.ROOK, 
        QUEEN: chess.QUEEN, 
        KING: chess.KING
    }

    for piece, bb in state.bitboards.items():
        if bb == 0: continue
        
        if piece.upper() not in piece_map: continue

        piece_type = piece_map[piece.upper()]
        color = chess.WHITE if piece.isupper() else chess.BLACK
        
        # sets pieces
        temp_bb = bb
        while temp_bb:
            lsb = temp_bb & -temp_bb
            sq = lsb.bit_length() - 1
            board.set_piece_at(sq, chess.Piece(piece_type, color))
            temp_bb ^= lsb

    # set turn
    board.turn = state.is_white

    # set castling rights
    board.castling_rights = chess.BB_EMPTY
    if state.castling_rights & CASTLE_WK: board.castling_rights |= chess.BB_H1
    if state.castling_rights & CASTLE_WQ: board.castling_rights |= chess.BB_A1
    if state.castling_rights & CASTLE_BK: board.castling_rights |= chess.BB_H8
    if state.castling_rights & CASTLE_BQ: board.castling_rights |= chess.BB_A8

    # set en-passant
    if state.en_passant_square != NO_SQUARE:
        board.ep_square = state.en_passant_square

    # set clocks
    board.halfmove_clock = state.halfmove_clock
    board.fullmove_number = state.fullmove_number

    return board
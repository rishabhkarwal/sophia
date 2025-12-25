from engine.core.utils import set_bit, algebraic_to_bit
from engine.board.state import State
from engine.core.constants import (
    NULL, WHITE, BLACK, WK, WQ, BK, BQ,
    CASTLE_BK, CASTLE_BQ, CASTLE_WK, CASTLE_WQ,
    FLIP_BOARD, CHAR_TO_PIECE, PIECE_STR
)
from engine.search.evaluation import calculate_initial_score
from engine.core.zobrist import compute_hash

def load_from_fen(fen_string: str = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1') -> State:
    fields = fen_string.split(' ')
    
    bitboards, board = _parse_pieces(fields[0])
    
    state = State(
        bitboards=bitboards,
        board=board,
        is_white=_parse_active_colour(fields[1]),
        castling_rights=_parse_castling_rights(fields[2]),
        en_passant_square=_parse_en_passant(fields[3]),
        halfmove_clock=int(fields[4]),
        fullmove_number=int(fields[5]),
        history=[],
    )
    
    state.mg_score, state.eg_score, state.phase = calculate_initial_score(state)
    state.hash = compute_hash(state)
    
    return state

def _parse_pieces(pieces_fen: str):
    square_count = 0
    ranks = pieces_fen.split('/')
    
    bitboards = [0] * 16
    board = [NULL] * 64
    
    for rank in ranks:
        for square in rank:
            if square.isnumeric():
                square_count += int(square)
            else:
                index = square_count ^ FLIP_BOARD
                piece = CHAR_TO_PIECE[square]

                bitboards[piece] |= (1 << index)

                if piece & WHITE: bitboards[WHITE] |= (1 << index)
                else: bitboards[BLACK] |= (1 << index)
                
                board[index] = piece
                square_count += 1
    
    return bitboards, board

def _parse_active_colour(colour_fen: str):
    return colour_fen == 'w'

def _parse_castling_rights(castling_fen: str):
    rights = 0
    if PIECE_STR[WK] in castling_fen: rights |= CASTLE_WK
    if PIECE_STR[WQ] in castling_fen: rights |= CASTLE_WQ
    if PIECE_STR[BK] in castling_fen: rights |= CASTLE_BK
    if PIECE_STR[BQ] in castling_fen: rights |= CASTLE_BQ
    return rights

def _parse_en_passant(en_passant_fen: str):
    if en_passant_fen == '-': return NULL
    return algebraic_to_bit(en_passant_fen)
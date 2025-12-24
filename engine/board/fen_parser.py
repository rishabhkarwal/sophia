from engine.core.utils import set_bit, algebraic_to_bit
from engine.board.state import State
from engine.core.constants import (
    NO_SQUARE, WHITE, BLACK,
    CASTLE_BK, CASTLE_BQ, CASTLE_WK, CASTLE_WQ,
    ALL_PIECES, FLIP_BOARD,
    WHITE_STR, BLACK_STR, ALL_STR,
    WK, BK, WQ, BQ
)
from engine.search.evaluation import calculate_initial_score
from engine.core.zobrist import compute_hash

def load_from_fen(fen_string: str = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1') -> State:
    state = State(
        bitboards={},
        is_white=WHITE,
        castling_rights=0,
        en_passant_square=NO_SQUARE,
        halfmove_clock=0,
        fullmove_number=0,
        history=[],
    )
    
    fields = fen_string.split(' ')
    
    state.bitboards = _parse_pieces(fields[0])
    state.is_white = _parse_active_colour(fields[1])
    state.castling_rights = _parse_castling_rights(fields[2])
    state.en_passant_square = _parse_en_passant(fields[3])
    state.halfmove_clock = int(fields[4])
    state.fullmove_number = int(fields[5])
    
    state.mg_score, state.eg_score, state.phase = calculate_initial_score(state)
    state.hash = compute_hash(state)
    
    return state

def _parse_pieces(pieces_fen: str):
    """Sets all bitboards"""
    square_count = 0
    ranks = pieces_fen.split('/')
    bitboards = {piece: 0 for piece in ALL_PIECES + (WHITE_STR, BLACK_STR, ALL_STR)}
    
    for rank in ranks:
        for square in rank:
            if square.isnumeric(): 
                square_count += int(square)
            
            if square.isalpha():  # piece
                index = square_count ^ FLIP_BOARD  # flipped as bitboards start from bottom left
                bitboards[square] = set_bit(bitboards[square], index)
                colour = WHITE_STR if square.isupper() else BLACK_STR
                bitboards[colour] = set_bit(bitboards[colour], index)
                square_count += 1
    
    bitboards[ALL_STR] = bitboards[WHITE_STR] | bitboards[BLACK_STR]
    return bitboards

def _parse_active_colour(colour_fen: str):
    """Sets the active player"""
    return colour_fen == 'w'

def _parse_castling_rights(castling_fen: str):
    """Sets castling rights bitmask"""
    rights = 0
    if WK in castling_fen: rights |= CASTLE_WK  # white kingside
    if WQ in castling_fen: rights |= CASTLE_WQ  # white queenside
    if BK in castling_fen: rights |= CASTLE_BK  # black kingside
    if BQ in castling_fen: rights |= CASTLE_BQ  # black queenside
    return rights

def _parse_en_passant(en_passant_fen: str):
    """Sets en passant square index"""
    if en_passant_fen == '-': return NO_SQUARE
    return algebraic_to_bit(en_passant_fen)
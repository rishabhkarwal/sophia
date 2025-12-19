from engine.core.bitboard_utils import BitBoard
from engine.board.state import State
from engine.core.constants import NO_SQUARE, WHITE, BLACK, CASTLE_BK, CASTLE_BQ, CASTLE_WK, CASTLE_WQ, WHITE_PIECES, BLACK_PIECES

def load_from_fen(fen_string : str = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'):
    state = State(
        bitboards = {},
        player = 0,
        castling = 0,
        en_passant = 0,
        halfmove_clock = 0,
        fullmove_number = 0,
        history = [],
    )

    fields = fen_string.split(' ')
    
    _parse_pieces(fields[0], state)

    _parse_active_colour(fields[1], state)

    _parse_castling_rights(fields[2], state)

    _parse_en_passant(fields[3], state)

    try:
        state.halfmove_clock = int(fields[4])
    except:
        state.halfmove_clock = 0
    
    try:
        state.fullmove_number = int(fields[5])
    except: 
        state.fullmove_number = 1

    return state

def _parse_pieces(pieces_fen, state):
    state.bitboards = {piece : 0 for piece in WHITE_PIECES + BLACK_PIECES + ('white', 'black', 'all')}

    count = 0
    for rank in pieces_fen.split()[0].split('/'):
        for square in rank:
            if square.isnumeric(): count += int(square)
            
            if square.isalpha():
                index = 56 - ((count // 8) * 8) + (count % 8)
                state.bitboards[square] = BitBoard.set_bit(state.bitboards[square], index)
                if square.isupper(): state.bitboards['white'] = BitBoard.set_bit(state.bitboards['white'], index)
                else: state.bitboards['black'] = BitBoard.set_bit(state.bitboards['black'], index)
                count += 1

    state.bitboards['all'] = state.bitboards['white'] | state.bitboards['black']

def _parse_active_colour(colour_fen: str, state):
    """Parses the active colour and updates player"""
    if colour_fen == 'w': state.player = WHITE
    elif colour_fen == 'b': state.player = BLACK

def _parse_castling_rights(castling_fen: str, state):
    """Parses the castling string and updates castling rights bitmask"""
    rights = 0
    if 'K' in castling_fen:
        rights |= CASTLE_WK
    if 'Q' in castling_fen:
        rights |= CASTLE_WQ
    if 'k' in castling_fen:
        rights |= CASTLE_BK
    if 'q' in castling_fen:
        rights |= CASTLE_BQ

    state.castling = rights

def _parse_en_passant(en_passant_fen: str, state):
    """Parses the en passant square and updates en passant square index"""
    if en_passant_fen != '-': state.en_passant = BitBoard.algebraic_to_bit(en_passant_fen)
    else: state.en_passant = NO_SQUARE
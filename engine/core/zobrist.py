import random
from engine.core.constants import ALL_PIECES, NO_SQUARE

# Zobrist table key constants
KEY_CASTLING = 'castling'
KEY_EP = 'ep'
KEY_BLACK_TO_MOVE = 'black_to_move'

def init_zobrist_keys():
    """Initialises random 64-bit integers for Zobrist hashing"""
    random.seed(42)
    table = {}
    
    # pieces: 'P': [rand_0, rand_1, ...], 'n': [rand_0, rand_1, ...]
    for piece in ALL_PIECES:
        table[piece] = [random.getrandbits(64) for _ in range(64)]
    
    # castling: 16 combinations (0-15)
    table[KEY_CASTLING] = [random.getrandbits(64) for _ in range(16)]
    
    # en-passant: file 0-7, or none (use index 8 for None)
    table[KEY_EP] = [random.getrandbits(64) for _ in range(9)]
    
    # side to move (black to move)
    table[KEY_BLACK_TO_MOVE] = random.getrandbits(64)
    
    return table

ZOBRIST_KEYS = init_zobrist_keys()

def compute_hash(state) -> int:
    """Computes the full Zobrist hash of a state"""
    h = 0
    # piece positions
    for piece, bb in state.bitboards.items():
        if piece not in ZOBRIST_KEYS: continue
        temp_bb = bb
        while temp_bb:
            sq = (temp_bb & -temp_bb).bit_length() - 1
            h ^= ZOBRIST_KEYS[piece][sq]
            temp_bb &= temp_bb - 1
            
    # castling rights
    h ^= ZOBRIST_KEYS[KEY_CASTLING][state.castling_rights]
    
    # en passant
    file = state.en_passant_square % 8 if state.en_passant_square != NO_SQUARE else 8
    h ^= ZOBRIST_KEYS[KEY_EP][file]
        
    # side to move (if black)
    if not state.is_white:
        h ^= ZOBRIST_KEYS[KEY_BLACK_TO_MOVE]
        
    return h

def z_piece(piece, square):
    """Get Zobrist key for a piece at a square"""
    return ZOBRIST_KEYS[piece][square]

def z_castle(rights):
    """Get Zobrist key for castling rights"""
    return ZOBRIST_KEYS[KEY_CASTLING][rights]

def z_ep(square):
    """Get Zobrist key for en passant square"""
    if square == NO_SQUARE: 
        return ZOBRIST_KEYS[KEY_EP][8]
    return ZOBRIST_KEYS[KEY_EP][square % 8]

def z_black_move():
    """Get Zobrist key for black to move"""
    return ZOBRIST_KEYS[KEY_BLACK_TO_MOVE]
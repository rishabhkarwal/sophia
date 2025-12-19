import random
from .constants import ALL_PIECES, NO_SQUARE

def init_zobrist_keys():
    """Initialises random 64-bit integers for Zobrist hashing"""
    random.seed(42) 
    table = {}
    # pieces: 'P': {0: rand, 1: rand...}, 'n': ...
    for piece in ALL_PIECES: table[piece] = [random.getrandbits(64) for _ in range(64)]
    # castling: 16 combinations (0-15)
    table['castling'] = [random.getrandbits(64) for _ in range(16)]
    # en-passant: file 0-7, or none (use 8 for None)
    table['ep'] = [random.getrandbits(64) for _ in range(9)]
    # side to move (black to move)
    table['black_to_move'] = random.getrandbits(64)

    return table

ZOBRIST_KEYS = init_zobrist_keys()

def compute_hash(state) -> int:
    """Computes the full Zobrist hash of a state"""
    h = 0
    # piece positions
    for piece, bb in state.bitboards.items():
        temp_bb = bb
        while temp_bb:
            sq = (temp_bb & -temp_bb).bit_length() - 1
            if piece in ZOBRIST_KEYS:
                h ^= ZOBRIST_KEYS[piece][sq]
            temp_bb &= temp_bb - 1
            
    # castling rights
    h ^= ZOBRIST_KEYS['castling'][state.castling]
    
    # en passant
    if state.en_passant != NO_SQUARE:
        file = state.en_passant % 8
        h ^= ZOBRIST_KEYS['ep'][file]
    else:
        h ^= ZOBRIST_KEYS['ep'][8]
        
    # side to move (if black)
    if state.player == 0: h ^= ZOBRIST_KEYS['black_to_move']
        
    return h
from engine.core.constants import ALL_PIECES, WHITE, BLACK
from engine.core.bitboard_utils import BitBoard

# PAWN
MG_PAWN = [
      0,  0,  0,  0,  0,  0,  0,  0,
     50, 50, 50, 50, 50, 50, 50, 50,
     10, 10, 20, 30, 30, 20, 10, 10,
      5,  5, 10, 25, 25, 10,  5,  5,
      0,  0,  0, 20, 20,  0,  0,  0,
      5, -5,-10,  0,  0,-10, -5,  5,
      5, 10, 10,-20,-20, 10, 10,  5,
      0,  0,  0,  0,  0,  0,  0,  0
]
EG_PAWN = [
      0,  0,  0,  0,  0,  0,  0,  0,
     80, 80, 80, 80, 80, 80, 80, 80,
     50, 50, 50, 50, 50, 50, 50, 50,
     30, 30, 30, 30, 30, 30, 30, 30,
     20, 20, 20, 20, 20, 20, 20, 20,
     10, 10, 10, 10, 10, 10, 10, 10,
     10, 10, 10, 10, 10, 10, 10, 10,
      0,  0,  0,  0,  0,  0,  0,  0
]

# KNIGHT
MG_KNIGHT = [
    -50,-40,-30,-30,-30,-30,-40,-50,
    -40,-20,  0,  0,  0,  0,-20,-40,
    -30,  0, 10, 15, 15, 10,  0,-30,
    -30,  5, 15, 20, 20, 15,  5,-30,
    -30,  0, 15, 20, 20, 15,  0,-30,
    -30,  5, 10, 15, 15, 10,  5,-30,
    -40,-20,  0,  5,  5,  0,-20,-40,
    -50,-40,-30,-30,-30,-30,-40,-50
]
EG_KNIGHT = MG_KNIGHT

# BISHOP
MG_BISHOP = [
    -20,-10,-10,-10,-10,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5, 10, 10,  5,  0,-10,
    -10,  5,  5, 10, 10,  5,  5,-10,
    -10,  0, 10, 10, 10, 10,  0,-10,
    -10, 10, 10, 10, 10, 10, 10,-10,
    -10,  5,  0,  0,  0,  0,  5,-10,
    -20,-10,-10,-10,-10,-10,-10,-20
]
EG_BISHOP = MG_BISHOP

# ROOK
MG_ROOK = [
      0,  0,  0,  0,  0,  0,  0,  0,
      5, 10, 10, 10, 10, 10, 10,  5,
     -5,  0,  0,  0,  0,  0,  0, -5,
     -5,  0,  0,  0,  0,  0,  0, -5,
     -5,  0,  0,  0,  0,  0,  0, -5,
     -5,  0,  0,  0,  0,  0,  0, -5,
     -5,  0,  0,  0,  0,  0,  0, -5,
      0,  0,  0,  5,  5,  0,  0,  0
]
EG_ROOK = MG_ROOK

# QUEEN
MG_QUEEN = [
    -20,-10,-10, -5, -5,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5,  5,  5,  5,  0,-10,
    -5,  0,  5,  5,  5,  5,  0, -5,
    0,  0,  5,  5,  5,  5,  0, -5,
    -10,  5,  5,  5,  5,  5,  0,-10,
    -10,  0,  5,  0,  0,  0,  0,-10,
    -20,-10,-10, -5, -5,-10,-10,-20
]
EG_QUEEN = MG_QUEEN

# KING
MG_KING = [
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -20,-30,-30,-40,-40,-30,-30,-20,
    -10,-20,-20,-20,-20,-20,-20,-10,
     20, 20,  0,  0,  0,  0, 20, 20,
     20, 30, 10,  0,  0, 10, 30, 20
]
EG_KING = [
    -50,-40,-30,-20,-20,-30,-40,-50,
    -30,-20,-10,  0,  0,-10,-20,-30,
    -30,-10, 20, 30, 30, 20,-10,-30,
    -30,-10, 30, 40, 40, 30,-10,-30,
    -30,-10, 30, 40, 40, 30,-10,-30,
    -30,-10, 20, 30, 30, 20,-10,-30,
    -30,-30,  0,  0,  0,  0,-30,-30,
    -50,-30,-30,-30,-30,-30,-30,-50
]

TAPERED_TABLES = {
    'P': (MG_PAWN, EG_PAWN),
    'N': (MG_KNIGHT, EG_KNIGHT),
    'B': (MG_BISHOP, EG_BISHOP),
    'R': (MG_ROOK, EG_ROOK),
    'Q': (MG_QUEEN, EG_QUEEN),
    'K': (MG_KING, EG_KING)
}

VALUES = {'P': 100, 'N': 320, 'B': 330, 'R': 500, 'Q': 900, 'K': 20000}
PHASE_WEIGHTS = {'N': 320, 'B': 330, 'R': 500, 'Q': 900}
MAX_PHASE = 6400

def evaluate(state):
    """
    Evaluates the board position using Tapered Evaluation (MG/EG blending).
    Returns score relative to side to move.
    """
    mg_score = 0
    eg_score = 0
    phase = 0
    
    for piece in ALL_PIECES:
        bb = state.bitboards.get(piece, 0)
        if not bb: continue
        
        is_white = piece.isupper()
        piece_type = piece.upper()
        
        material = VALUES[piece_type]
        
        # Phase Calc
        if piece_type in PHASE_WEIGHTS:
            phase += PHASE_WEIGHTS[piece_type] * bb.bit_count()

        # Select tables
        mg_table, eg_table = TAPERED_TABLES[piece_type]
        
        for sq in BitBoard.bit_scan(bb):
            if is_white:
                # White: Table is mapped 0=A1..63=H8
                # We assume the table data matches the bitboard index (0=A1).
                # To match visual top-down representation to Little-Endian bitboard:
                # Row index = 7 - (sq // 8)
                table_idx = (7 - (sq // 8)) * 8 + (sq % 8) 
                
                mg_score += material + mg_table[table_idx]
                eg_score += material + eg_table[table_idx]
            else:
                # Black: Mirror vertically
                # Row index = (sq // 8)
                table_idx = (sq // 8) * 8 + (sq % 8)
                
                mg_score -= (material + mg_table[table_idx])
                eg_score -= (material + eg_table[table_idx])

    phase = min(phase, MAX_PHASE)
    
    # Linear interpolation
    final_score = (
        (mg_score * phase) + (eg_score * (MAX_PHASE - phase))
    ) // MAX_PHASE

    return final_score if state.player == WHITE else -final_score
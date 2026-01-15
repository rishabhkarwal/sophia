NAME = 'Sophia'
AUTHOR = '@rishabhkarwal'

# null value for empty squares and pieces
NULL = -1

# colours
WHITE = 1
BLACK = 0

# piece type encoding (shifted left by 1 to leave room for colour bit)
PAWN   = 0b001 << 1  # 2
KNIGHT = 0b010 << 1  # 4
BISHOP = 0b011 << 1  # 6
ROOK   = 0b100 << 1  # 8
QUEEN  = 0b101 << 1  # 10
KING   = 0b111 << 1  # 14

# white pieces (colour bit = 1)
WP = WHITE | PAWN    # 3
WN = WHITE | KNIGHT  # 5
WB = WHITE | BISHOP  # 7
WR = WHITE | ROOK    # 9
WQ = WHITE | QUEEN   # 11
WK = WHITE | KING    # 15

# black pieces (colour bit = 0)
BP = BLACK | PAWN    # 2
BN = BLACK | KNIGHT  # 4
BB = BLACK | BISHOP  # 6
BR = BLACK | ROOK    # 8
BQ = BLACK | QUEEN   # 10
BK = BLACK | KING    # 14

PIECE_VALUES = {
    PAWN: 100,
    KNIGHT: 305,
    BISHOP: 333,
    ROOK: 563,
    QUEEN: 950,
    KING: 20000
}

# pieces stored at their natural indices (2-15)
# white and black aggregate boards at (0-1)

# piece arrays
WHITE_PIECES = [WP, WN, WB, WR, WQ, WK]
BLACK_PIECES = [BP, BN, BB, BR, BQ, BK]
ALL_PIECES = WHITE_PIECES + BLACK_PIECES

# piece to UCI string
PIECE_STR = {
    WP: 'P', WN: 'N', WB: 'B', WR: 'R', WQ: 'Q', WK: 'K',
    BP: 'p', BN: 'n', BB: 'b', BR: 'r', BQ: 'q', BK: 'k',
    NULL: ' '
}
CHAR_TO_PIECE = {v: k for k, v in PIECE_STR.items() if k != NULL}

# castling rights bitmask
CASTLE_WK = 0b0001
CASTLE_WQ = 0b0010
CASTLE_BK = 0b0100
CASTLE_BQ = 0b1000

# evaluation constants
INFINITY = 100_000
MATE = 100_000

# game phase constants
OPENING_PHASE = 20  # phase > 20 = opening
MIDDLEGAME_PHASE = 16  # 12 < phase <= 20 = middlegame
ENDGAME_PHASE = 8  # phase <= 8 = endgame

# pawn structure
DOUBLED_PAWN_PENALTY = 10
ISOLATED_PAWN_PENALTY = 15
PASSED_PAWN_BONUS = [0, 10, 17, 15, 62, 168, 276, 0]

# knight positioning
KNIGHT_OUTPOST_BONUS = 10

# rook positioning
ROOK_ON_SEVENTH_RANK = 12
ROOK_BEHIND_PASSED_PAWN = 10

# piece mobility (pre-computed will be added)
TRAPPED_PIECE_PENALTY = 50

# piece coordination
ROOK_BATTERY_BONUS = 15
QUEEN_ROOK_BATTERY_BONUS = 15

# king safety
KING_PAWN_SHIELD_BONUS = 5

# king activity (endgame)
KING_TO_CENTRE_BONUS = 15
KING_TO_ENEMY_PAWNS_BONUS = 15

# core features
BISHOP_PAIR_BONUS = 20
ROOK_OPEN_FILE = 15
ROOK_SEMI_OPEN_FILE = 4

# mobility bonuses (per legal square)
KNIGHT_MOBILITY = 2
BISHOP_MOBILITY = 3
ROOK_MOBILITY = 3
QUEEN_MOBILITY = 1

# piece development bonuses
DEVELOPED_PIECE_BONUS = 15  # bonus for getting pieces off back rank
QUEEN_EARLY_PENALTY = 20  # penalty for moving queen too early

# trading behaviour
WINNING_THRESHOLD = 200
LOSING_THRESHOLD = -100
TRADE_BONUS_PER_PIECE = 20
TRADE_PENALTY_PER_PIECE = 25

# base contempt: engine prefers to play on rather than draw
CONTEMPT = 100  # centipawns - higher = more aggressive

# repetition penalties based on position evaluation
REPETITION_PENALTY_WINNING = 500 # MASSIVE penalty when winning
REPETITION_PENALTY_EQUAL = 100 # strong penalty when equal
REPETITION_PENALTY_SLIGHT = 150 # when slightly better

# thresholds for different contempt levels
SLIGHTLY_BETTER_THRESHOLD = 100 # eval > this = prefer to play on
CLEARLY_WINNING_THRESHOLD = 300 # eval > this = fight hard for win
CLEARLY_LOSING_THRESHOLD = -300 # eval < this = draw is acceptable

# 50-move rule contempt
FIFTY_MOVE_CONTEMPT_BASE = 50 # Base contempt at 50 moves
FIFTY_MOVE_SCALE_START = 90 # Start scaling contempt

# pruning margins
RAZOR_MARGIN = [0, 240, 280, 300]
STATIC_NULL_MARGIN = 120
FUTILITY_MARGIN = [0, 100, 180, 270] # per depth

# late move reductions
LMR_BASE_REDUCTION = 1
LMR_MOVE_THRESHOLD = 3 # start LMR after this many moves

# late move pruning
LMP_BASE = 3
LMP_MULTIPLIER = 2  # threshold = base + depth * depth * multiplier

# null move pruning
NMP_BASE_REDUCTION = 2
NMP_DEPTH_REDUCTION = 3  # use R=3 when depth >= 6
NMP_EVAL_MARGIN = 200  # extra reduction when eval > beta + margin

# extensions
CHECK_EXTENSION = 1
SINGULAR_EXTENSION = 0  # too slow so removed
SINGULAR_MARGIN = 50

# history
HISTORY_MAX = 16384
HISTORY_GRAVITY = 16 # for aging

# file masks
FILE_A = 0x0101010101010101
FILE_B = 0x0202020202020202
FILE_G = 0x4040404040404040
FILE_H = 0x8080808080808080
FILE_AB = FILE_A | FILE_B
FILE_GH = FILE_G | FILE_H

# rank masks
RANK_1 = 0x00000000000000FF
RANK_2 = 0x000000000000FF00
RANK_3 = 0x0000000000FF0000
RANK_4 = 0x00000000FF000000
RANK_5 = 0x000000FF00000000
RANK_6 = 0x0000FF0000000000
RANK_7 = 0x00FF000000000000
RANK_8 = 0xFF00000000000000

# board masks
FULL_BOARD = 0xFFFFFFFFFFFFFFFF
EMPTY_BOARD = 0x0000000000000000
SQUARE_TO_BB = [1 << square for square in range(64)]

# square indices
A1, B1, C1, D1, E1, F1, G1, H1 = 0, 1, 2, 3, 4, 5, 6, 7
A2, B2, C2, D2, E2, F2, G2, H2 = 8, 9, 10, 11, 12, 13, 14, 15
A3, B3, C3, D3, E3, F3, G3, H3 = 16, 17, 18, 19, 20, 21, 22, 23
A4, B4, C4, D4, E4, F4, G4, H4 = 24, 25, 26, 27, 28, 29, 30, 31
A5, B5, C5, D5, E5, F5, G5, H5 = 32, 33, 34, 35, 36, 37, 38, 39
A6, B6, C6, D6, E6, F6, G6, H6 = 40, 41, 42, 43, 44, 45, 46, 47
A7, B7, C7, D7, E7, F7, G7, H7 = 48, 49, 50, 51, 52, 53, 54, 55
A8, B8, C8, D8, E8, F8, G8, H8 = 56, 57, 58, 59, 60, 61, 62, 63

# move encoding masks
MASK_SOURCE = 0b0000000000111111
MASK_TARGET = 0b0000111111000000
MASK_FLAG   = 0b1111000000000000

# bit manipulation
FLIP_BOARD = 56 # XOR to mirror board

# directional offsets
NORTH = 8
SOUTH = -NORTH
EAST  = 1
WEST  = -EAST

# search configuration
MAX_DEPTH = 100
TIME_CHECK_NODES = 1023
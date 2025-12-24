NAME = 'Indigo'
AUTHOR = '@rishabhkarwal'

# board state
WHITE = True
BLACK = False
NO_SQUARE = -1

# castling rights bitmask
CASTLE_WK = 1 # 0001
CASTLE_WQ = 2 # 0010
CASTLE_BK = 4 # 0100
CASTLE_BQ = 8 # 1000

# evaluation
INFINITY = 100_000
MATE = 100_000  # mate score

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

# square indices
A1, B1, C1, D1, E1, F1, G1, H1 = 0, 1, 2, 3, 4, 5, 6, 7
A2, B2, C2, D2, E2, F2, G2, H2 = 8, 9, 10, 11, 12, 13, 14, 15
A3, B3, C3, D3, E3, F3, G3, H3 = 16, 17, 18, 19, 20, 21, 22, 23
A4, B4, C4, D4, E4, F4, G4, H4 = 24, 25, 26, 27, 28, 29, 30, 31
A5, B5, C5, D5, E5, F5, G5, H5 = 32, 33, 34, 35, 36, 37, 38, 39
A6, B6, C6, D6, E6, F6, G6, H6 = 40, 41, 42, 43, 44, 45, 46, 47
A7, B7, C7, D7, E7, F7, G7, H7 = 48, 49, 50, 51, 52, 53, 54, 55
A8, B8, C8, D8, E8, F8, G8, H8 = 56, 57, 58, 59, 60, 61, 62, 63

# piece characters
PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING = 'P', 'N', 'B', 'R', 'Q', 'K'

# white pieces
WP, WN, WB, WR, WQ, WK = [piece.upper() for piece in [PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING]]

# black pieces
BP, BN, BB, BR, BQ, BK = [piece.lower() for piece in [PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING]]

# piece groupings
WHITE_PIECES = (WP, WN, WB, WR, WQ, WK)
BLACK_PIECES = (BP, BN, BB, BR, BQ, BK)
ALL_PIECES = WHITE_PIECES + BLACK_PIECES

# bitboard string keys
WHITE_STR = 'white'
BLACK_STR = 'black'
ALL_STR = 'all'

# move encoding masks
MASK_SOURCE = 0b0000000000111111 # 6 bits for source square
MASK_TARGET = 0b0000111111000000 # 6 bits for target square
MASK_FLAG   = 0b1111000000000000 # 4 bits for move flags

# bit manipulation
FLIP_BOARD = 56  # XOR to flip rank for FEN parsing

# directional offsets
NORTH = 8
SOUTH = -NORTH
EAST  = 1
WEST  = -EAST

# search configuration
MAX_DEPTH = 100 # maximum search depth
TIME_CHECK_NODES = 2047 # check time every N nodes
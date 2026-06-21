from engine.core.constants import PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING

PIECE_VALUES = {
    PAWN: 100,
    KNIGHT: 305,
    BISHOP: 333,
    ROOK: 563,
    QUEEN: 950,
    KING: 20000,
}

# PeSTO material values
MG_VALUES = {PAWN: 82, KNIGHT: 337, BISHOP: 365, ROOK: 477, QUEEN: 1025, KING: 0}
EG_VALUES = {PAWN: 94, KNIGHT: 281, BISHOP: 297, ROOK: 512, QUEEN: 936, KING: 0}

# game phase increments
PHASE_INC = {PAWN: 0, KNIGHT: 1, BISHOP: 1, ROOK: 2, QUEEN: 4, KING: 0}

# pawn structure
DOUBLED_PAWN_PENALTY = 10
ISOLATED_PAWN_PENALTY = 15
PASSED_PAWN_BONUS = [0, 10, 17, 15, 62, 168, 276, 0]

# knight positioning
KNIGHT_OUTPOST_BONUS = 10
KNIGHT_OUTPOST_RANKS_W = (4, 6)
KNIGHT_OUTPOST_RANKS_B = (2, 4)

# rook positioning
ROOK_ON_SEVENTH_RANK = 12
ROOK_BEHIND_PASSED_PAWN = 10

# piece mobility
TRAPPED_PIECE_PENALTY = 50

# piece coordination
ROOK_BATTERY_BONUS = 15
QUEEN_ROOK_BATTERY_BONUS = 15
DIAGONAL_BATTERY_SCALE = 0.5

# king safety
KING_PAWN_SHIELD_BONUS = 5
KING_SHIELD_HOME_RANK_MAX = 1
KING_SHIELD_FAR_RANK_MIN = 6
KING_SHIELD_SCAN_RANKS = 2

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

# trading behaviour
WINNING_THRESHOLD = 200
LOSING_THRESHOLD = -100
TRADE_BONUS_PER_PIECE = 20
TRADE_PENALTY_PER_PIECE = 25

# contempt
CONTEMPT = 100
LOSING_CONTEMPT_SCALE = 0.5

# repetition penalties
REPETITION_PENALTY_WINNING = 500
REPETITION_PENALTY_EQUAL = 100
REPETITION_PENALTY_SLIGHT = 150

# contempt thresholds
SLIGHTLY_BETTER_THRESHOLD = 100
CLEARLY_WINNING_THRESHOLD = 300
CLEARLY_LOSING_THRESHOLD = -300

# 50-move rule contempt
FIFTY_MOVE_CONTEMPT_BASE = 50
FIFTY_MOVE_SCALE_START = 90

# pruning margins
RAZOR_MARGIN = [0, 240, 280, 300]
STATIC_NULL_MARGIN = 120
FUTILITY_MARGIN = [0, 100, 180, 270]

# late move reductions
LMR_BASE_REDUCTION = 1
LMR_MOVE_THRESHOLD = 3
LMR_MIN_DEPTH = 3
LMR_NON_PV_REDUCTION = 1
LMR_CHECK_PRESSURE_DECREMENT = 1

# endgame phase-transition extension
PHASE_TRANSITION_EXTENSION = 1

# late move pruning
LMP_BASE = 3
LMP_MULTIPLIER = 2

# null move pruning
NMP_BASE_REDUCTION = 2
NMP_DEPTH_REDUCTION = 3
NMP_MIN_DEPTH = 3
NMP_DEEP_DEPTH = 6
NMP_EVAL_MARGIN = 200
NMP_EVAL_EXTRA_REDUCTION = 1

# extensions
CHECK_EXTENSION = 1
SINGULAR_EXTENSION = 0
SINGULAR_MARGIN = 50

# move ordering score bands
SCORE_TT_MOVE      = 2_000_000_000
SCORE_GOOD_CAP     = 1_000_000_000
SCORE_COUNTER_MOVE =   900_000_000
SCORE_KILLER_1     =   800_000_000
SCORE_KILLER_2     =   700_000_000
SCORE_BAD_CAP      =  -100_000_000
MOVE_REPETITION_PENALTY = -25
MVV_LVA_MULTIPLIER = 10

# aspiration windows
ASPIRATION_MIN          = 35
ASPIRATION_MAX          = 500
ASPIRATION_INIT_SCALE   = 0.8
ASPIRATION_WIDEN_FACTOR = 2
ASPIRATION_STABILITY_COUNT = 3
ASPIRATION_TIGHTEN_SCALE   = 0.8
ASPIRATION_MIN_DEPTH    = 2

# time management
TIME_HARD_LIMIT_FACTOR    = 1.5
TIME_HARD_LIMIT_OFFSET    = 0.5
TIME_CHECK_SWITCH         = 10_000
TIME_CHECK_TIGHT          = 255
TIME_USAGE_LONG           = 0.7
TIME_USAGE_SHORT          = 0.9
TIME_USAGE_TC_THRESHOLD   = 120_000
MATE_SCORE_MARGIN         = 1000
TIME_PRESSURE_THRESHOLD   = 10_000

# syzygy scoring
TB_WIN_SCORE_MARGIN = 1000

# IID
IID_MIN_DEPTH       = 4
IID_DEPTH_REDUCTION = 2

# LMR extra reduction
LMR_HEAVY_THRESHOLD = 10
LMR_HEAVY_REDUCTION = 2

# pruning depth caps
RAZORING_DEPTH_CAP    = 3
RFP_DEPTH_CAP         = 3
SNMP_DEPTH_CAP        = 3
FUTILITY_DEPTH_CAP    = 3
LMP_DEPTH_CAP         = 4
SEE_PRUNING_DEPTH_CAP = 6

# reverse futility pruning margin (per depth)
REVERSE_FUTILITY_MARGIN = 120

# evaluation phase gates (fraction of max phase)
PHASE_GATE_DOUBLED_PAWNS = 0.8
PHASE_GATE_KING_SAFETY   = 0.6
PHASE_GATE_MOBILITY      = 0.5
PHASE_GATE_KING_ENDGAME  = 0.4

# mop-up evaluation
MOP_UP_ACTIVATION      = 200
MOP_UP_CENTRE_WEIGHT   = 4
MOP_UP_DISTANCE_WEIGHT = 2
MOP_UP_MAX_DISTANCE    = 14

# trading evaluation
TRADING_STARTING_PIECES = 24

# time management
DEFAULT_TIME_LIMIT    = 2000
MOVES_TO_GO_MIN       = 20
MOVES_TO_GO_LOOKBACK  = 50
INCREMENT_FRACTION    = 0.5
LOW_TIME_THRESHOLD    = 10_000
LOW_TIME_DIVISOR      = 5
MOVE_OVERHEAD         = 200
PONDERHIT_HARD_FACTOR = 1.5
PONDERHIT_HARD_OFFSET = 0.5

# piece-square tables (mg = middlegame, eg = endgame)
MG_PAWN = [
      0,   0,   0,   0,   0,   0,   0,   0,
     98, 134,  61,  95,  68, 126,  34, -11,
     -6,   7,  26,  31,  65,  56,  25, -20,
    -14,  13,   6,  21,  23,  12,  17, -23,
    -27,  -2,  -5,  12,  17,   6,  10, -25,
    -26,  -4,  -4, -10,   3,   3,  33, -12,
    -35,  -1, -20, -23, -15,  24,  38, -22,
      0,   0,   0,   0,   0,   0,   0,   0,
]

EG_PAWN = [
      0,   0,   0,   0,   0,   0,   0,   0,
    178, 173, 158, 134, 147, 132, 165, 187,
     94, 100,  85,  67,  56,  53,  82,  84,
     32,  24,  13,   5,  -2,   4,  17,  17,
     13,   9,  -3,  -7,  -7,  -8,   3,  -1,
      4,   7,  -6,   1,   0,  -5,  -1,  -8,
     13,   8,   8,  10,  13,   0,   2,  -7,
      0,   0,   0,   0,   0,   0,   0,   0,
]

MG_KNIGHT = [
   -167, -89, -34, -49,  61, -97, -15, -107,
    -73, -41,  72,  36,  23,  62,   7, -17,
    -47,  60,  37,  65,  84, 129,  73,  44,
     -9,  17,  19,  53,  37,  69,  18,  22,
    -13,   4,  16,  13,  28,  19,  21,  -8,
    -23,  -9,  12,  10,  19,  17,  25, -16,
    -29, -53, -12,  -3,  -1,  18, -14, -19,
   -105, -21, -58, -33, -17, -28, -19, -23,
]

EG_KNIGHT = [
    -58, -38, -13, -28, -31, -27, -63, -99,
    -25,  -8, -25,  -2,  -9, -25, -24, -52,
    -24, -20,  10,   9,  -1,  -9, -19, -41,
    -17,   3,  22,  22,  22,  11,   8, -18,
    -18,  -6,  16,  25,  16,  17,   4, -18,
    -23,  -3,  -1,  15,  10,  -3, -20, -22,
    -42, -20, -10,  -5,  -2, -20, -23, -44,
    -29, -51, -23, -15, -22, -18, -50, -64,
]

MG_BISHOP = [
    -29,   4, -82, -37, -25, -42,   7,  -8,
    -26,  16, -18, -13,  30,  59,  18, -47,
    -16,  37,  43,  40,  35,  50,  37,  -2,
     -4,   5,  19,  50,  37,  37,   7,  -2,
     -6,  13,  13,  26,  34,  12,  10,   4,
      0,  15,  15,  15,  14,  27,  18,  10,
      4,  15,  16,   0,   7,  21,  33,   1,
    -33,  -3, -14, -21, -13, -12, -39, -21,
]

EG_BISHOP = [
    -14, -21, -11,  -8,  -7,  -9, -17, -24,
     -8,  -4,   7, -12,  -3, -13,  -4, -14,
      2,  -8,   0,  -1,  -2,   6,   0,   4,
     -3,   9,  12,   9,  14,  10,   3,   2,
     -6,   3,  13,  19,   7,  10,  -3,  -9,
    -12,  -3,   8,  10,  13,   3,  -7, -15,
    -14, -18,  -7,  -1,   4,  -9, -15, -27,
    -23,  -9, -23,  -5,  -9, -16,  -5, -17,
]

MG_ROOK = [
     32,  42,  32,  51,  63,   9,  31,  43,
     27,  32,  58,  62,  80,  67,  26,  44,
     -5,  19,  26,  36,  17,  45,  61,  16,
    -24, -11,   7,  26,  24,  35,  -8, -20,
    -36, -26, -12,  -1,   9,  -7,   6, -23,
    -45, -25, -16, -17,   3,   0,  -5, -33,
    -44, -16, -20,  -9,  -1,  11,  -6, -71,
    -19, -13,   1,  17,  16,   7, -37, -26,
]

EG_ROOK = [
     13,  10,  18,  15,  12,  12,   8,   5,
     11,  13,  13,  11,  -3,   3,   8,   3,
      7,   7,   7,   5,   4,  -3,  -5,  -3,
      4,   3,  13,   1,   2,   1,  -1,   2,
      3,   5,   8,   4,  -5,  -6,  -8, -11,
     -4,   0,  -5,  -1,  -7, -12,  -8, -16,
     -6,  -6,   0,   2,  -9,  -9, -11,  -3,
     -9,   2,   3,  -1,  -5, -13,   4, -20,
]

MG_QUEEN = [
    -28,   0,  29,  12,  59,  44,  43,  45,
    -24, -39,  -5,   1, -16,  57,  28,  54,
    -13, -17,   7,   8,  29,  56,  47,  57,
    -27, -27, -16, -16,  -1,  17,  -2,   1,
     -9, -26,  -9, -10,  -2,  -4,   3,  -3,
    -14,   2, -11,  -2,  -5,   2,  14,   5,
    -35,  -8,  11,   2,   8,  15,  -3,   1,
     -1, -18,  -9,  10, -15, -25, -31, -50,
]

EG_QUEEN = [
     -9,  22,  22,  27,  27,  19,  10,  20,
    -17,  20,  32,  41,  58,  25,  30,   0,
    -20,   6,   9,  49,  47,  35,  19,   9,
      3,  22,  24,  45,  57,  40,  57,  36,
    -18,  28,  19,  47,  31,  34,  39,  23,
    -16, -27,  15,   6,   9,  17,  10,   5,
    -22, -23, -30, -16, -16, -23, -36, -32,
    -33, -28, -22, -43,  -5, -32, -20, -41,
]

MG_KING = [
    -65,  23,  16, -15, -56, -34,   2,  13,
     29,  -1, -20,  -7,  -8,  -4, -38, -29,
     -9,  24,   2, -16, -20,   6,  22, -22,
    -17, -20, -12, -27, -30, -25, -14, -36,
    -49,  -1, -27, -39, -46, -44, -33, -51,
    -14, -14, -22, -46, -44, -30, -15, -27,
      1,   7,  -8, -64, -43, -16,   9,   8,
    -15,  36,  12, -54,   8, -28,  24,  14,
]

EG_KING = [
    -74, -35, -18, -18, -11,  15,   4, -17,
    -12,  17,  14,  17,  17,  38,  23,  11,
     10,  17,  23,  15,  20,  45,  44,  13,
     -8,  22,  24,  27,  26,  33,  26,   3,
    -18,  -4,  21,  24,  27,  23,   9, -11,
    -19,  -3,  11,  21,  23,  16,   7,  -9,
    -27, -11,   4,  13,  14,   4,  -5, -17,
    -53, -34, -21, -11, -28, -14, -24, -43,
]

PSQTs = {
    PAWN:   (MG_PAWN,   EG_PAWN),
    KNIGHT: (MG_KNIGHT, EG_KNIGHT),
    BISHOP: (MG_BISHOP, EG_BISHOP),
    ROOK:   (MG_ROOK,   EG_ROOK),
    QUEEN:  (MG_QUEEN,  EG_QUEEN),
    KING:   (MG_KING,   EG_KING),
}

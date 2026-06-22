import json
import os

from engine.core.constants import PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING

PIECE_VALUES = {
    PAWN: 100,
    KNIGHT: 305,
    BISHOP: 333,
    ROOK: 563,
    QUEEN: 950,
    KING: 20000,
}

# tuned material values
MG_VALUES = {PAWN: 78, KNIGHT: 347, BISHOP: 369, ROOK: 491, QUEEN: 1041, KING: 0}
EG_VALUES = {PAWN: 94, KNIGHT: 281, BISHOP: 301, ROOK: 526, QUEEN: 954, KING: 0}

# game phase increments
PHASE_INC = {PAWN: 0, KNIGHT: 1, BISHOP: 1, ROOK: 2, QUEEN: 4, KING: 0}

# pawn structure
DOUBLED_PAWN_PENALTY = 14
ISOLATED_PAWN_PENALTY = 15
PASSED_PAWN_BONUS = [0, 14, 17, 24, 50, 145, 253, 0]

# knight positioning
KNIGHT_OUTPOST_BONUS = 24
KNIGHT_OUTPOST_RANKS_W = (4, 6)
KNIGHT_OUTPOST_RANKS_B = (2, 4)

# rook positioning
ROOK_ON_SEVENTH_RANK = 15
ROOK_BEHIND_PASSED_PAWN = 10

# piece mobility
TRAPPED_PIECE_PENALTY = 27

# piece coordination
ROOK_BATTERY_BONUS = 10
QUEEN_ROOK_BATTERY_BONUS = 5
DIAGONAL_BATTERY_SCALE = 0.0

# king safety
KING_PAWN_SHIELD_BONUS = 10
KING_SHIELD_HOME_RANK_MAX = 1
KING_SHIELD_FAR_RANK_MIN = 6
KING_SHIELD_SCAN_RANKS = 2

# king activity (endgame)
KING_TO_CENTRE_BONUS = 3
KING_TO_ENEMY_PAWNS_BONUS = 10

# core features
BISHOP_PAIR_BONUS = 30
ROOK_OPEN_FILE = 20
ROOK_SEMI_OPEN_FILE = 10

# mobility bonuses (per legal square)
KNIGHT_MOBILITY = 5
BISHOP_MOBILITY = 5
ROOK_MOBILITY = 6
QUEEN_MOBILITY = 2

# trading behaviour
WINNING_THRESHOLD = 186
LOSING_THRESHOLD = -100
TRADE_BONUS_PER_PIECE = 10
TRADE_PENALTY_PER_PIECE = 10

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
RAZOR_MARGIN = [0, 488, 684, 708]
STATIC_NULL_MARGIN = 262
FUTILITY_MARGIN = [0, 554, 704, 715]

# late move reductions
LMR_BASE_REDUCTION = 1
LMR_MOVE_THRESHOLD = 4
LMR_MIN_DEPTH = 2
LMR_NON_PV_REDUCTION = 1

# endgame phase-transition extension
PHASE_TRANSITION_EXTENSION = 1

# late move pruning
LMP_BASE = 4
LMP_MULTIPLIER = 1

# null move pruning
NMP_BASE_REDUCTION = 2
NMP_DEPTH_REDUCTION = 3
NMP_MIN_DEPTH = 3
NMP_DEEP_DEPTH = 8
NMP_EVAL_MARGIN = 194
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
MOVE_REPETITION_PENALTY = -2
MVV_LVA_MULTIPLIER = 10

# aspiration windows
ASPIRATION_MIN          = 96
ASPIRATION_MAX          = 416
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
IID_MIN_DEPTH       = 7
IID_DEPTH_REDUCTION = 2

# LMR extra reduction
LMR_HEAVY_THRESHOLD = 20
LMR_HEAVY_REDUCTION = 2

# pruning depth caps
RAZORING_DEPTH_CAP    = 3
RFP_DEPTH_CAP         = 3
SNMP_DEPTH_CAP        = 3
FUTILITY_DEPTH_CAP    = 3
LMP_DEPTH_CAP         = 4
SEE_PRUNING_DEPTH_CAP = 3

# reverse futility pruning margin (per depth)
REVERSE_FUTILITY_MARGIN = 141

# evaluation phase gates (fraction of max phase)
PHASE_GATE_DOUBLED_PAWNS = 0.78
PHASE_GATE_KING_SAFETY   = 0.56
PHASE_GATE_MOBILITY      = 0.45
PHASE_GATE_KING_ENDGAME  = 0.46

# mop-up evaluation
MOP_UP_ACTIVATION      = 197
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
       0,    0,    0,    0,    0,    0,    0,    0,
      75,  111,   43,   74,   45,  103,   20,  -28,
     -24,  -13,    4,   10,   44,   60,   33,  -26,
     -20,   -1,   -8,   35,   38,    9,   11,  -34,
     -36,   -3,    1,   29,   22,    6,    4,  -32,
     -28,   -6,   -2,  -23,   -3,    5,   25,   -8,
     -23,    9,  -16,  -21,   -1,   36,   52,   -8,
       0,    0,    0,    0,    0,    0,    0,    0,
]

EG_PAWN = [
       0,    0,    0,    0,    0,    0,    0,    0,
     159,  150,  136,  113,  124,  109,  161,  165,
      75,   78,   63,   45,   33,   39,   62,   66,
      36,   12,    0,   -5,   -1,   14,   17,   12,
       7,   12,   -1,    2,    1,   -6,    9,   -1,
       4,    7,   -4,   -2,    0,   -3,   -9,   -8,
       5,   16,   16,   11,   19,   10,   10,    1,
       0,    0,    0,    0,    0,    0,    0,    0,
]

MG_KNIGHT = [
    -162,  -94,  -38,  -64,   59, -113,    6,  -93,
     -53,  -33,   60,   27,    6,   75,   12,    2,
     -31,   77,   33,   75,   67,  141,   78,   24,
      -9,   31,   19,   60,   49,   86,   35,   36,
      -6,   21,   27,   11,   36,   38,   20,  -22,
     -35,  -17,   20,   19,   32,   27,   26,  -28,
     -42,  -57,   -7,   -8,   -7,   11,  -26,  -26,
    -128,  -31,  -42,  -34,  -22,  -40,  -20,  -46,
]

EG_KNIGHT = [
     -49,  -26,  -34,  -34,  -42,  -29,  -49,  -85,
     -32,   -4,  -36,   -7,   -1,  -18,   -9,  -31,
      -7,  -21,   12,    8,    0,  -15,  -22,  -53,
      -3,    3,   12,   39,   36,   26,   16,   -1,
      -4,    7,   17,   17,   25,   15,   14,  -21,
     -20,   -3,   -5,   22,   14,  -11,   -4,  -35,
     -32,   -1,   -7,    2,    3,   -4,  -32,  -45,
     -52,  -42,   -2,   -5,  -26,  -16,  -40,  -47,
]

MG_BISHOP = [
     -25,    0,  -99,  -44,  -27,  -49,   20,   14,
     -18,    7,  -13,   -6,   10,   57,   28,  -38,
       1,   36,   41,   37,   53,   50,   53,    7,
       3,   23,   29,   58,   49,   48,   12,   11,
      11,   22,   26,   36,   42,   12,   18,   -4,
      -5,   29,   14,   23,   21,   22,   32,   20,
      12,    3,   30,   -4,   -1,   18,   37,   16,
     -41,    8,  -12,  -22,  -12,  -26,  -20,  -35,
]

EG_BISHOP = [
     -28,  -22,    9,  -17,   -7,   -9,   -3,  -34,
     -11,  -20,    5,    1,    5,   -6,   -4,   -9,
      15,  -10,   10,   -1,   -4,    8,   -5,    9,
     -23,   12,   26,   13,   26,   22,    1,   -1,
       5,    6,   23,   27,   13,   11,    4,  -19,
     -17,   -2,   16,    9,   24,    2,    2,    0,
     -13,  -17,   -1,  -10,    0,  -12,   -5,  -17,
     -36,   -8,  -31,  -15,   -8,   -2,   17,   -4,
]

MG_ROOK = [
      24,   37,   38,   55,   61,   19,   41,   39,
      28,   18,   48,   56,   73,   68,   14,   45,
      -2,   19,   33,   40,   19,   54,   76,   22,
     -29,    3,    2,   33,   26,   55,   -6,   -5,
     -30,  -20,  -17,   -6,    7,   -1,   20,  -19,
     -50,  -18,  -15,  -33,    5,    0,   -9,  -30,
     -47,  -23,  -32,  -23,   -6,    5,   -6,  -78,
     -19,   -7,   -3,   17,   20,   19,  -36,  -36,
]

EG_ROOK = [
      27,    6,   22,    3,   11,   18,   13,    4,
      14,    3,   11,    4,   -7,    1,   -7,    4,
      12,   14,   15,   -6,    2,    1,  -13,    3,
      13,   19,   21,   14,    5,    4,   10,   15,
      11,   11,   12,   -6,    2,  -20,   -4,   -5,
       7,   -1,  -10,   -2,   -8,  -14,    3,  -24,
       2,  -10,   -1,   -9,  -22,    0,  -13,  -12,
      -9,    2,    3,   -1,   -5,   -5,    0,  -28,
]

MG_QUEEN = [
     -16,    2,   22,   19,   68,   60,   51,   59,
     -40,  -43,    0,    9,  -11,   65,   25,   39,
     -20,  -13,   22,   26,   45,   66,   63,   66,
     -15,  -25,   -8,    2,   11,   31,    2,   14,
      -6,  -18,   -4,    7,   10,    6,    9,   -8,
     -30,    5,   -4,   11,   -1,    6,   14,   -4,
     -49,   -7,   11,  -11,    4,   11,   -8,  -11,
     -14,  -31,  -11,   11,  -26,  -40,  -43,  -63,
]

EG_QUEEN = [
       7,   32,    9,   26,   29,   34,    8,   37,
     -13,   27,   33,   36,   69,   38,   31,   -6,
      -6,   18,   11,   63,   54,   35,   30,   24,
       2,   24,   39,   59,   69,   49,   68,   50,
     -12,   27,   32,   55,   47,   48,   44,   28,
     -34,  -29,   29,    8,    9,    9,    7,   -8,
     -41,  -10,  -33,  -27,  -14,  -38,  -41,  -51,
     -34,  -40,  -30,  -44,   -6,  -50,  -38,  -53,
]

MG_KING = [
     -78,   13,   -7,  -37,  -63,  -46,   -5,   -5,
      28,   14,  -38,   -1,  -16,   -3,  -24,  -21,
     -26,    2,   -6,  -18,  -24,   20,   14,  -33,
     -15,  -27,  -15,  -35,  -39,  -24,  -30,  -46,
     -36,   -2,  -42,  -46,  -33,  -35,  -38,  -56,
     -17,  -18,  -30,  -54,  -49,  -41,  -13,  -26,
       6,  -12,  -10,  -73,  -55,  -27,    8,    8,
     -12,   34,    4,  -72,    0,  -43,   36,   20,
]

EG_KING = [
     -93,  -58,  -41,  -41,   -2,   -2,   -6,  -32,
     -23,   28,    4,   40,    9,   34,   28,    1,
       8,    0,   29,   24,   28,   39,   39,    9,
      -9,   17,   37,   17,   17,   22,   20,   -1,
     -13,   -7,   10,   17,   27,   23,    3,  -21,
     -22,   -6,    1,   23,   23,   19,    5,  -16,
     -16,  -18,    3,   18,   14,    4,   -1,   -9,
     -46,  -24,  -21,   -7,  -36,  -29,  -16,  -37,
]

PSQTs = {
    PAWN:   (MG_PAWN,   EG_PAWN),
    KNIGHT: (MG_KNIGHT, EG_KNIGHT),
    BISHOP: (MG_BISHOP, EG_BISHOP),
    ROOK:   (MG_ROOK,   EG_ROOK),
    QUEEN:  (MG_QUEEN,  EG_QUEEN),
    KING:   (MG_KING,   EG_KING),
}

_MATERIAL_PARAM_TARGETS = {
    "mg_pawn":   (MG_VALUES, PAWN),
    "mg_knight": (MG_VALUES, KNIGHT),
    "mg_bishop": (MG_VALUES, BISHOP),
    "mg_rook":   (MG_VALUES, ROOK),
    "mg_queen":  (MG_VALUES, QUEEN),
    "eg_pawn":   (EG_VALUES, PAWN),
    "eg_knight": (EG_VALUES, KNIGHT),
    "eg_bishop": (EG_VALUES, BISHOP),
    "eg_rook":   (EG_VALUES, ROOK),
    "eg_queen":  (EG_VALUES, QUEEN),
}

_TUNE_PARAM_ALIASES = {
    "doubled_pawn_penalty":     "DOUBLED_PAWN_PENALTY",
    "isolated_pawn_penalty":    "ISOLATED_PAWN_PENALTY",
    "knight_outpost_bonus":     "KNIGHT_OUTPOST_BONUS",
    "rook_on_seventh_rank":     "ROOK_ON_SEVENTH_RANK",
    "rook_behind_passed_pawn":  "ROOK_BEHIND_PASSED_PAWN",
    "rook_battery_bonus":       "ROOK_BATTERY_BONUS",
    "queen_rook_battery_bonus": "QUEEN_ROOK_BATTERY_BONUS",
    "diagonal_battery_scale":   "DIAGONAL_BATTERY_SCALE",
    "rook_open_file":           "ROOK_OPEN_FILE",
    "rook_semi_open_file":      "ROOK_SEMI_OPEN_FILE",
    "bishop_pair_bonus":        "BISHOP_PAIR_BONUS",
    "trapped_piece_penalty":    "TRAPPED_PIECE_PENALTY",
    "knight_mobility":          "KNIGHT_MOBILITY",
    "bishop_mobility":          "BISHOP_MOBILITY",
    "rook_mobility":            "ROOK_MOBILITY",
    "queen_mobility":           "QUEEN_MOBILITY",
    "king_pawn_shield_bonus":   "KING_PAWN_SHIELD_BONUS",
    "king_to_centre_bonus":     "KING_TO_CENTRE_BONUS",
    "king_to_enemy_pawns_bonus": "KING_TO_ENEMY_PAWNS_BONUS",
    "trade_bonus_per_piece":    "TRADE_BONUS_PER_PIECE",
    "trade_penalty_per_piece":  "TRADE_PENALTY_PER_PIECE",
    "winning_threshold":        "WINNING_THRESHOLD",
    "losing_threshold":         "LOSING_THRESHOLD",
    "mop_up_activation":        "MOP_UP_ACTIVATION",
    "mop_up_centre_weight":     "MOP_UP_CENTRE_WEIGHT",
    "mop_up_distance_weight":   "MOP_UP_DISTANCE_WEIGHT",
    "phase_gate_doubled_pawns": "PHASE_GATE_DOUBLED_PAWNS",
    "phase_gate_king_safety":   "PHASE_GATE_KING_SAFETY",
    "phase_gate_mobility":      "PHASE_GATE_MOBILITY",
    "phase_gate_king_endgame":  "PHASE_GATE_KING_ENDGAME",
}

_PASSED_PAWN_PARAM_NAMES = [
    "passed_pawn_rank2",
    "passed_pawn_rank3",
    "passed_pawn_rank4",
    "passed_pawn_rank5",
    "passed_pawn_rank6",
    "passed_pawn_rank7",
]


def _set_tune_value(name, value):
    old_value = globals().get(name)
    if isinstance(old_value, list) and isinstance(value, list):
        old_value[:] = value
    elif isinstance(old_value, dict) and isinstance(value, dict):
        old_value.clear()
        old_value.update(value)
    else:
        globals()[name] = value


def _apply_tune_params(data):
    if not isinstance(data, dict): return

    for section in ["params", "scalars", "phase_thresholds", "floats"]:
        values = data.get(section)
        if isinstance(values, dict): _apply_tune_params(values)

    psqt = data.get("psqt")
    if isinstance(psqt, dict):
        for name, values in psqt.items():
            attr = name.upper()
            if attr in globals() and isinstance(globals()[attr], list):
                globals()[attr][:] = values

    if all(name in data for name in _PASSED_PAWN_PARAM_NAMES):
        PASSED_PAWN_BONUS[:] = [0] + [data[name] for name in _PASSED_PAWN_PARAM_NAMES] + [0]

    for name, value in data.items():
        if name in {"params", "scalars", "phase_thresholds", "floats", "psqt", "mse", "K", "scale", "score_fraction"}:
            continue
        if name in _MATERIAL_PARAM_TARGETS:
            target, piece = _MATERIAL_PARAM_TARGETS[name]
            target[piece] = value
            continue
        const_name = _TUNE_PARAM_ALIASES.get(name, name)
        if const_name in globals(): _set_tune_value(const_name, value)


def _load_tune_params_from_env():
    params_path = os.environ.get("SOPHIA_TUNE_PARAMS")
    if not params_path: return
    with open(params_path) as f:
        _apply_tune_params(json.load(f))


_load_tune_params_from_env()

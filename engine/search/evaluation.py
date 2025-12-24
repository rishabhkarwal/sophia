from engine.core.constants import (
    WHITE, BLACK,
    FILE_A,
    PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
    WP, WN, WB, WR, WQ, WK,
    BP, BN, BB, BR, BQ, BK,
    ALL_STR, FLIP_BOARD
)
from engine.moves.precomputed import (
    KNIGHT_ATTACKS,
    KING_ATTACKS,
    BISHOP_MASKS,
    BISHOP_TABLE,
    ROOK_MASKS,
    ROOK_TABLE
)
from engine.search.psqt import (
    MG_PAWN, EG_PAWN,
    MG_KNIGHT, EG_KNIGHT,
    MG_BISHOP, EG_BISHOP,
    MG_ROOK, EG_ROOK,
    MG_QUEEN, EG_QUEEN,
    MG_KING, EG_KING
)

"""PeSTO Evaluation Function"""

# Piece values
MG_VALUES = {PAWN: 82, KNIGHT: 337, BISHOP: 365, ROOK: 477, QUEEN: 1025, KING: 0}
EG_VALUES = {PAWN: 94, KNIGHT: 281, BISHOP: 297, ROOK: 512, QUEEN: 936, KING: 0}

# Game phase increments
PHASE_INC = {PAWN: 0, KNIGHT: 1, BISHOP: 1, ROOK: 2, QUEEN: 4, KING: 0}
MAX_PHASE = 4 * PHASE_INC[KNIGHT] + 4 * PHASE_INC[BISHOP] + 4 * PHASE_INC[ROOK] + 2 * PHASE_INC[QUEEN]

PASSED_PAWN_BONUS = [0, 10, 17, 15, 62, 168, 276, 0]

ISOLATED_PAWN_PENALTY = -10
DOUBLED_PAWN_PENALTY = -12
BISHOP_PAIR_BONUS = 25
ROOK_OPEN_FILE = 10
ROOK_SEMI_OPEN_FILE = 5
CONNECTED_ROOKS_BONUS = 15

PSQTs = {
    PAWN: (MG_PAWN, EG_PAWN),
    KNIGHT: (MG_KNIGHT, EG_KNIGHT),
    BISHOP: (MG_BISHOP, EG_BISHOP),
    ROOK: (MG_ROOK, EG_ROOK),
    QUEEN: (MG_QUEEN, EG_QUEEN),
    KING: (MG_KING, EG_KING)
}

# Piece indices for array access
PIECE_INDICES = {
    WP: 0, WN: 1, WB: 2, WR: 3, WQ: 4, WK: 5,
    BP: 6, BN: 7, BB: 8, BR: 9, BQ: 10, BK: 11
}

MG_TABLE = [[0] * 64 for _ in range(12)]
EG_TABLE = [[0] * 64 for _ in range(12)]
PHASE_WEIGHTS = [0] * 12

PASSED_PAWN_MASKS = [[0] * 64 for _ in range(2)]
FILE_MASKS = [0] * 8
ADJACENT_FILE_MASKS = [0] * 8

def init_eval_tables():
    # white pieces (indices 0-5)
    for piece_type, (mg_val, eg_val) in PSQTs.items():
        white_piece = piece_type.upper()
        idx = PIECE_INDICES[white_piece]
        PHASE_WEIGHTS[idx] = PHASE_INC[piece_type]
        MG_TABLE[idx] = [MG_VALUES[piece_type] + val for val in mg_val]
        EG_TABLE[idx] = [EG_VALUES[piece_type] + val for val in eg_val]

    # black pieces (indices 6-11)
    for piece_type, (mg_val, eg_val) in PSQTs.items():
        black_piece = piece_type.lower()
        idx = PIECE_INDICES[black_piece]
        PHASE_WEIGHTS[idx] = PHASE_INC[piece_type]
        for sq in range(64):
            flipped_sq = sq ^ FLIP_BOARD
            MG_TABLE[idx][sq] = -(MG_VALUES[piece_type] + mg_val[flipped_sq])
            EG_TABLE[idx][sq] = -(EG_VALUES[piece_type] + eg_val[flipped_sq])
    
    # file masks
    for f in range(8):
        mask = FILE_A << f
        FILE_MASKS[f] = mask
        adj = 0
        if f > 0: adj |= FILE_A << (f - 1)
        if f < 7: adj |= FILE_A << (f + 1)
        ADJACENT_FILE_MASKS[f] = adj

    # passed pawn masks
    for sq in range(64):
        file, rank = sq % 8, sq // 8
        w_mask = 0
        for r in range(rank + 1, 8):
            for f_adj in range(max(0, file - 1), min(8, file + 2)):
                w_mask |= (1 << (r * 8 + f_adj))
        PASSED_PAWN_MASKS[WHITE][sq] = w_mask
        
        b_mask = 0
        for r in range(rank - 1, -1, -1):
            for f_adj in range(max(0, file - 1), min(8, file + 2)):
                b_mask |= (1 << (r * 8 + f_adj))
        PASSED_PAWN_MASKS[BLACK][sq] = b_mask

init_eval_tables()

def calculate_initial_score(state):
    mg, eg, phase = 0, 0, 0

    for piece_char, bb in state.bitboards.items():
        if piece_char not in PIECE_INDICES: continue

        p_idx = PIECE_INDICES[piece_char]
        count = bb.bit_count()
        phase += PHASE_WEIGHTS[p_idx] * count

        while bb:
            lsb = bb & -bb
            sq = lsb.bit_length() - 1
            mg += MG_TABLE[p_idx][sq]
            eg += EG_TABLE[p_idx][sq]
            bb &= bb - 1

    return mg, eg, phase

def get_mop_up_score(state, winning_colour):
    winning_king_bb = state.bitboards[WK if winning_colour == WHITE else BK]
    losing_king_bb = state.bitboards[BK if winning_colour == WHITE else WK]

    if not winning_king_bb or not losing_king_bb: return 0

    winning_sq = (winning_king_bb & -winning_king_bb).bit_length() - 1
    losing_sq = (losing_king_bb & -losing_king_bb).bit_length() - 1

    losing_rank, losing_file = losing_sq // 8, losing_sq % 8

    centre_dist = max(3 - losing_rank, losing_rank - 4) + max(3 - losing_file, losing_file - 4)

    mop_up = 4 * centre_dist

    winning_rank, winning_file = winning_sq // 8, winning_sq % 8

    dist_between_kings = abs(winning_rank - losing_rank) + abs(winning_file - losing_file)

    mop_up += 2 * (14 - dist_between_kings)

    return mop_up if winning_colour == WHITE else -mop_up

def evaluate(state):
    mg_phase = min(state.phase, MAX_PHASE)
    eg_phase = MAX_PHASE - mg_phase
    evaluation = (state.mg_score * mg_phase + state.eg_score * eg_phase) // MAX_PHASE
    
    bitboards = state.bitboards
    all_pieces = bitboards[ALL_STR]
    w_pawns = bitboards[WP]
    b_pawns = bitboards[BP]
    
    # bishop pair
    if bitboards[WB].bit_count() >= 2: evaluation += BISHOP_PAIR_BONUS
    if bitboards[BB].bit_count() >= 2: evaluation -= BISHOP_PAIR_BONUS

    # king Safety & pawn structure
    w_king_sq = (bitboards[WK] & -bitboards[WK]).bit_length() - 1 if bitboards[WK] else -1
    b_king_sq = (bitboards[BK] & -bitboards[BK]).bit_length() - 1 if bitboards[BK] else -1
    w_king_zone = KING_ATTACKS[w_king_sq] if w_king_sq != -1 else 0
    b_king_zone = KING_ATTACKS[b_king_sq] if b_king_sq != -1 else 0

    # white pawns & structure
    temp_w = w_pawns
    while temp_w:
        lsb = temp_w & -temp_w
        sq = lsb.bit_length() - 1
        f = sq % 8
        if not (PASSED_PAWN_MASKS[WHITE][sq] & b_pawns): evaluation += PASSED_PAWN_BONUS[sq // 8]
        if (w_pawns & FILE_MASKS[f]) != lsb: evaluation += DOUBLED_PAWN_PENALTY
        if not (w_pawns & ADJACENT_FILE_MASKS[f]): evaluation += ISOLATED_PAWN_PENALTY
        temp_w &= temp_w - 1

    # black pawns & structure
    temp_b = b_pawns
    while temp_b:
        lsb = temp_b & -temp_b
        sq = lsb.bit_length() - 1
        f = sq % 8
        if not (PASSED_PAWN_MASKS[BLACK][sq] & w_pawns): evaluation -= PASSED_PAWN_BONUS[7 - (sq // 8)]
        if (b_pawns & FILE_MASKS[f]) != lsb: evaluation -= DOUBLED_PAWN_PENALTY
        if not (b_pawns & ADJACENT_FILE_MASKS[f]): evaluation -= ISOLATED_PAWN_PENALTY
        temp_b &= temp_b - 1

    # rooks & mobility & king safety zone attacks
    for colour, p_keys in [(WHITE, [WN, WB, WR, WQ]), (BLACK, [BN, BB, BR, BQ])]:
        score_adj = 0
        enemy_pawns = b_pawns if colour == WHITE else w_pawns
        enemy_king_zone = b_king_zone if colour == WHITE else w_king_zone
        
        # connected rooks & open files
        rooks = bitboards[WR if colour == WHITE else BR]
        if rooks.bit_count() >= 2:
            r1 = (rooks & -rooks).bit_length() - 1
            r2 = (rooks & (rooks - 1)).bit_length() - 1
            if ROOK_TABLE[(r1, all_pieces & ROOK_MASKS[r1])] & (1 << r2): 
                score_adj += CONNECTED_ROOKS_BONUS
        
        temp_rooks = rooks
        while temp_rooks:
            sq = (temp_rooks & -temp_rooks).bit_length() - 1
            f = sq % 8
            if not (w_pawns & FILE_MASKS[f]) and not (b_pawns & FILE_MASKS[f]): 
                score_adj += ROOK_OPEN_FILE
            elif not (enemy_pawns & FILE_MASKS[f]): 
                score_adj += ROOK_SEMI_OPEN_FILE
            temp_rooks &= temp_rooks - 1

        # mobility & attacks
        for p_key in p_keys:
            pieces = bitboards[p_key]
            while pieces:
                sq = (pieces & -pieces).bit_length() - 1
                if p_key.upper() == KNIGHT: 
                    atts = KNIGHT_ATTACKS[sq]
                elif p_key.upper() == BISHOP: 
                    atts = BISHOP_TABLE[(sq, all_pieces & BISHOP_MASKS[sq])]
                elif p_key.upper() == ROOK: 
                    atts = ROOK_TABLE[(sq, all_pieces & ROOK_MASKS[sq])]
                else: 
                    atts = ROOK_TABLE[(sq, all_pieces & ROOK_MASKS[sq])] | BISHOP_TABLE[(sq, all_pieces & BISHOP_MASKS[sq])]
                
                score_adj += atts.bit_count()
                if atts & enemy_king_zone: 
                    score_adj += 15 * (atts & enemy_king_zone).bit_count()
                pieces &= pieces - 1
        
        evaluation += score_adj if colour == WHITE else -score_adj

    # mop up
    if mg_phase < int(MAX_PHASE * 0.4):
        score_no_mopup = evaluation if state.is_white else -evaluation
        if score_no_mopup > 200: 
            evaluation += get_mop_up_score(state, state.is_white)
        elif score_no_mopup < -200: 
            evaluation += get_mop_up_score(state, not state.is_white)
    
    return evaluation if state.is_white else -evaluation
from engine.core.constants import (
    WHITE, BLACK,
    FILE_A, INFINITY, PIECE_VALUES,
    PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
    WP, WN, WB, WR, WQ, WK,
    BP, BN, BB, BR, BQ, BK,
    WHITE, BLACK, FLIP_BOARD, SQUARE_TO_BB
)
from engine.search.psqt import PSQTs

# piece values
MG_VALUES = {PAWN: 82, KNIGHT: 337, BISHOP: 365, ROOK: 477, QUEEN: 1025, KING: 0}
EG_VALUES = {PAWN: 94, KNIGHT: 281, BISHOP: 297, ROOK: 512, QUEEN: 936, KING: 0}

# game phase increments
PHASE_INC = {PAWN: 0, KNIGHT: 1, BISHOP: 1, ROOK: 2, QUEEN: 4, KING: 0}
MAX_PHASE = 4 * PHASE_INC[KNIGHT] + 4 * PHASE_INC[BISHOP] + 4 * PHASE_INC[ROOK] + 2 * PHASE_INC[QUEEN]

# streamlined: keep only fast, high-impact features rather than overdoing it
BISHOP_PAIR_BONUS = 40
ROOK_OPEN_FILE = 8
ROOK_SEMI_OPEN_FILE = 4

# trading behaviour parameters (was too 'trade-happy')
WINNING_THRESHOLD = 150  # cp advantage to consider "winning"
LOSING_THRESHOLD = -150  # cp disadvantage to consider "losing"
TRADE_BONUS_PER_PIECE = 5  # bonus for trading when winning
TRADE_PENALTY_PER_PIECE = 8  # penalty for trading when losing


MG_TABLE = [[0] * 64 for _ in range(16)]
EG_TABLE = [[0] * 64 for _ in range(16)]
PHASE_WEIGHTS = [0] * 16

PASSED_PAWN_MASKS = [[0] * 64 for _ in range(2)]
FILE_MASKS = [0] * 8
ADJACENT_FILE_MASKS = [0] * 8

# pawn hash table
class PawnHashTable: # I don't really want a new file for this
    def __init__(self, size_mb=16):
        total_bytes = size_mb * 1024 * 1024
        self.size = total_bytes // 12
        self.table = [None] * self.size
    
    def probe(self, pawn_hash):
        idx = pawn_hash % self.size
        entry = self.table[idx]
        if entry and entry[0] == pawn_hash:
            return entry[1]
        return None
    
    def store(self, pawn_hash, score):
        idx = pawn_hash % self.size
        self.table[idx] = (pawn_hash, score)

def init_eval_tables():
    piece_type_map = {
        PAWN: (PAWN, MG_VALUES[PAWN], EG_VALUES[PAWN], PHASE_INC[PAWN]),
        KNIGHT: (KNIGHT, MG_VALUES[KNIGHT], EG_VALUES[KNIGHT], PHASE_INC[KNIGHT]),
        BISHOP: (BISHOP, MG_VALUES[BISHOP], EG_VALUES[BISHOP], PHASE_INC[BISHOP]),
        ROOK: (ROOK, MG_VALUES[ROOK], EG_VALUES[ROOK], PHASE_INC[ROOK]),
        QUEEN: (QUEEN, MG_VALUES[QUEEN], EG_VALUES[QUEEN], PHASE_INC[QUEEN]),
        KING: (KING, MG_VALUES[KING], EG_VALUES[KING], PHASE_INC[KING])
    }
    
    for p_type, (base_type, mg_val, eg_val, phase_inc) in piece_type_map.items():
        mg_psqt, eg_psqt = PSQTs[base_type]
        
        w_piece = WHITE | p_type
        PHASE_WEIGHTS[w_piece] = phase_inc
        MG_TABLE[w_piece] = [mg_val + val for val in mg_psqt]
        EG_TABLE[w_piece] = [eg_val + val for val in eg_psqt]
        
        b_piece = BLACK | p_type
        PHASE_WEIGHTS[b_piece] = phase_inc
        for sq in range(64):
            flipped_sq = sq ^ FLIP_BOARD
            MG_TABLE[b_piece][sq] = -(mg_val + mg_psqt[flipped_sq])
            EG_TABLE[b_piece][sq] = -(eg_val + eg_psqt[flipped_sq])
    
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
                w_mask |= SQUARE_TO_BB[r * 8 + f_adj]
        PASSED_PAWN_MASKS[WHITE][sq] = w_mask
        
        b_mask = 0
        for r in range(rank - 1, -1, -1):
            for f_adj in range(max(0, file - 1), min(8, file + 2)):
                b_mask |= SQUARE_TO_BB[r * 8 + f_adj]
        PASSED_PAWN_MASKS[BLACK][sq] = b_mask

init_eval_tables()

def calculate_initial_score(state):
    mg, eg, phase = 0, 0, 0
    
    for p_idx in [WP, WN, WB, WR, WQ, WK, BP, BN, BB, BR, BQ, BK]:
        bb = state.bitboards[p_idx]
        if not bb: continue
        
        count = bb.bit_count()
        phase += PHASE_WEIGHTS[p_idx] * count

        while bb:
            lsb = bb & -bb
            sq = lsb.bit_length() - 1
            mg += MG_TABLE[p_idx][sq]
            eg += EG_TABLE[p_idx][sq]
            bb &= bb - 1

    return mg, eg, phase

def calculate_initial_passed_pawns(state):
    """calculate initial passed pawn bitboards"""
    w_pawns = state.bitboards[WP]
    b_pawns = state.bitboards[BP]
    
    w_passed = 0
    b_passed = 0
    
    # white passed pawns
    temp = w_pawns
    while temp:
        lsb = temp & -temp
        sq = lsb.bit_length() - 1
        if not (PASSED_PAWN_MASKS[WHITE][sq] & b_pawns):
            w_passed |= lsb
        temp &= temp - 1
    
    # black passed pawns
    temp = b_pawns
    while temp:
        lsb = temp & -temp
        sq = lsb.bit_length() - 1
        if not (PASSED_PAWN_MASKS[BLACK][sq] & w_pawns):
            b_passed |= lsb
        temp &= temp - 1
    
    return w_passed, b_passed

def get_mop_up_score(state, winning_colour):
    """Endgame mop-up evaluation"""
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

def _evaluate_pawn_structure_fast(state, w_pawns, b_pawns):
    """Fast pawn evaluation using precomputed passed pawns"""
    pawn_score = 0

    PASSED_BONUS = [0, 10, 17, 15, 62, 168, 276, 0]
    
    # white
    temp = state.white_passed_pawns
    while temp:
        lsb = temp & -temp
        sq = lsb.bit_length() - 1
        rank = sq // 8
        pawn_score += PASSED_BONUS[rank]
        temp &= temp - 1
    
    # black
    temp = state.black_passed_pawns
    while temp:
        lsb = temp & -temp
        sq = lsb.bit_length() - 1
        rank = sq // 8
        pawn_score -= PASSED_BONUS[7 - rank]
        temp &= temp - 1
    
    return pawn_score

def evaluate_trading_bonus(state, base_eval):
    """
    winning: bonus for simplification (equal trades)
    losing: penalty for trades
    """
    if abs(base_eval) < 100: # position is roughly equal
        return 0
    
    # count total pieces (excluding pawns and kings)
    w_pieces = (state.bitboards[WN].bit_count() + state.bitboards[WB].bit_count() + 
                state.bitboards[WR].bit_count() + state.bitboards[WQ].bit_count())
    b_pieces = (state.bitboards[BN].bit_count() + state.bitboards[BB].bit_count() + 
                state.bitboards[BR].bit_count() + state.bitboards[BQ].bit_count())
    
    total_pieces = w_pieces + b_pieces
    
    # fewer pieces on board = more simplified
    # max pieces at start: 12 (4N + 4B + 4R + 2Q per side = 24 total)
    simplification_level = 24 - total_pieces
    
    trading_adjustment = 0
    
    if base_eval > WINNING_THRESHOLD: # white winning
        # bonus for simplification
        trading_adjustment = simplification_level * TRADE_BONUS_PER_PIECE
    elif base_eval < LOSING_THRESHOLD: # white losing
        # penalty for simplification
        trading_adjustment = -simplification_level * TRADE_PENALTY_PER_PIECE
    
    return trading_adjustment

def evaluate(state, pawn_hash_table=None):
    mg_phase = min(state.phase, MAX_PHASE)
    eg_phase = MAX_PHASE - mg_phase
    
    base_score = (state.mg_score * mg_phase + state.eg_score * eg_phase) // MAX_PHASE
    
    evaluation = base_score
    
    bitboards = state.bitboards
    all_pieces = bitboards[WHITE] | bitboards[BLACK]
    w_pawns = bitboards[WP]
    b_pawns = bitboards[BP]
    
    # bishop pair
    if bitboards[WB].bit_count() >= 2: evaluation += BISHOP_PAIR_BONUS
    if bitboards[BB].bit_count() >= 2: evaluation -= BISHOP_PAIR_BONUS

    # precomputed passed pawns (already tracked incrementally)
    pawn_score = _evaluate_pawn_structure_fast(state, w_pawns, b_pawns)
    evaluation += pawn_score

    # rook evaluation
    for colour, rook_piece in [(WHITE, WR), (BLACK, BR)]:
        score_adj = 0
        
        temp_rooks = bitboards[rook_piece]
        while temp_rooks:
            sq = (temp_rooks & -temp_rooks).bit_length() - 1
            f = sq % 8
            if not (w_pawns & FILE_MASKS[f]) and not (b_pawns & FILE_MASKS[f]): 
                score_adj += ROOK_OPEN_FILE
            elif not ((b_pawns if colour == WHITE else w_pawns) & FILE_MASKS[f]): 
                score_adj += ROOK_SEMI_OPEN_FILE
            temp_rooks &= temp_rooks - 1
        
        evaluation += score_adj if colour == WHITE else -score_adj

    # trading behaviour adjustment
    trading_bonus = evaluate_trading_bonus(state, evaluation)
    evaluation += trading_bonus

    # mop up in endgame
    if mg_phase < int(MAX_PHASE * 0.4):
        score_no_mopup = evaluation if state.is_white else -evaluation
        if score_no_mopup > 200: 
            evaluation += get_mop_up_score(state, state.is_white)
        elif score_no_mopup < -200: 
            evaluation += get_mop_up_score(state, not state.is_white)
    
    return evaluation if state.is_white else -evaluation
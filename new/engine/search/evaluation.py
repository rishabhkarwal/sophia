from engine.core.constants import (
    WHITE, BLACK,
    FILE_A, INFINITY, PIECE_VALUES,
    PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
    WP, WN, WB, WR, WQ, WK,
    BP, BN, BB, BR, BQ, BK,
    FLIP_BOARD, SQUARE_TO_BB, NULL,
    DOUBLED_PAWN_PENALTY, ISOLATED_PAWN_PENALTY, PASSED_PAWN_BONUS,
    KNIGHT_OUTPOST_BONUS, ROOK_ON_SEVENTH_RANK, ROOK_BEHIND_PASSED_PAWN,
    TRAPPED_PIECE_PENALTY, ROOK_BATTERY_BONUS, QUEEN_ROOK_BATTERY_BONUS,
    KING_PAWN_SHIELD_BONUS,
    KING_TO_CENTRE_BONUS, KING_TO_ENEMY_PAWNS_BONUS,
    BISHOP_PAIR_BONUS, ROOK_OPEN_FILE, ROOK_SEMI_OPEN_FILE,
    KNIGHT_MOBILITY, BISHOP_MOBILITY, ROOK_MOBILITY, QUEEN_MOBILITY,
    WINNING_THRESHOLD, LOSING_THRESHOLD, TRADE_BONUS_PER_PIECE, TRADE_PENALTY_PER_PIECE,
    DEVELOPED_PIECE_BONUS, QUEEN_EARLY_PENALTY,
    OPENING_PHASE, MIDDLEGAME_PHASE, ENDGAME_PHASE,
    A1, B1, C1, D1, F1, G1, H1,
    A8, B8, C8, D8, F8, G8, H8,
    RANK_1, RANK_8
)
from engine.moves.precomputed import (
    KNIGHT_ATTACKS, KING_ATTACKS,
    BISHOP_MASKS, BISHOP_TABLE,
    ROOK_MASKS, ROOK_TABLE
)
from engine.search.psqt import PSQTs
from engine.core.zobrist import ZOBRIST_KEYS

# piece values
MG_VALUES = {PAWN: 82, KNIGHT: 337, BISHOP: 365, ROOK: 477, QUEEN: 1025, KING: 0}
EG_VALUES = {PAWN: 94, KNIGHT: 281, BISHOP: 297, ROOK: 512, QUEEN: 936, KING: 0}

# game phase increments
PHASE_INC = {PAWN: 0, KNIGHT: 1, BISHOP: 1, ROOK: 2, QUEEN: 4, KING: 0}
MAX_PHASE = 4 * PHASE_INC[KNIGHT] + 4 * PHASE_INC[BISHOP] + 4 * PHASE_INC[ROOK] + 2 * PHASE_INC[QUEEN]

MG_TABLE = [[0] * 64 for _ in range(16)]
EG_TABLE = [[0] * 64 for _ in range(16)]
PHASE_WEIGHTS = [0] * 16

PASSED_PAWN_MASKS = [[0] * 64 for _ in range(2)]
FILE_MASKS = [0] * 8
ADJACENT_FILE_MASKS = [0] * 8

# knight outpost masks
KNIGHT_OUTPOST_MASKS_W = [0] * 64
KNIGHT_OUTPOST_MASKS_B = [0] * 64

# pre-computed mobility tables
KNIGHT_MOBILITY_TABLE = [0] * 64
BISHOP_MOBILITY_TABLE = [0] * 64
ROOK_MOBILITY_TABLE = [0] * 64
QUEEN_MOBILITY_TABLE = [0] * 64

class PawnHashTable:
    def __init__(self, size_mb=16):
        total_bytes = size_mb * 1024 * 1024
        self.size = total_bytes // 16
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
    
    for f in range(8):
        mask = FILE_A << f
        FILE_MASKS[f] = mask
        adj = 0
        if f > 0: adj |= FILE_A << (f - 1)
        if f < 7: adj |= FILE_A << (f + 1)
        ADJACENT_FILE_MASKS[f] = adj

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

        if 4 <= rank <= 6: KNIGHT_OUTPOST_MASKS_W[sq] = PASSED_PAWN_MASKS[WHITE][sq]
        if 2 <= rank <= 4: KNIGHT_OUTPOST_MASKS_B[sq] = PASSED_PAWN_MASKS[BLACK][sq]
    
    # pre-compute mobility tables
    for sq in range(64):
        KNIGHT_MOBILITY_TABLE[sq] = KNIGHT_ATTACKS[sq].bit_count() * KNIGHT_MOBILITY
        
        bishop_moves = BISHOP_TABLE[sq][0]  # empty board
        BISHOP_MOBILITY_TABLE[sq] = bishop_moves.bit_count() * BISHOP_MOBILITY
        
        rook_moves = ROOK_TABLE[sq][0]  # empty board
        ROOK_MOBILITY_TABLE[sq] = rook_moves.bit_count() * ROOK_MOBILITY
        
        queen_moves = (bishop_moves | rook_moves)
        QUEEN_MOBILITY_TABLE[sq] = queen_moves.bit_count() * QUEEN_MOBILITY

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
    w_pawns = state.bitboards[WP]
    b_pawns = state.bitboards[BP]
    
    w_passed = 0
    b_passed = 0
    
    temp = w_pawns
    while temp:
        lsb = temp & -temp
        sq = lsb.bit_length() - 1
        if not (PASSED_PAWN_MASKS[WHITE][sq] & b_pawns):
            w_passed |= lsb
        temp &= temp - 1
    
    temp = b_pawns
    while temp:
        lsb = temp & -temp
        sq = lsb.bit_length() - 1
        if not (PASSED_PAWN_MASKS[BLACK][sq] & w_pawns):
            b_passed |= lsb
        temp &= temp - 1
    
    return w_passed, b_passed

def get_pawn_hash(state):
    """Compute hash from pawn positions only for caching pawn structure evaluation"""
    h = 0
    w_pawns = state.bitboards[WP]
    b_pawns = state.bitboards[BP]
    
    temp = w_pawns
    while temp:
        sq = (temp & -temp).bit_length() - 1
        h ^= ZOBRIST_KEYS.pieces[WP][sq]
        temp &= temp - 1
    
    temp = b_pawns
    while temp:
        sq = (temp & -temp).bit_length() - 1
        h ^= ZOBRIST_KEYS.pieces[BP][sq]
        temp &= temp - 1
    
    return h

def _evaluate_pawn_structure_cached(state, w_pawns, b_pawns, pawn_hash_table):
    """Evaluate pawn structure with hash table caching"""
    
    pawn_hash = get_pawn_hash(state)
    
    if pawn_hash_table:
        cached = pawn_hash_table.probe(pawn_hash)
        if cached is not None:
            return cached
    
    pawn_score = 0

    temp = state.white_passed_pawns
    while temp:
        lsb = temp & -temp
        sq = lsb.bit_length() - 1
        rank = sq // 8
        pawn_score += PASSED_PAWN_BONUS[rank]
        temp &= temp - 1
    
    temp = state.black_passed_pawns
    while temp:
        lsb = temp & -temp
        sq = lsb.bit_length() - 1
        rank = sq // 8
        pawn_score -= PASSED_PAWN_BONUS[7 - rank]
        temp &= temp - 1
    
    if state.phase < int(MAX_PHASE * 0.8):
        for file in range(8):
            w_count = (w_pawns & FILE_MASKS[file]).bit_count()
            b_count = (b_pawns & FILE_MASKS[file]).bit_count()
            if w_count > 1: pawn_score -= DOUBLED_PAWN_PENALTY * (w_count - 1)
            if b_count > 1: pawn_score += DOUBLED_PAWN_PENALTY * (b_count - 1)
    
    for file in range(8):
        w_on_file = w_pawns & FILE_MASKS[file]
        b_on_file = b_pawns & FILE_MASKS[file]
        
        if w_on_file:
            if not (w_pawns & ADJACENT_FILE_MASKS[file]):
                pawn_score -= ISOLATED_PAWN_PENALTY * w_on_file.bit_count()
        
        if b_on_file:
            if not (b_pawns & ADJACENT_FILE_MASKS[file]):
                pawn_score += ISOLATED_PAWN_PENALTY * b_on_file.bit_count()
    
    if pawn_hash_table:
        pawn_hash_table.store(pawn_hash, pawn_score)
    
    return pawn_score

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

def evaluate_trading_bonus(state, base_eval):
    if LOSING_THRESHOLD <= base_eval <= WINNING_THRESHOLD:
        return 0
    
    w_pieces = (state.bitboards[WN].bit_count() + state.bitboards[WB].bit_count() + 
                state.bitboards[WR].bit_count() + state.bitboards[WQ].bit_count())
    b_pieces = (state.bitboards[BN].bit_count() + state.bitboards[BB].bit_count() + 
                state.bitboards[BR].bit_count() + state.bitboards[BQ].bit_count())
    
    total_pieces = w_pieces + b_pieces
    simplification_level = 24 - total_pieces
    
    if base_eval > WINNING_THRESHOLD:
        return simplification_level * TRADE_BONUS_PER_PIECE
    elif base_eval < LOSING_THRESHOLD:
        return -simplification_level * TRADE_PENALTY_PER_PIECE
    
    return 0

def evaluate_king_safety_simple(king_sq, own_pawns):
    """Simplified king safety"""
    king_rank = king_sq // 8
    king_file = king_sq % 8
    safety_score = 0
    
    if king_rank <= 1:
        direction = 1
    elif king_rank >= 6:
        direction = -1
    else:
        return 0

    for rank_offset in range(1, 3):
        check_rank = king_rank + (rank_offset * direction)
        if not (0 <= check_rank <= 7): break
        
        for file_offset in range(-1, 2):
            check_file = king_file + file_offset
            if 0 <= check_file <= 7:
                check_sq = check_rank * 8 + check_file
                if SQUARE_TO_BB[check_sq] & own_pawns:
                    safety_score += KING_PAWN_SHIELD_BONUS
    
    return safety_score

def evaluate_king_endgame_activity(king_sq, enemy_pawns):
    king_rank, king_file = king_sq // 8, king_sq % 8
    centre_dist = max(3 - king_rank, king_rank - 4) + max(3 - king_file, king_file - 4)
    centralisation_bonus = (7 - centre_dist) * KING_TO_CENTRE_BONUS
    
    if not enemy_pawns:
        return centralisation_bonus
    
    min_dist = 14
    temp = enemy_pawns
    while temp:
        pawn_sq = (temp & -temp).bit_length() - 1
        pawn_rank, pawn_file = pawn_sq // 8, pawn_sq % 8
        dist = abs(king_rank - pawn_rank) + abs(king_file - pawn_file)
        if dist < min_dist:
            min_dist = dist
        temp &= temp - 1
    
    proximity_bonus = (14 - min_dist) * KING_TO_ENEMY_PAWNS_BONUS
    
    return centralisation_bonus + proximity_bonus

def evaluate_piece_development(state):
    """Evaluate piece development in opening/early middlegame"""
    if state.phase <= MIDDLEGAME_PHASE:
        return 0  # not in opening anymore
    
    dev_score = 0
    
    # white knights
    if state.bitboards[WN] & SQUARE_TO_BB[B1]:
        dev_score -= DEVELOPED_PIECE_BONUS
    if state.bitboards[WN] & SQUARE_TO_BB[G1]:
        dev_score -= DEVELOPED_PIECE_BONUS
    
    # black knights
    if state.bitboards[BN] & SQUARE_TO_BB[B8]:
        dev_score += DEVELOPED_PIECE_BONUS
    if state.bitboards[BN] & SQUARE_TO_BB[G8]:
        dev_score += DEVELOPED_PIECE_BONUS
    
    # white bishops
    if state.bitboards[WB] & (SQUARE_TO_BB[C1] | SQUARE_TO_BB[F1]):
        dev_score -= DEVELOPED_PIECE_BONUS
    
    # black bishops
    if state.bitboards[BB] & (SQUARE_TO_BB[C8] | SQUARE_TO_BB[F8]):
        dev_score += DEVELOPED_PIECE_BONUS
    
    # white rooks
    if state.bitboards[WR] & RANK_1:
        undeveloped_rooks = (state.bitboards[WR] & RANK_1).bit_count()
        if undeveloped_rooks == 2:
            dev_score -= DEVELOPED_PIECE_BONUS
    
    # black rooks
    if state.bitboards[BR] & RANK_8:
        undeveloped_rooks = (state.bitboards[BR] & RANK_8).bit_count()
        if undeveloped_rooks == 2:
            dev_score += DEVELOPED_PIECE_BONUS
    
    # queen out too early penalty (only in opening)
    if state.phase > OPENING_PHASE:
        if state.fullmove_number < 8:
            if not (state.bitboards[WQ] & SQUARE_TO_BB[D1]):
                dev_score -= QUEEN_EARLY_PENALTY
            if not (state.bitboards[BQ] & SQUARE_TO_BB[D8]):
                dev_score += QUEEN_EARLY_PENALTY
    
    return dev_score
    
def evaluate(state, pawn_hash_table=None):
    mg_phase = min(state.phase, MAX_PHASE)
    eg_phase = MAX_PHASE - mg_phase
    
    base_score = (state.mg_score * mg_phase + state.eg_score * eg_phase) // MAX_PHASE
    evaluation = base_score
    
    bitboards = state.bitboards
    all_pieces = bitboards[WHITE] | bitboards[BLACK]
    w_pawns = bitboards[WP]
    b_pawns = bitboards[BP]
    
    if bitboards[WB].bit_count() >= 2: evaluation += BISHOP_PAIR_BONUS
    if bitboards[BB].bit_count() >= 2: evaluation -= BISHOP_PAIR_BONUS

    pawn_score = _evaluate_pawn_structure_cached(state, w_pawns, b_pawns, pawn_hash_table)
    evaluation += pawn_score

    # piece development (opening/early middlegame)
    if state.phase > MIDDLEGAME_PHASE:
        evaluation += evaluate_piece_development(state)

    for colour, rook_piece in [(WHITE, WR), (BLACK, BR)]:
        score_adj = 0
        temp_rooks = bitboards[rook_piece]
        
        while temp_rooks:
            sq = (temp_rooks & -temp_rooks).bit_length() - 1
            f = sq % 8
            rank = sq // 8
            
            if not (w_pawns & FILE_MASKS[f]) and not (b_pawns & FILE_MASKS[f]): 
                score_adj += ROOK_OPEN_FILE
            elif not ((b_pawns if colour == WHITE else w_pawns) & FILE_MASKS[f]): 
                score_adj += ROOK_SEMI_OPEN_FILE
            
            if (colour == WHITE and rank == 6) or (colour == BLACK and rank == 1):
                score_adj += ROOK_ON_SEVENTH_RANK
            
            passed_pawns = state.white_passed_pawns if colour == WHITE else state.black_passed_pawns
            if passed_pawns & FILE_MASKS[f]:
                passed_sq = (passed_pawns & FILE_MASKS[f] & -(passed_pawns & FILE_MASKS[f])).bit_length() - 1
                passed_rank = passed_sq // 8
                if (colour == WHITE and rank < passed_rank) or (colour == BLACK and rank > passed_rank):
                    score_adj += ROOK_BEHIND_PASSED_PAWN
            
            temp_rooks &= temp_rooks - 1
        
        evaluation += score_adj if colour == WHITE else -score_adj

    for colour, knight_piece in [(WHITE, WN), (BLACK, BN)]:
        temp_knights = bitboards[knight_piece]
        while temp_knights:
            sq = (temp_knights & -temp_knights).bit_length() - 1
            
            outpost_mask = KNIGHT_OUTPOST_MASKS_W[sq] if colour == WHITE else KNIGHT_OUTPOST_MASKS_B[sq]
            enemy_pawns = b_pawns if colour == WHITE else w_pawns
            
            if outpost_mask and not (enemy_pawns & outpost_mask):
                if colour == WHITE:
                    pawn_def = (sq >= 8 and ((SQUARE_TO_BB[sq - 7] | SQUARE_TO_BB[sq - 9]) & w_pawns))
                else:
                    pawn_def = (sq < 56 and ((SQUARE_TO_BB[sq + 7] | SQUARE_TO_BB[sq + 9]) & b_pawns))
                
                if pawn_def:
                    evaluation += KNIGHT_OUTPOST_BONUS if colour == WHITE else -KNIGHT_OUTPOST_BONUS
            
            temp_knights &= temp_knights - 1

    w_king_sq = (bitboards[WK] & -bitboards[WK]).bit_length() - 1 if bitboards[WK] else NULL
    b_king_sq = (bitboards[BK] & -bitboards[BK]).bit_length() - 1 if bitboards[BK] else NULL
    
    if mg_phase > int(MAX_PHASE * 0.6):
        if w_king_sq >= 0:
            evaluation += evaluate_king_safety_simple(w_king_sq, w_pawns)
        if b_king_sq >= 0:
            evaluation -= evaluate_king_safety_simple(b_king_sq, b_pawns)

    # mobility using pre-computed tables (faster)
    if mg_phase > int(MAX_PHASE * 0.5):
        for colour, pieces in [(WHITE, [(WN, KNIGHT_MOBILITY_TABLE), (WB, BISHOP_MOBILITY_TABLE), (WR, ROOK_MOBILITY_TABLE), (WQ, QUEEN_MOBILITY_TABLE)]),
                               (BLACK, [(BN, KNIGHT_MOBILITY_TABLE), (BB, BISHOP_MOBILITY_TABLE), (BR, ROOK_MOBILITY_TABLE), (BQ, QUEEN_MOBILITY_TABLE)])]:
            mobility_score = 0
            
            for piece_key, mobility_table in pieces:
                piece_bb = bitboards[piece_key]
                
                while piece_bb:
                    sq = (piece_bb & -piece_bb).bit_length() - 1
                    
                    # use pre-computed mobility
                    mobility_score += mobility_table[sq]
                    
                    piece_bb &= piece_bb - 1
            
            evaluation += mobility_score if colour == WHITE else -mobility_score

    for colour in [WHITE, BLACK]:
        battery_score = 0
        rooks = bitboards[WR if colour == WHITE else BR]
        queen = bitboards[WQ if colour == WHITE else BQ]
        
        for file in range(8):
            if (rooks & FILE_MASKS[file]).bit_count() >= 2:
                battery_score += ROOK_BATTERY_BONUS
        
        if queen:
            queen_sq = (queen & -queen).bit_length() - 1
            queen_file = queen_sq % 8
            
            if rooks & FILE_MASKS[queen_file]:
                battery_score += QUEEN_ROOK_BATTERY_BONUS
            
            bishop_pattern = BISHOP_TABLE[queen_sq][all_pieces & BISHOP_MASKS[queen_sq]]
            if rooks & bishop_pattern:
                battery_score += QUEEN_ROOK_BATTERY_BONUS // 2
        
        evaluation += battery_score if colour == WHITE else -battery_score

    trading_bonus = evaluate_trading_bonus(state, evaluation)
    evaluation += trading_bonus

    if mg_phase < int(MAX_PHASE * 0.4):
        score_no_mopup = evaluation if state.is_white else -evaluation
        
        if w_king_sq >= 0:
            w_king_activity = evaluate_king_endgame_activity(w_king_sq, b_pawns)
            evaluation += w_king_activity
        if b_king_sq >= 0:
            b_king_activity = evaluate_king_endgame_activity(b_king_sq, w_pawns)
            evaluation -= b_king_activity
        
        if score_no_mopup > 200: 
            evaluation += get_mop_up_score(state, state.is_white)
        elif score_no_mopup < -200: 
            evaluation += get_mop_up_score(state, not state.is_white)
    
    return evaluation if state.is_white else -evaluation
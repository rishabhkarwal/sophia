from engine.core.constants import (
    WHITE, BLACK,
    FILE_A, INFINITY, PIECE_VALUES,
    PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
    WP, WN, WB, WR, WQ, WK,
    BP, BN, BB, BR, BQ, BK,
    FLIP_BOARD, SQUARE_TO_BB, NULL as _NULL,
    DOUBLED_PAWN_PENALTY, ISOLATED_PAWN_PENALTY, PASSED_PAWN_BONUS,
    KNIGHT_OUTPOST_BONUS, ROOK_ON_SEVENTH_RANK, ROOK_BEHIND_PASSED_PAWN,
    TRAPPED_PIECE_PENALTY, ROOK_BATTERY_BONUS, QUEEN_ROOK_BATTERY_BONUS,
    KING_PAWN_SHIELD_BONUS,
    KING_TO_CENTRE_BONUS, KING_TO_ENEMY_PAWNS_BONUS,
    BISHOP_PAIR_BONUS, ROOK_OPEN_FILE, ROOK_SEMI_OPEN_FILE,
    KNIGHT_MOBILITY, BISHOP_MOBILITY, ROOK_MOBILITY, QUEEN_MOBILITY,
    WINNING_THRESHOLD, LOSING_THRESHOLD, TRADE_BONUS_PER_PIECE, TRADE_PENALTY_PER_PIECE
)
from engine.moves.precomputed cimport KNIGHT_ATTACKS, KING_ATTACKS, BISHOP_MASKS, ROOK_MASKS
from engine.moves.precomputed import BISHOP_TABLE, ROOK_TABLE
from engine.search.psqt import PSQTs
from engine.core.zobrist import ZOBRIST_KEYS
import engine.core.constants as _const
from engine.uci.utils import send_info_string
from engine.board.state cimport State
from engine.core.bits cimport lsb, popcount, pop_lsb

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
cdef unsigned long long FILE_MASKS[8]
cdef unsigned long long ADJACENT_FILE_MASKS[8]

# knight outpost masks
KNIGHT_OUTPOST_MASKS_W = [0] * 64
KNIGHT_OUTPOST_MASKS_B = [0] * 64

class PawnHashTable:
    def __init__(self, size_mb=16):
        total_bytes = size_mb * 1024 * 1024
        self.size = total_bytes // 16
        self.table = [None] * self.size
        self.dbg_hits = 0
        self.dbg_misses = 0

    def probe(self, pawn_hash):
        idx = pawn_hash % self.size
        entry = self.table[idx]
        if entry and entry[0] == pawn_hash:
            if _const.DEBUG_EVAL: self.dbg_hits += 1
            return entry[1]
        if _const.DEBUG_EVAL: self.dbg_misses += 1
        return None

    def store(self, pawn_hash, score):
        idx = pawn_hash % self.size
        self.table[idx] = (pawn_hash, score)

    def hit_rate(self):
        total = self.dbg_hits + self.dbg_misses
        return f"{self.dbg_hits}/{total} ({100*self.dbg_hits//total if total else 0}%)"

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

        b_piece = BLACK | p_type
        PHASE_WEIGHTS[b_piece] = phase_inc

        for sq in range(64):
            flipped_sq = sq ^ FLIP_BOARD
            MG_TABLE[w_piece][sq] = mg_val + mg_psqt[flipped_sq]
            EG_TABLE[w_piece][sq] = eg_val + eg_psqt[flipped_sq]

            MG_TABLE[b_piece][sq] = -(mg_val + mg_psqt[sq])
            EG_TABLE[b_piece][sq] = -(eg_val + eg_psqt[sq])

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

        # knight outpost masks
        if 4 <= rank <= 6: KNIGHT_OUTPOST_MASKS_W[sq] = PASSED_PAWN_MASKS[WHITE][sq]
        if 2 <= rank <= 4: KNIGHT_OUTPOST_MASKS_B[sq] = PASSED_PAWN_MASKS[BLACK][sq]

init_eval_tables()

def calculate_initial_score(state):
    cdef int mg
    cdef int eg
    cdef int phase
    cdef int count
    cdef int sq
    cdef int p_idx
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

cdef unsigned long long get_pawn_hash(State state) noexcept:
    cdef unsigned long long h = 0, temp
    cdef int sq
    temp = state.bitboards[WP]
    while temp:
        sq   = lsb(temp)
        temp &= temp - 1
        h   ^= ZOBRIST_KEYS.pieces[WP][sq]
    temp = state.bitboards[BP]
    while temp:
        sq   = lsb(temp)
        temp &= temp - 1
        h   ^= ZOBRIST_KEYS.pieces[BP][sq]
    return h

cdef int _evaluate_pawn_structure_cached(State state, unsigned long long w_pawns,
                                          unsigned long long b_pawns,
                                          object pawn_hash_table) noexcept:
    cdef int pawn_score, sq, rank, f, w_count, b_count
    cdef unsigned long long pawn_hash, temp, w_on_file, b_on_file

    pawn_hash = get_pawn_hash(state)

    if pawn_hash_table:
        cached = pawn_hash_table.probe(pawn_hash)
        if cached is not None:
            return cached

    pawn_score = 0

    temp = state.white_passed_pawns
    while temp:
        sq    = lsb(temp)
        temp &= temp - 1
        rank  = sq >> 3
        pawn_score += PASSED_PAWN_BONUS[rank]

    temp = state.black_passed_pawns
    while temp:
        sq    = lsb(temp)
        temp &= temp - 1
        rank  = sq >> 3
        pawn_score -= PASSED_PAWN_BONUS[7 - rank]

    if state.phase < int(MAX_PHASE * 0.8):
        for f in range(8):
            w_count = popcount(w_pawns & FILE_MASKS[f])
            b_count = popcount(b_pawns & FILE_MASKS[f])
            if w_count > 1: pawn_score -= DOUBLED_PAWN_PENALTY * (w_count - 1)
            if b_count > 1: pawn_score += DOUBLED_PAWN_PENALTY * (b_count - 1)

    for f in range(8):
        w_on_file = w_pawns & FILE_MASKS[f]
        b_on_file = b_pawns & FILE_MASKS[f]

        if w_on_file:
            if not (w_pawns & ADJACENT_FILE_MASKS[f]):
                pawn_score -= ISOLATED_PAWN_PENALTY * popcount(w_on_file)

        if b_on_file:
            if not (b_pawns & ADJACENT_FILE_MASKS[f]):
                pawn_score += ISOLATED_PAWN_PENALTY * popcount(b_on_file)

    if pawn_hash_table:
        pawn_hash_table.store(pawn_hash, pawn_score)

    return pawn_score

cdef int get_mop_up_score(State state, bint winning_is_white) noexcept:
    cdef int winning_sq, losing_sq, losing_rank, losing_file
    cdef int centre_dist, mop_up, winning_rank, winning_file, dist_between_kings
    cdef unsigned long long winning_king_bb, losing_king_bb
    winning_king_bb = state.bitboards[WK] if winning_is_white else state.bitboards[BK]
    losing_king_bb  = state.bitboards[BK] if winning_is_white else state.bitboards[WK]

    if not winning_king_bb or not losing_king_bb: return 0

    winning_sq  = lsb(winning_king_bb)
    losing_sq   = lsb(losing_king_bb)

    losing_rank = losing_sq >> 3
    losing_file = losing_sq & 7

    centre_dist = max(3 - losing_rank, losing_rank - 4) + max(3 - losing_file, losing_file - 4)
    mop_up = 4 * centre_dist

    winning_rank = winning_sq >> 3
    winning_file = winning_sq & 7
    dist_between_kings = abs(winning_rank - losing_rank) + abs(winning_file - losing_file)
    mop_up += 2 * (14 - dist_between_kings)

    return mop_up if winning_is_white else -mop_up


cdef int evaluate_trading_bonus(State state, int base_eval) noexcept:
    cdef int w_pieces, b_pieces, total_pieces, simplification_level
    if LOSING_THRESHOLD <= base_eval <= WINNING_THRESHOLD:
        return 0

    w_pieces = (popcount(state.bitboards[WN]) + popcount(state.bitboards[WB]) +
                popcount(state.bitboards[WR]) + popcount(state.bitboards[WQ]))
    b_pieces = (popcount(state.bitboards[BN]) + popcount(state.bitboards[BB]) +
                popcount(state.bitboards[BR]) + popcount(state.bitboards[BQ]))

    total_pieces = w_pieces + b_pieces
    simplification_level = 24 - total_pieces

    if base_eval > WINNING_THRESHOLD:
        return simplification_level * TRADE_BONUS_PER_PIECE
    elif base_eval < LOSING_THRESHOLD:
        return -simplification_level * TRADE_PENALTY_PER_PIECE

    return 0


cdef int evaluate_king_safety_simple(int king_sq, unsigned long long own_pawns) noexcept:
    cdef int king_rank, king_file, safety_score, direction
    cdef int rank_offset, check_rank, file_offset, check_file, check_sq
    king_rank = king_sq >> 3
    king_file = king_sq & 7
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
                if ((<unsigned long long>1) << check_sq) & own_pawns:
                    safety_score += KING_PAWN_SHIELD_BONUS

    return safety_score


cdef int evaluate_king_endgame_activity(int king_sq, unsigned long long enemy_pawns) noexcept:
    cdef int king_rank, king_file, centre_dist, centralisation_bonus
    cdef int min_dist, pawn_sq, pawn_rank, pawn_file, dist, proximity_bonus
    cdef unsigned long long temp
    king_rank = king_sq >> 3
    king_file = king_sq & 7
    centre_dist = max(3 - king_rank, king_rank - 4) + max(3 - king_file, king_file - 4)
    centralisation_bonus = (7 - centre_dist) * KING_TO_CENTRE_BONUS

    if not enemy_pawns:
        return centralisation_bonus

    min_dist = 14
    temp = enemy_pawns
    while temp:
        pawn_sq   = lsb(temp)
        temp     &= temp - 1
        pawn_rank = pawn_sq >> 3
        pawn_file = pawn_sq & 7
        dist = abs(king_rank - pawn_rank) + abs(king_file - pawn_file)
        if dist < min_dist:
            min_dist = dist

    proximity_bonus = (14 - min_dist) * KING_TO_ENEMY_PAWNS_BONUS

    return centralisation_bonus + proximity_bonus

cpdef int evaluate(State state, object pawn_hash_table=None):
    cdef int mg_phase
    cdef int eg_phase
    cdef int base_score
    cdef int evaluation
    cdef int dbg_bishop_pair
    cdef int pawn_score
    cdef int dbg_rook
    cdef int score_adj
    cdef int sq
    cdef int f
    cdef int rank
    cdef int passed_sq
    cdef int passed_rank
    cdef int adj
    cdef int dbg_knight_outpost
    cdef int bonus
    cdef int w_king_sq
    cdef int b_king_sq
    cdef int dbg_king_safety
    cdef int ks
    cdef int dbg_mobility
    cdef int mobility_score
    cdef int piece_type
    cdef int legal_squares
    cdef int dbg_battery
    cdef int battery_score
    cdef int file
    cdef int queen_sq
    cdef int queen_file
    cdef int trading_bonus
    cdef int dbg_king_activity
    cdef int dbg_mop_up
    cdef int score_no_mopup
    cdef int w_king_activity
    cdef int b_king_activity
    cdef int mop
    cdef unsigned long long all_pieces, w_pawns, b_pawns
    cdef unsigned long long temp_rooks, temp_knights, piece_bb
    cdef unsigned long long passed_pawns, outpost_mask, enemy_pawns_bb
    cdef unsigned long long wk_bb, bk_bb, rooks_bb, queen_bb
    cdef unsigned long long file_mask, passed_file_mask

    mg_phase = min(state.phase, MAX_PHASE)
    eg_phase = MAX_PHASE - mg_phase

    base_score = (state.mg_score * mg_phase + state.eg_score * eg_phase) // MAX_PHASE
    evaluation = base_score

    all_pieces = state.bitboards[WHITE] | state.bitboards[BLACK]
    w_pawns = state.bitboards[WP]
    b_pawns = state.bitboards[BP]

    # bishop pair
    dbg_bishop_pair = 0
    if popcount(state.bitboards[WB]) >= 2:
        evaluation += BISHOP_PAIR_BONUS
        dbg_bishop_pair += BISHOP_PAIR_BONUS
    if popcount(state.bitboards[BB]) >= 2:
        evaluation -= BISHOP_PAIR_BONUS
        dbg_bishop_pair -= BISHOP_PAIR_BONUS

    # pawn structure (WITH HASH TABLE CACHING)
    pawn_score = _evaluate_pawn_structure_cached(state, w_pawns, b_pawns, pawn_hash_table)
    evaluation += pawn_score

    # rook evaluation (open files, 7th rank, behind passed pawns)
    dbg_rook = 0
    # white rooks
    score_adj = 0
    temp_rooks = state.bitboards[WR]
    passed_pawns = state.white_passed_pawns
    while temp_rooks:
        sq = lsb(temp_rooks)
        f = sq & 7
        rank = sq >> 3
        file_mask = FILE_MASKS[f]

        if not (w_pawns & file_mask) and not (b_pawns & file_mask):
            score_adj += ROOK_OPEN_FILE
        elif not (b_pawns & file_mask):
            score_adj += ROOK_SEMI_OPEN_FILE

        if rank == 6:
            score_adj += ROOK_ON_SEVENTH_RANK

        passed_file_mask = passed_pawns & file_mask
        if passed_file_mask:
            passed_sq = lsb(passed_file_mask)
            passed_rank = passed_sq >> 3
            if rank < passed_rank:
                score_adj += ROOK_BEHIND_PASSED_PAWN

        temp_rooks = pop_lsb(temp_rooks)

    evaluation += score_adj
    dbg_rook += score_adj

    # black rooks
    score_adj = 0
    temp_rooks = state.bitboards[BR]
    passed_pawns = state.black_passed_pawns
    while temp_rooks:
        sq = lsb(temp_rooks)
        f = sq & 7
        rank = sq >> 3
        file_mask = FILE_MASKS[f]

        if not (w_pawns & file_mask) and not (b_pawns & file_mask):
            score_adj += ROOK_OPEN_FILE
        elif not (w_pawns & file_mask):
            score_adj += ROOK_SEMI_OPEN_FILE

        if rank == 1:
            score_adj += ROOK_ON_SEVENTH_RANK

        passed_file_mask = passed_pawns & file_mask
        if passed_file_mask:
            passed_sq = lsb(passed_file_mask)
            passed_rank = passed_sq >> 3
            if rank > passed_rank:
                score_adj += ROOK_BEHIND_PASSED_PAWN

        temp_rooks = pop_lsb(temp_rooks)

    evaluation -= score_adj
    dbg_rook -= score_adj

    # knight outposts
    dbg_knight_outpost = 0
    temp_knights = state.bitboards[WN]
    while temp_knights:
        sq = lsb(temp_knights)
        outpost_mask = KNIGHT_OUTPOST_MASKS_W[sq]
        if outpost_mask and not (b_pawns & outpost_mask):
            if sq >= 8 and ((SQUARE_TO_BB[sq - 7] | SQUARE_TO_BB[sq - 9]) & w_pawns):
                evaluation += KNIGHT_OUTPOST_BONUS
                dbg_knight_outpost += KNIGHT_OUTPOST_BONUS
        temp_knights = pop_lsb(temp_knights)

    temp_knights = state.bitboards[BN]
    while temp_knights:
        sq = lsb(temp_knights)
        outpost_mask = KNIGHT_OUTPOST_MASKS_B[sq]
        if outpost_mask and not (w_pawns & outpost_mask):
            if sq < 56 and ((SQUARE_TO_BB[sq + 7] | SQUARE_TO_BB[sq + 9]) & b_pawns):
                evaluation -= KNIGHT_OUTPOST_BONUS
                dbg_knight_outpost -= KNIGHT_OUTPOST_BONUS
        temp_knights = pop_lsb(temp_knights)

    # simplified king safety (middlegame only, no expensive loops)
    wk_bb = state.bitboards[WK]
    bk_bb = state.bitboards[BK]
    w_king_sq = lsb(wk_bb) if wk_bb else _NULL
    b_king_sq = lsb(bk_bb) if bk_bb else _NULL

    dbg_king_safety = 0
    if mg_phase > int(MAX_PHASE * 0.6):
        if w_king_sq >= 0:
            ks = evaluate_king_safety_simple(w_king_sq, w_pawns)
            evaluation += ks
            dbg_king_safety += ks
        if b_king_sq >= 0:
            ks = evaluate_king_safety_simple(b_king_sq, b_pawns)
            evaluation -= ks
            dbg_king_safety -= ks

    # mobility + trapped pieces (ONLY in middlegame when phase > 50%)
    dbg_mobility = 0
    if mg_phase > int(MAX_PHASE * 0.5):
        # white pieces
        mobility_score = 0
        piece_bb = state.bitboards[WN]
        while piece_bb:
            sq = lsb(piece_bb)
            legal_squares = popcount(KNIGHT_ATTACKS[sq] & ~state.bitboards[WHITE])
            if legal_squares == 0:
                mobility_score -= TRAPPED_PIECE_PENALTY
            else:
                mobility_score += legal_squares * KNIGHT_MOBILITY
            piece_bb = pop_lsb(piece_bb)

        piece_bb = state.bitboards[WB]
        while piece_bb:
            sq = lsb(piece_bb)
            legal_squares = popcount(BISHOP_TABLE[sq][all_pieces & BISHOP_MASKS[sq]] & ~state.bitboards[WHITE])
            if legal_squares == 0:
                mobility_score -= TRAPPED_PIECE_PENALTY
            else:
                mobility_score += legal_squares * BISHOP_MOBILITY
            piece_bb = pop_lsb(piece_bb)

        piece_bb = state.bitboards[WR]
        while piece_bb:
            sq = lsb(piece_bb)
            legal_squares = popcount(ROOK_TABLE[sq][all_pieces & ROOK_MASKS[sq]] & ~state.bitboards[WHITE])
            if legal_squares == 0:
                mobility_score -= TRAPPED_PIECE_PENALTY
            else:
                mobility_score += legal_squares * ROOK_MOBILITY
            piece_bb = pop_lsb(piece_bb)

        piece_bb = state.bitboards[WQ]
        while piece_bb:
            sq = lsb(piece_bb)
            legal_squares = popcount((BISHOP_TABLE[sq][all_pieces & BISHOP_MASKS[sq]] |
                                      ROOK_TABLE[sq][all_pieces & ROOK_MASKS[sq]]) & ~state.bitboards[WHITE])
            if legal_squares == 0:
                mobility_score -= TRAPPED_PIECE_PENALTY
            else:
                mobility_score += legal_squares * QUEEN_MOBILITY
            piece_bb = pop_lsb(piece_bb)

        evaluation += mobility_score
        dbg_mobility += mobility_score

        # black pieces
        mobility_score = 0
        piece_bb = state.bitboards[BN]
        while piece_bb:
            sq = lsb(piece_bb)
            legal_squares = popcount(KNIGHT_ATTACKS[sq] & ~state.bitboards[BLACK])
            if legal_squares == 0:
                mobility_score -= TRAPPED_PIECE_PENALTY
            else:
                mobility_score += legal_squares * KNIGHT_MOBILITY
            piece_bb = pop_lsb(piece_bb)

        piece_bb = state.bitboards[BB]
        while piece_bb:
            sq = lsb(piece_bb)
            legal_squares = popcount(BISHOP_TABLE[sq][all_pieces & BISHOP_MASKS[sq]] & ~state.bitboards[BLACK])
            if legal_squares == 0:
                mobility_score -= TRAPPED_PIECE_PENALTY
            else:
                mobility_score += legal_squares * BISHOP_MOBILITY
            piece_bb = pop_lsb(piece_bb)

        piece_bb = state.bitboards[BR]
        while piece_bb:
            sq = lsb(piece_bb)
            legal_squares = popcount(ROOK_TABLE[sq][all_pieces & ROOK_MASKS[sq]] & ~state.bitboards[BLACK])
            if legal_squares == 0:
                mobility_score -= TRAPPED_PIECE_PENALTY
            else:
                mobility_score += legal_squares * ROOK_MOBILITY
            piece_bb = pop_lsb(piece_bb)

        piece_bb = state.bitboards[BQ]
        while piece_bb:
            sq = lsb(piece_bb)
            legal_squares = popcount((BISHOP_TABLE[sq][all_pieces & BISHOP_MASKS[sq]] |
                                      ROOK_TABLE[sq][all_pieces & ROOK_MASKS[sq]]) & ~state.bitboards[BLACK])
            if legal_squares == 0:
                mobility_score -= TRAPPED_PIECE_PENALTY
            else:
                mobility_score += legal_squares * QUEEN_MOBILITY
            piece_bb = pop_lsb(piece_bb)

        evaluation -= mobility_score
        dbg_mobility -= mobility_score

    # piece batteries
    dbg_battery = 0
    # white batteries
    battery_score = 0
    rooks_bb = state.bitboards[WR]
    queen_bb = state.bitboards[WQ]
    for file in range(8):
        if popcount(rooks_bb & FILE_MASKS[file]) >= 2:
            battery_score += ROOK_BATTERY_BONUS
    if queen_bb:
        queen_sq = lsb(queen_bb)
        queen_file = queen_sq & 7
        if rooks_bb & FILE_MASKS[queen_file]:
            battery_score += QUEEN_ROOK_BATTERY_BONUS
        if rooks_bb & BISHOP_TABLE[queen_sq][all_pieces & BISHOP_MASKS[queen_sq]]:
            battery_score += QUEEN_ROOK_BATTERY_BONUS // 2
    evaluation += battery_score
    dbg_battery += battery_score

    # black batteries
    battery_score = 0
    rooks_bb = state.bitboards[BR]
    queen_bb = state.bitboards[BQ]
    for file in range(8):
        if popcount(rooks_bb & FILE_MASKS[file]) >= 2:
            battery_score += ROOK_BATTERY_BONUS
    if queen_bb:
        queen_sq = lsb(queen_bb)
        queen_file = queen_sq & 7
        if rooks_bb & FILE_MASKS[queen_file]:
            battery_score += QUEEN_ROOK_BATTERY_BONUS
        if rooks_bb & BISHOP_TABLE[queen_sq][all_pieces & BISHOP_MASKS[queen_sq]]:
            battery_score += QUEEN_ROOK_BATTERY_BONUS // 2
    evaluation -= battery_score
    dbg_battery -= battery_score

    # trading behaviour
    trading_bonus = evaluate_trading_bonus(state, evaluation)
    evaluation += trading_bonus

    # endgame: king activity + mop up (only when phase < 40%)
    dbg_king_activity = 0
    dbg_mop_up = 0
    if mg_phase < int(MAX_PHASE * 0.4):
        score_no_mopup = evaluation if state.is_white else -evaluation

        if w_king_sq >= 0:
            w_king_activity = evaluate_king_endgame_activity(w_king_sq, b_pawns)
            evaluation += w_king_activity
            dbg_king_activity += w_king_activity
        if b_king_sq >= 0:
            b_king_activity = evaluate_king_endgame_activity(b_king_sq, w_pawns)
            evaluation -= b_king_activity
            dbg_king_activity -= b_king_activity

        if score_no_mopup > 200:
            mop = get_mop_up_score(state, state.is_white)
            evaluation += mop
            dbg_mop_up = mop
        elif score_no_mopup < -200:
            mop = get_mop_up_score(state, not state.is_white)
            evaluation += mop
            dbg_mop_up = mop

    if _const.DEBUG_EVAL:
        side = "w" if state.is_white else "b"
        send_info_string(
            f"[eval {side}] "
            f"psqt={base_score:+d} "
            f"pawns={pawn_score:+d} "
            f"bishop_pair={dbg_bishop_pair:+d} "
            f"rooks={dbg_rook:+d} "
            f"knight_outpost={dbg_knight_outpost:+d} "
            f"king_safety={dbg_king_safety:+d} "
            f"mobility={dbg_mobility:+d} "
            f"battery={dbg_battery:+d} "
            f"trading={trading_bonus:+d} "
            f"king_activity={dbg_king_activity:+d} "
            f"mop_up={dbg_mop_up:+d} "
            f"phase={mg_phase}/{MAX_PHASE} "
            f"total={evaluation:+d}"
        )

    return evaluation if state.is_white else -evaluation

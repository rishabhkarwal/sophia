# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True

import time
import threading
import engine.core.constants as _const
from engine.core.constants import (
    WHITE, BLACK, INFINITY,
    MAX_DEPTH, TIME_CHECK_NODES, INFINITE_TIME,
    PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
    MASK_SOURCE, NULL as _NULL,
    HISTORY_MAX, HISTORY_GRAVITY,
    FIFTY_MOVE_LIMIT, SYZYGY_PIECE_THRESHOLD,
)
from engine.core.parameters import (
    PIECE_VALUES,
    RAZOR_MARGIN, STATIC_NULL_MARGIN, FUTILITY_MARGIN,
    LMR_BASE_REDUCTION, LMR_MOVE_THRESHOLD,
    LMR_MIN_DEPTH, LMR_NON_PV_REDUCTION,
    PHASE_TRANSITION_EXTENSION,
    LMP_BASE, LMP_MULTIPLIER,
    NMP_BASE_REDUCTION, NMP_DEPTH_REDUCTION, NMP_EVAL_MARGIN,
    NMP_MIN_DEPTH, NMP_DEEP_DEPTH, NMP_EVAL_EXTRA_REDUCTION,
    CHECK_EXTENSION,
    CONTEMPT, LOSING_CONTEMPT_SCALE, REPETITION_PENALTY_WINNING, REPETITION_PENALTY_EQUAL,
    REPETITION_PENALTY_SLIGHT, SLIGHTLY_BETTER_THRESHOLD,
    CLEARLY_WINNING_THRESHOLD, CLEARLY_LOSING_THRESHOLD,
    FIFTY_MOVE_CONTEMPT_BASE, FIFTY_MOVE_SCALE_START,
    ASPIRATION_DELTA, ASPIRATION_WIDEN_FACTOR, ASPIRATION_MIN_DEPTH,
    TIME_HARD_LIMIT_FACTOR, TIME_HARD_LIMIT_OFFSET,
    TIME_CHECK_SWITCH, TIME_CHECK_TIGHT,
    TIME_USAGE_LONG, TIME_USAGE_SHORT, TIME_USAGE_TC_THRESHOLD,
    MATE_SCORE_MARGIN, TIME_PRESSURE_THRESHOLD,
    TB_WIN_SCORE_MARGIN,
    IID_MIN_DEPTH, IID_DEPTH_REDUCTION,
    LMR_HEAVY_THRESHOLD, LMR_HEAVY_REDUCTION,
    RAZORING_DEPTH_CAP, RFP_DEPTH_CAP, SNMP_DEPTH_CAP,
    FUTILITY_DEPTH_CAP, LMP_DEPTH_CAP, SEE_PRUNING_DEPTH_CAP,
    REVERSE_FUTILITY_MARGIN,
    DEFAULT_TIME_LIMIT,
)
from engine.core.move import move_to_uci
from engine.core.move cimport is_capture, is_promotion, is_en_passant
from engine.core.bits cimport popcount
from engine.moves.generator cimport (
    MoveList, generate_pseudo_legal_move_list, generate_check_evasion_move_list,
    is_pseudo_legal_move,
)
from engine.moves.generator import generate_pseudo_legal_moves
from engine.board.move_exec cimport (
    make_move, unmake_move,
    make_null_move, unmake_null_move,
    has_insufficient_material, repetition_count
)
from engine.moves.legality cimport is_in_check
from engine.search.transposition import (
    FLAG_EXACT, FLAG_LOWERBOUND, FLAG_UPPERBOUND
)
from engine.search.transposition cimport TranspositionTable
from engine.search.evaluation cimport evaluate
from engine.search.evaluation import evaluate, PawnHashTable
from engine.search.ordering import MoveOrdering
from engine.search.ordering cimport MoveOrdering, pick_next_move, pick_next_move_list, score_move_list
from engine.uci.utils import send_command, send_info_string
from engine.search.syzygy import SyzygyHandler
from engine.search.utils import _get_cp_score
from engine.board.state cimport State

cdef int _INFINITY       = INFINITY
cdef int _WHITE          = WHITE
cdef int _BLACK          = BLACK
cdef int _CHECK_EXT      = CHECK_EXTENSION
cdef int _LMR_BASE       = LMR_BASE_REDUCTION
cdef int _LMR_THRESH     = LMR_MOVE_THRESHOLD
cdef int _LMP_BASE       = LMP_BASE
cdef int _NMP_BASE       = NMP_BASE_REDUCTION
cdef int _NMP_DEPTH      = NMP_DEPTH_REDUCTION
cdef int _NMP_MIN_DEPTH  = NMP_MIN_DEPTH
cdef int _NMP_DEEP_DEPTH = NMP_DEEP_DEPTH
cdef int _NMP_EVAL_MARGIN = NMP_EVAL_MARGIN
cdef int _NMP_EVAL_EXTRA_RED = NMP_EVAL_EXTRA_REDUCTION
cdef int _LMR_MIN_DEPTH  = LMR_MIN_DEPTH
cdef int _LMR_NON_PV_RED = LMR_NON_PV_REDUCTION
cdef int _PHASE_EXT      = PHASE_TRANSITION_EXTENSION
cdef int _STATIC_NULL    = STATIC_NULL_MARGIN
cdef int _CONTEMPT       = CONTEMPT
cdef double _LOSING_CONTEMPT_SCALE = LOSING_CONTEMPT_SCALE
cdef int _REP_WIN        = REPETITION_PENALTY_WINNING
cdef int _REP_EQUAL      = REPETITION_PENALTY_EQUAL
cdef int _REP_SLIGHT     = REPETITION_PENALTY_SLIGHT
cdef int _SLIGHTLY_BETTER = SLIGHTLY_BETTER_THRESHOLD
cdef int _CLEARLY_WIN    = CLEARLY_WINNING_THRESHOLD
cdef int _CLEARLY_LOSE   = CLEARLY_LOSING_THRESHOLD
cdef int _50MV_BASE      = FIFTY_MOVE_CONTEMPT_BASE
cdef int _50MV_START     = FIFTY_MOVE_SCALE_START
cdef int _MAX_DEPTH      = MAX_DEPTH
cdef int _TIME_CHECK     = TIME_CHECK_NODES
cdef int _LMP_MULT       = LMP_MULTIPLIER
cdef int _QUEEN_VAL      = PIECE_VALUES[QUEEN]
cdef int _PAWN_VAL       = PIECE_VALUES[PAWN]
cdef int _FLAG_EXACT     = FLAG_EXACT
cdef int _FLAG_LB        = FLAG_LOWERBOUND
cdef int _FLAG_UB        = FLAG_UPPERBOUND
cdef int _RFP_MARGIN     = REVERSE_FUTILITY_MARGIN
cdef int _SYZYGY_THRESH  = SYZYGY_PIECE_THRESHOLD
cdef int _TB_WIN_MARGIN  = TB_WIN_SCORE_MARGIN
cdef int _IID_MIN_DEPTH  = IID_MIN_DEPTH
cdef int _IID_DEPTH_RED  = IID_DEPTH_REDUCTION
cdef int _LMR_HEAVY_THRESH = LMR_HEAVY_THRESHOLD
cdef int _LMR_HEAVY_RED  = LMR_HEAVY_REDUCTION
cdef int _RAZOR_CAP      = RAZORING_DEPTH_CAP
cdef int _RFP_CAP        = RFP_DEPTH_CAP
cdef int _SNMP_CAP       = SNMP_DEPTH_CAP
cdef int _FUTILITY_CAP   = FUTILITY_DEPTH_CAP
cdef int _LMP_CAP        = LMP_DEPTH_CAP
cdef int _SEE_CAP        = SEE_PRUNING_DEPTH_CAP
cdef int _50MV_LIMIT     = FIFTY_MOVE_LIMIT
cdef int _TIME_PRESS_THRESH = TIME_PRESSURE_THRESHOLD
cdef int _TIME_CHK_SWITCH   = TIME_CHECK_SWITCH
cdef int _TIME_CHK_TIGHT    = TIME_CHECK_TIGHT
cdef int _MATE_MARGIN       = MATE_SCORE_MARGIN
cdef int _ASP_MIN_DEPTH     = ASPIRATION_MIN_DEPTH
cdef int _ASP_DELTA         = ASPIRATION_DELTA
cdef int _ASP_WIDEN         = ASPIRATION_WIDEN_FACTOR
cdef int _TT_SCORE_BOUND    = INFINITY - 2 * MATE_SCORE_MARGIN

_RAZOR_MARGIN_LIST   = list(RAZOR_MARGIN)
_FUTILITY_MARGIN_LIST = list(FUTILITY_MARGIN)


cdef inline int _score_to_tt(int score, int ply) noexcept:
    if score >= _TT_SCORE_BOUND:
        return score + ply
    if score <= -_TT_SCORE_BOUND:
        return score - ply
    return score


cdef inline int _score_from_tt(int score, int ply) noexcept:
    if score >= _TT_SCORE_BOUND:
        return score - ply
    if score <= -_TT_SCORE_BOUND:
        return score + ply
    return score


cdef inline bint _move_was_tried(unsigned int* tried_moves, int tried_count,
                                 unsigned int move) noexcept:
    cdef int i
    for i in range(tried_count):
        if tried_moves[i] == move:
            return True
    return False


cdef inline bint _move_in_list(MoveList* moves, unsigned int move) noexcept:
    cdef int i
    for i in range(moves.count):
        if moves.moves[i] == move:
            return True
    return False


cdef bint _is_pseudo_search_move(State state, unsigned int move) noexcept:
    if move == 0: return False
    return is_pseudo_legal_move(state, move)


class TimeoutError(Exception):
    """raised when search runs out of time"""
    pass


cdef class SearchEngine:
    def __init__(self, time_limit=DEFAULT_TIME_LIMIT, tt_size_mb=64):
        self.time_limit = time_limit
        self.tt = TranspositionTable(tt_size_mb)
        self.pawn_hash = PawnHashTable(32)
        self.syzygy = SyzygyHandler()
        self.syzygy_cache = {}
        self.ordering = MoveOrdering()
        self.nodes_searched = 0
        self.depth_reached = 0
        self.seldepth = 0
        self.tbhits = 0
        self.start_time = 0.0
        self.limit_start_time = 0.0
        self.root_colour = WHITE

        self.opponent_time_ms = INFINITE_TIME
        self.nodes_limit = None

        # hard and soft time limitss
        self.hard_time_limit = 0.0
        self.soft_time_limit = 0.0
        self.check_interval = TIME_CHECK_NODES

        self.stop_flag = threading.Event()
        self.ponder_move = None

        # debug counters
        self.dbg_nmp_attempts     = 0
        self.dbg_nmp_cutoffs      = 0
        self.dbg_rfp_attempts     = 0
        self.dbg_rfp_cutoffs      = 0
        self.dbg_snmp_attempts    = 0
        self.dbg_snmp_cutoffs     = 0
        self.dbg_razor_attempts   = 0
        self.dbg_razor_cutoffs    = 0
        self.dbg_futility_skips   = 0
        self.dbg_lmp_skips        = 0
        self.dbg_lmr_reductions   = 0
        self.dbg_lmr_researches   = 0
        self.dbg_pvs_researches   = 0
        self.dbg_check_extensions = 0
        self.dbg_iid_triggers     = 0
        self.dbg_iid_tt_hits      = 0
        self.dbg_tt_exact_used    = 0
        self.dbg_tt_bound_cutoff  = 0
        self.dbg_tt_bound_noncutoff = 0
        self.dbg_tt_shallow       = 0
        self.dbg_qnodes           = 0
        self.dbg_qstandpat        = 0
        self.dbg_qdelta_prunes    = 0
        self.dbg_see_tests        = 0
        self.dbg_see_prunes       = 0
        self.dbg_qsee_tests       = 0
        self.dbg_qsee_prunes      = 0
        self.dbg_beta_cutoff_idx  = []
        self.dbg_cutoff_by_tt     = 0
        self.dbg_cutoff_by_killer = 0
        self.dbg_cutoff_by_cap    = 0
        self.dbg_cutoff_by_quiet  = 0
        self.dbg_asp_fail_low     = 0
        self.dbg_asp_fail_high    = 0
        self.dbg_asp_fail_both    = 0
        self.dbg_repetition_draws = 0
        self.dbg_fifty_move_draws = 0
        self.dbg_insuf_mat_draws  = 0
        self.dbg_syzygy_probes    = 0
        self.dbg_syzygy_hits      = 0

    def _check_time(self):
        if self.stop_flag.is_set():
            raise TimeoutError("stop")

        if self.nodes_limit is not None and self.nodes_searched >= self.nodes_limit:
            raise TimeoutError("nodes limit reached")

        elapsed = time.time() - self.limit_start_time

        if elapsed >= self.hard_time_limit:
            raise TimeoutError("hard time limit exceeded")

    def _update_check_interval(self):
        self.check_interval = TIME_CHECK_NODES if self.time_limit > _TIME_CHK_SWITCH else _TIME_CHK_TIGHT

    def _get_pv_line(self, state, max_depth=20):
        pv_moves = []
        undo_stack = []
        seen_hashes = {state.hash}

        for _ in range(max_depth):
            tt_entry = self.tt.probe_entry(state.hash)

            if not tt_entry or tt_entry[4] is None: break

            move = tt_entry[4]
            pv_moves.append(move)

            make_move(state, move)
            undo_stack.append(move)

            if state.hash in seen_hashes: break
            seen_hashes.add(state.hash)

        for move in reversed(undo_stack):
            unmake_move(state, move)

        return ' '.join(move_to_uci(m) for m in pv_moves)

    def get_best_move(self, state, opp_time_ms=INFINITE_TIME, depth_limit=None, nodes_limit=None, is_movetime=False):
        syzygy_result = self.syzygy.get_best_move(state)
        if syzygy_result:
            syzygy_move, wdl, dtz = syzygy_result

            ply = 0
            if wdl > 0: score = _INFINITY - ply - abs(dtz)
            elif wdl < 0: score = -_INFINITY + ply + abs(dtz)
            else: score = 0

            score_str = _get_cp_score(score)
            self.tbhits += 1

            send_command(f"info depth {abs(dtz)} score {score_str} pv {syzygy_move} tbhits {self.tbhits} string syzygy hit")

            self.tt.store(<unsigned long long>state.hash, <short>_MAX_DEPTH,
                          _score_to_tt(score, ply), <unsigned char>_FLAG_EXACT, 0)

            return syzygy_move

        self.opponent_time_ms = opp_time_ms
        self.nodes_limit = nodes_limit

        self.nodes_searched = 0
        self.seldepth = 0
        self.tbhits = 0
        self.syzygy_cache = {}
        self.ponder_move = None
        self.start_time = time.time()
        self.limit_start_time = self.start_time
        self.root_colour = state.is_white

        if _const.DEBUG:
            self.dbg_nmp_attempts     = 0
            self.dbg_nmp_cutoffs      = 0
            self.dbg_rfp_attempts     = 0
            self.dbg_rfp_cutoffs      = 0
            self.dbg_snmp_attempts    = 0
            self.dbg_snmp_cutoffs     = 0
            self.dbg_razor_attempts   = 0
            self.dbg_razor_cutoffs    = 0
            self.dbg_futility_skips   = 0
            self.dbg_lmp_skips        = 0
            self.dbg_lmr_reductions   = 0
            self.dbg_lmr_researches   = 0
            self.dbg_pvs_researches   = 0
            self.dbg_check_extensions = 0
            self.dbg_iid_triggers     = 0
            self.dbg_iid_tt_hits      = 0
            self.dbg_tt_exact_used    = 0
            self.dbg_tt_bound_cutoff  = 0
            self.dbg_tt_bound_noncutoff = 0
            self.dbg_tt_shallow       = 0
            self.dbg_qnodes           = 0
            self.dbg_qstandpat        = 0
            self.dbg_qdelta_prunes    = 0
            self.dbg_see_tests        = 0
            self.dbg_see_prunes       = 0
            self.dbg_qsee_tests       = 0
            self.dbg_qsee_prunes      = 0
            self.dbg_beta_cutoff_idx  = []
            self.dbg_cutoff_by_tt     = 0
            self.dbg_cutoff_by_killer = 0
            self.dbg_cutoff_by_cap    = 0
            self.dbg_cutoff_by_quiet  = 0
            self.dbg_asp_fail_low     = 0
            self.dbg_asp_fail_high    = 0
            self.dbg_asp_fail_both    = 0
            self.dbg_repetition_draws = 0
            self.dbg_fifty_move_draws = 0
            self.dbg_insuf_mat_draws  = 0
            self.dbg_syzygy_probes    = 0
            self.dbg_syzygy_hits      = 0

        # set time limits
        self.soft_time_limit = self.time_limit / 1000.0
        if is_movetime:
            self.hard_time_limit = self.soft_time_limit
        else:
            self.hard_time_limit = min(self.soft_time_limit * TIME_HARD_LIMIT_FACTOR, self.time_limit / 1000.0 + TIME_HARD_LIMIT_OFFSET)
        self._update_check_interval()

        self.depth_reached = 0

        moves = generate_pseudo_legal_moves(state)
        legal_moves = []
        for move in moves:
            make_move(state, move)
            if not is_in_check(state, not state.is_white):
                legal_moves.append(move)
            unmake_move(state, move)

        if not legal_moves: return None

        moves = legal_moves

        captures = []
        quiet = []
        for m in moves:
            if is_capture(<unsigned int>m) or is_promotion(<unsigned int>m): captures.append(m)
            else: quiet.append(m)
        moves = captures + quiet

        best_move_so_far = moves[0]
        current_depth = 1
        current_score = 0

        try:
            while True:
                if depth_limit is not None and current_depth > depth_limit:
                    break

                if best_move_so_far in moves:
                    moves.remove(best_move_so_far)
                    moves.insert(0, best_move_so_far)

                alpha = -_INFINITY
                beta = _INFINITY
                asp_delta = _ASP_DELTA

                if current_depth > _ASP_MIN_DEPTH:
                    alpha = current_score - asp_delta
                    beta  = current_score + asp_delta

                    while True:
                        best_move, score = self._search_root(state, current_depth, moves, alpha, beta)

                        if alpha == -_INFINITY and beta == _INFINITY:
                            break
                        elif score <= alpha:
                            if _const.DEBUG: self.dbg_asp_fail_low += 1
                            send_info_string(f'aspiration fail-low: delta = {asp_delta}')
                            asp_delta *= _ASP_WIDEN
                            alpha = -_INFINITY if asp_delta >= _INFINITY else current_score - asp_delta
                        elif score >= beta:
                            if _const.DEBUG: self.dbg_asp_fail_high += 1
                            send_info_string(f'aspiration fail-high: delta = {asp_delta}')
                            asp_delta *= _ASP_WIDEN
                            beta = _INFINITY if asp_delta >= _INFINITY else current_score + asp_delta
                        else:
                            break
                else:
                    best_move, score = self._search_root(state, current_depth, moves, -_INFINITY, _INFINITY)

                best_move_so_far = best_move
                current_score = score

                self.depth_reached = current_depth

                elapsed = time.time() - self.start_time
                nps = int(self.nodes_searched / elapsed) if elapsed > 0 else 0

                score_str = _get_cp_score(score)

                hashfull = self.tt.get_hashfull()
                pv_string = self._get_pv_line(state, current_depth)

                pv_parts = pv_string.split()
                self.ponder_move = pv_parts[1] if len(pv_parts) >= 2 else None

                send_command(f"info depth {current_depth} seldepth {self.seldepth} score {score_str} nodes {self.nodes_searched} nps {nps} time {int(elapsed * 1000)} hashfull {hashfull} tbhits {self.tbhits} pv {pv_string}")

                if _const.DEBUG:
                    def _pct(n, d):
                        return f"{100 * n // max(d, 1)}%"

                    avg_cutoff_idx = (sum(self.dbg_beta_cutoff_idx) / len(self.dbg_beta_cutoff_idx)) if self.dbg_beta_cutoff_idx else 0
                    first_move_cuts = sum(1 for i in self.dbg_beta_cutoff_idx if i == 0)
                    total_cuts = len(self.dbg_beta_cutoff_idx)
                    qratio = _pct(self.dbg_qnodes, self.nodes_searched)
                    lmr_fail = _pct(self.dbg_lmr_researches, self.dbg_lmr_reductions)
                    syzygy_hit_rate = _pct(self.dbg_syzygy_hits, self.dbg_syzygy_probes) if self.dbg_syzygy_probes else "n/a"
                    iid_hit_rate = _pct(self.dbg_iid_tt_hits, self.dbg_iid_triggers) if self.dbg_iid_triggers else "n/a"
                    tt_total = self.dbg_tt_exact_used + self.dbg_tt_bound_cutoff + self.dbg_tt_bound_noncutoff + self.dbg_tt_shallow

                    send_info_string(
                        f"[dbg prune d{current_depth}] "
                        f"nmp={self.dbg_nmp_attempts}/{self.dbg_nmp_cutoffs}({_pct(self.dbg_nmp_cutoffs, self.dbg_nmp_attempts)}) "
                        f"rfp={self.dbg_rfp_attempts}/{self.dbg_rfp_cutoffs}({_pct(self.dbg_rfp_cutoffs, self.dbg_rfp_attempts)}) "
                        f"snmp={self.dbg_snmp_attempts}/{self.dbg_snmp_cutoffs}({_pct(self.dbg_snmp_cutoffs, self.dbg_snmp_attempts)}) "
                        f"razor={self.dbg_razor_attempts}/{self.dbg_razor_cutoffs}({_pct(self.dbg_razor_cutoffs, self.dbg_razor_attempts)}) "
                        f"futility={self.dbg_futility_skips} lmp={self.dbg_lmp_skips}"
                    )
                    send_info_string(
                        f"[dbg search d{current_depth}] "
                        f"tt_exact={self.dbg_tt_exact_used} tt_bound_cut={self.dbg_tt_bound_cutoff} tt_bound_nc={self.dbg_tt_bound_noncutoff} tt_shallow={self.dbg_tt_shallow}(of {tt_total}) "
                        f"lmr={self.dbg_lmr_reductions}(re={self.dbg_lmr_researches},{lmr_fail}) "
                        f"pvs_re={self.dbg_pvs_researches} "
                        f"check_ext={self.dbg_check_extensions} "
                        f"iid={self.dbg_iid_triggers}(tt_hit={iid_hit_rate}) "
                        f"asp=lo:{self.dbg_asp_fail_low}/hi:{self.dbg_asp_fail_high}/both:{self.dbg_asp_fail_both}"
                    )
                    send_info_string(
                        f"[dbg q/order d{current_depth}] "
                        f"qnodes={self.dbg_qnodes}({qratio}) standpat={self.dbg_qstandpat} qdelta={self.dbg_qdelta_prunes} "
                        f"see={self.dbg_see_prunes}/{self.dbg_see_tests} qsee={self.dbg_qsee_prunes}/{self.dbg_qsee_tests} "
                        f"cutoff_src=tt:{self.dbg_cutoff_by_tt}/killer:{self.dbg_cutoff_by_killer}/cap:{self.dbg_cutoff_by_cap}/quiet:{self.dbg_cutoff_by_quiet} "
                        f"cutoff_idx=avg{avg_cutoff_idx:.1f}(1st={first_move_cuts}/{total_cuts}) "
                        f"syzygy={self.dbg_syzygy_probes}(hit={syzygy_hit_rate}) "
                        f"draws=rep:{self.dbg_repetition_draws}+50mv:{self.dbg_fifty_move_draws}+insuf:{self.dbg_insuf_mat_draws}"
                    )

                    # reset per-depth counters
                    self.dbg_nmp_attempts     = 0
                    self.dbg_nmp_cutoffs      = 0
                    self.dbg_rfp_attempts     = 0
                    self.dbg_rfp_cutoffs      = 0
                    self.dbg_snmp_attempts    = 0
                    self.dbg_snmp_cutoffs     = 0
                    self.dbg_razor_attempts   = 0
                    self.dbg_razor_cutoffs    = 0
                    self.dbg_futility_skips   = 0
                    self.dbg_lmp_skips        = 0
                    self.dbg_lmr_reductions   = 0
                    self.dbg_lmr_researches   = 0
                    self.dbg_pvs_researches   = 0
                    self.dbg_check_extensions = 0
                    self.dbg_iid_triggers     = 0
                    self.dbg_iid_tt_hits      = 0
                    self.dbg_tt_exact_used    = 0
                    self.dbg_tt_bound_cutoff  = 0
                    self.dbg_tt_bound_noncutoff = 0
                    self.dbg_tt_shallow       = 0
                    self.dbg_qnodes           = 0
                    self.dbg_qstandpat        = 0
                    self.dbg_qdelta_prunes    = 0
                    self.dbg_see_tests        = 0
                    self.dbg_see_prunes       = 0
                    self.dbg_qsee_tests       = 0
                    self.dbg_qsee_prunes      = 0
                    self.dbg_beta_cutoff_idx  = []
                    self.dbg_cutoff_by_tt     = 0
                    self.dbg_cutoff_by_killer = 0
                    self.dbg_cutoff_by_cap    = 0
                    self.dbg_cutoff_by_quiet  = 0
                    self.dbg_asp_fail_low     = 0
                    self.dbg_asp_fail_high    = 0
                    self.dbg_asp_fail_both    = 0
                    self.dbg_repetition_draws = 0
                    self.dbg_fifty_move_draws = 0
                    self.dbg_insuf_mat_draws  = 0
                    self.dbg_syzygy_probes    = 0
                    self.dbg_syzygy_hits      = 0

                if abs(score) >= _INFINITY - _MATE_MARGIN:
                    break

                if not is_movetime and depth_limit is None and nodes_limit is None:
                    time_usage_pct = TIME_USAGE_LONG if self.time_limit > TIME_USAGE_TC_THRESHOLD else TIME_USAGE_SHORT
                    elapsed = time.time() - self.limit_start_time
                    if elapsed > self.soft_time_limit * time_usage_pct:
                        break

                current_depth += 1
                if current_depth > _MAX_DEPTH: break

        except TimeoutError:
            pass

        return best_move_so_far

    def _search_root(self, State state, int depth, list moves, int alpha, int beta):
        cdef int best_value
        cdef int ply
        cdef int i
        cdef unsigned int move
        cdef int child_depth
        cdef int old_phase
        cdef int value
        cdef int alpha_orig, beta_orig, flag
        cdef unsigned int tt_move, k1, k2, counter
        cdef object tt_entry, best_move

        alpha_orig = alpha
        beta_orig = beta

        tt_entry = self.tt.probe_entry(state.hash)
        tt_move = <unsigned int>tt_entry[4] if (tt_entry and tt_entry[4] is not None) else 0

        k1 = self.ordering.killer_moves[depth][0]
        k2 = self.ordering.killer_moves[depth][1]
        counter = self.ordering.get_countermove(0)

        best_move = moves[0]
        best_value = -_INFINITY * 10
        ply = 0

        for i in range(len(moves)):
            pick_next_move(moves, i, state, self.ordering, tt_move, counter, depth, k1, k2)
            move = moves[i]

            old_phase = state.phase
            make_move(state, move)
            child_depth = depth - 1
            if old_phase > 0 and state.phase == 0:
                child_depth += _PHASE_EXT

            if i == 0:
                value = -self._alpha_beta(state, child_depth, -beta, -alpha, ply + 1, move, True, True)
            else:
                value = -self._alpha_beta(state, child_depth, -(alpha + 1), -alpha, ply + 1, move, True, False)
                if alpha < value < beta:
                    value = -self._alpha_beta(state, child_depth, -beta, -alpha, ply + 1, move, True, True)

            unmake_move(state, move)

            if value > best_value:
                best_value = value
                best_move = move

            if value > alpha:
                alpha = value
                if alpha >= beta:
                    self.tt.store(<unsigned long long>state.hash, <short>depth,
                                  _score_to_tt(alpha, ply),
                                  <unsigned char>_FLAG_LB, move)
                    return best_move, alpha

        flag = _FLAG_EXACT
        if best_value <= alpha_orig: flag = _FLAG_UB
        elif best_value >= beta_orig: flag = _FLAG_LB

        self.tt.store(<unsigned long long>state.hash, <short>depth,
                      _score_to_tt(best_value, ply),
                      <unsigned char>flag,
                      <unsigned int>best_move if best_move is not None else 0)

        return best_move, best_value

    cdef int _alpha_beta(self, State state, int depth, int alpha, int beta, int ply,
                         unsigned int previous_move, bint allow_null, bint is_pv) except? -32768:
        cdef int mating_value, mated_value, static_eval, scaled_contempt
        cdef int score, TB_WIN_SCORE, reduced_depth, reduction
        cdef int rfp_margin, futility_margin, alpha_orig
        cdef int legal_moves_count, i, j, old_phase, child_depth
        cdef int lmp_threshold, best_value, value, val, flag
        cdef int repeat_count, stage, stage_limit, tried_count
        cdef unsigned int move, candidate
        cdef bint in_check, gives_check, is_interesting, do_futility
        cdef bint needs_full, time_pressure_mode, see_ok, use_staged
        cdef unsigned int tt_move, k1, k2, counter
        cdef object best_move
        cdef MoveList moves, bad_moves
        cdef int scores[256]
        cdef signed char see_cache[256]
        cdef unsigned int tried_moves[256]
        cdef unsigned int quiet_moves_tried[256]
        cdef int quiet_moves_count
        cdef unsigned int q
        # tt probe output — c locals extracted immediately to avoid stale pointer after recursion
        cdef short         _tt_depth
        cdef int           _tt_score
        cdef unsigned char _tt_flag
        cdef unsigned int  _tt_move_raw
        cdef bint          _tt_hit, _iid_hit
        cdef unsigned long long all_pieces

        if ply > self.seldepth: self.seldepth = ply

        self.nodes_searched += 1

        if (self.nodes_searched & self.check_interval) == 0:
            self._check_time()

        mating_value = _INFINITY - ply
        if mating_value < beta:
            beta = mating_value
            if alpha >= mating_value:
                return mating_value

        mated_value = -_INFINITY + ply
        if mated_value > alpha:
            alpha = mated_value
            if beta <= mated_value:
                return mated_value

        repeat_count = repetition_count(state)
        is_threefold = repeat_count >= 2
        is_fivefold = repeat_count >= 4

        if is_threefold or is_fivefold:
            if _const.DEBUG: self.dbg_repetition_draws += 1
            static_eval = evaluate(state, self.pawn_hash)

            if is_fivefold:
                if static_eval > _CLEARLY_WIN:
                    return -_REP_WIN
                elif static_eval > _SLIGHTLY_BETTER:
                    return -_REP_SLIGHT
                elif static_eval < _CLEARLY_LOSE:
                    return 0
                else:
                    return -_CONTEMPT

            if static_eval > _CLEARLY_WIN:
                return -_REP_WIN
            elif static_eval > _SLIGHTLY_BETTER:
                return -_REP_SLIGHT
            elif static_eval >= -_SLIGHTLY_BETTER:
                return -_REP_EQUAL
            elif static_eval < _CLEARLY_LOSE:
                return 0
            else:
                return -_CONTEMPT

        # 50-move rule with scaled contempt
        if state.halfmove_clock >= _50MV_START:
            if _const.DEBUG: self.dbg_fifty_move_draws += 1
            static_eval = evaluate(state, self.pawn_hash)

            if state.halfmove_clock >= _50MV_LIMIT:
                if static_eval > _CLEARLY_WIN:
                    return static_eval - _50MV_BASE
                elif static_eval < _CLEARLY_LOSE:
                    return 0
                else:
                    return -_CONTEMPT
            else:
                progress = (state.halfmove_clock - _50MV_START) / (_50MV_LIMIT - _50MV_START)
                scaled_contempt = int(_50MV_BASE * progress)

                if static_eval > _CLEARLY_WIN:
                    return static_eval - scaled_contempt
                elif static_eval < _CLEARLY_LOSE:
                    return -<int>(scaled_contempt * _LOSING_CONTEMPT_SCALE)
                else:
                    return -scaled_contempt

        # insufficient material
        if has_insufficient_material(state):
            if _const.DEBUG: self.dbg_insuf_mat_draws += 1
            static_eval = evaluate(state, self.pawn_hash)
            if static_eval > _SLIGHTLY_BETTER:
                return -_CONTEMPT
            return 0

        _tt_hit = self.tt.probe(<unsigned long long>state.hash,
                                &_tt_depth, &_tt_score, &_tt_flag, &_tt_move_raw)
        if _tt_hit:
            _tt_score = _score_from_tt(_tt_score, ply)
        if _tt_hit and _tt_depth >= depth:
            if _tt_flag == _FLAG_EXACT:
                if _const.DEBUG: self.dbg_tt_exact_used += 1
                return _tt_score
            elif _tt_flag == _FLAG_LB: alpha = max(alpha, _tt_score)
            elif _tt_flag == _FLAG_UB: beta = min(beta, _tt_score)
            if alpha >= beta:
                if _const.DEBUG: self.dbg_tt_bound_cutoff += 1
                return _tt_score
            if _const.DEBUG: self.dbg_tt_bound_noncutoff += 1
        elif _const.DEBUG and _tt_hit and _tt_depth < depth:
            self.dbg_tt_shallow += 1

        if depth <= 0: return self._quiescence(state, alpha, beta, ply)

        all_pieces = state.bitboards[_WHITE] | state.bitboards[_BLACK]
        if popcount(all_pieces) <= _SYZYGY_THRESH:
            if _const.DEBUG: self.dbg_syzygy_probes += 1
            cached = self.syzygy_cache.get(state.hash)
            if cached is None:
                wdl = self.syzygy.probe_wdl(state)
                if wdl is not None:
                    dtz = self.syzygy.probe_dtz(state)
                    self.syzygy_cache[state.hash] = (wdl, dtz)
                    cached = (wdl, dtz)
            if cached is not None:
                if _const.DEBUG: self.dbg_syzygy_hits += 1
                self.tbhits += 1
                wdl, dtz = cached
                TB_WIN_SCORE = _INFINITY - _TB_WIN_MARGIN

                if wdl > 0: score = TB_WIN_SCORE - ply - abs(dtz)
                elif wdl < 0: score = -TB_WIN_SCORE + ply + abs(dtz)
                else: score = 0

                self.tt.store(<unsigned long long>state.hash, <short>depth,
                              _score_to_tt(score, ply),
                              <unsigned char>_FLAG_EXACT, 0)
                return score

        in_check = is_in_check(state, state.is_white)

        # check extension
        if in_check:
            depth += _CHECK_EXT
            if _const.DEBUG: self.dbg_check_extensions += 1

        # IID
        if is_pv and depth >= _IID_MIN_DEPTH and not _tt_hit:
            if _const.DEBUG: self.dbg_iid_triggers += 1
            reduced_depth = depth - _IID_DEPTH_RED
            self._alpha_beta(state, reduced_depth, alpha, beta, ply, previous_move, True, True)
            _iid_hit = self.tt.probe(<unsigned long long>state.hash,
                                     &_tt_depth, &_tt_score, &_tt_flag, &_tt_move_raw)
            if _iid_hit:
                _tt_hit = True
            if _const.DEBUG and _iid_hit: self.dbg_iid_tt_hits += 1

        # static eval for pruning
        static_eval = evaluate(state, self.pawn_hash) if not in_check else 0

        # razoring
        if not is_pv and not in_check and depth <= _RAZOR_CAP and allow_null:
            if depth < len(_RAZOR_MARGIN_LIST) and static_eval + _RAZOR_MARGIN_LIST[depth] < alpha:
                if _const.DEBUG: self.dbg_razor_attempts += 1
                razor_score = self._quiescence(state, alpha - 1, alpha, ply)
                if razor_score < alpha:
                    if _const.DEBUG: self.dbg_razor_cutoffs += 1
                    return razor_score

        # reverse futility pruning
        if not is_pv and not in_check and depth <= _RFP_CAP and allow_null and state.phase > 0:
            rfp_margin = _RFP_MARGIN * depth
            if _const.DEBUG: self.dbg_rfp_attempts += 1
            if static_eval - rfp_margin >= beta:
                if _const.DEBUG: self.dbg_rfp_cutoffs += 1
                return static_eval - rfp_margin

        # static null move pruning
        if not is_pv and not in_check and depth <= _SNMP_CAP and allow_null and state.phase > 0:
            if _const.DEBUG: self.dbg_snmp_attempts += 1
            if static_eval - _STATIC_NULL >= beta:
                if _const.DEBUG: self.dbg_snmp_cutoffs += 1
                return static_eval

        # adaptive null move pruning
        if allow_null and depth >= _NMP_MIN_DEPTH and not in_check and not is_pv and state.phase > 0:
            if _const.DEBUG: self.dbg_nmp_attempts += 1
            make_null_move(state)

            reduction = _NMP_BASE
            if depth >= _NMP_DEEP_DEPTH: reduction = _NMP_DEPTH
            if static_eval > beta + _NMP_EVAL_MARGIN: reduction += _NMP_EVAL_EXTRA_RED

            val = -self._alpha_beta(state, depth - 1 - reduction, -beta, -beta + 1, ply + 1, 0, False, False)
            unmake_null_move(state)

            if val >= beta:
                if _const.DEBUG: self.dbg_nmp_cutoffs += 1
                return beta

        # futility pruning
        do_futility = False
        if not is_pv and not in_check and depth <= _FUTILITY_CAP and allow_null:
            if depth < len(_FUTILITY_MARGIN_LIST):
                futility_margin = _FUTILITY_MARGIN_LIST[depth]
                if static_eval + futility_margin < alpha:
                    do_futility = True

        alpha_orig = alpha
        tt_move = _tt_move_raw if (_tt_hit and _tt_move_raw != 0) else 0
        k1 = self.ordering.killer_moves[depth][0]
        k2 = self.ordering.killer_moves[depth][1]
        counter = self.ordering.get_countermove(previous_move)

        best_value = -_INFINITY * 10
        best_move = None
        legal_moves_count = 0
        quiet_moves_count = 0

        time_pressure_mode = self.opponent_time_ms < _TIME_PRESS_THRESH

        use_staged = not in_check
        tried_count = 0
        bad_moves.count = 0
        stage = 0
        stage_limit = 5 if use_staged else 2

        while stage < stage_limit:
            moves.count = 0

            if stage == 0:
                if tt_move != 0 and _is_pseudo_search_move(state, tt_move):
                    moves.moves[0] = tt_move
                    moves.count = 1
            elif not use_staged:
                generate_check_evasion_move_list(state, &moves)
            elif stage == 1:
                generate_pseudo_legal_move_list(state, &moves, True)
            elif stage == 2:
                for j in range(3):
                    if j == 0:
                        candidate = counter
                    elif j == 1:
                        candidate = k1
                    else:
                        candidate = k2

                    if candidate == 0: continue
                    if _move_was_tried(tried_moves, tried_count, candidate): continue
                    if _move_in_list(&moves, candidate): continue
                    if is_capture(candidate) or is_en_passant(candidate) or is_promotion(candidate): continue
                    if not _is_pseudo_search_move(state, candidate): continue

                    moves.moves[moves.count] = candidate
                    moves.count += 1
            elif stage == 3:
                generate_pseudo_legal_move_list(state, &moves, False)
            else:
                for j in range(bad_moves.count):
                    moves.moves[j] = bad_moves.moves[j]
                moves.count = bad_moves.count

            if moves.count != 0:
                score_move_list(&moves, scores, see_cache, state, self.ordering, tt_move, counter, depth, k1, k2)

            for i in range(moves.count):
                pick_next_move_list(&moves, scores, see_cache, i)
                move = moves.moves[i]

                if _move_was_tried(tried_moves, tried_count, move):
                    continue

                if use_staged:
                    if stage == 1 and see_cache[i] != 1:
                        if not _move_in_list(&bad_moves, move):
                            bad_moves.moves[bad_moves.count] = move
                            bad_moves.count += 1
                        continue
                    if stage == 3 and (is_capture(move) or is_en_passant(move)):
                        continue

                if tried_count < 256:
                    tried_moves[tried_count] = move
                    tried_count += 1

                see_ok = True
                if is_capture(move) and depth <= _SEE_CAP:
                    see_ok = see_cache[i] == 1

                old_phase = state.phase
                make_move(state, move)

                if is_in_check(state, not state.is_white):
                    unmake_move(state, move)
                    continue

                legal_moves_count += 1

                gives_check = is_in_check(state, state.is_white)

                is_interesting = is_capture(move) or is_en_passant(move) or is_promotion(move)

                if gives_check and time_pressure_mode:
                    is_interesting = True

                if not is_interesting:
                    if quiet_moves_count < 256:
                        quiet_moves_tried[quiet_moves_count] = move
                        quiet_moves_count += 1

                child_depth = depth - 1
                if old_phase > 0 and state.phase == 0:
                    child_depth += _PHASE_EXT

                if do_futility and not is_interesting and not gives_check:
                    if _const.DEBUG: self.dbg_futility_skips += 1
                    unmake_move(state, move)
                    continue

                # late move pruning
                if not is_pv and not in_check and not is_interesting and depth <= _LMP_CAP:
                    lmp_threshold = _LMP_BASE + depth * depth * _LMP_MULT
                    if legal_moves_count > lmp_threshold:
                        if _const.DEBUG: self.dbg_lmp_skips += 1
                        unmake_move(state, move)
                        continue

                # SEE pruning
                if is_capture(move) and depth <= _SEE_CAP and not gives_check:
                    if _const.DEBUG: self.dbg_see_tests += 1
                    if not see_ok:
                        if _const.DEBUG: self.dbg_see_prunes += 1
                        unmake_move(state, move)
                        continue

                needs_full = True

                # late move reduction
                if depth >= _LMR_MIN_DEPTH and legal_moves_count >= _LMR_THRESH and not is_interesting and not in_check and not gives_check and allow_null:
                    if _const.DEBUG: self.dbg_lmr_reductions += 1
                    reduction = _LMR_BASE
                    if legal_moves_count >= _LMR_HEAVY_THRESH: reduction = _LMR_HEAVY_RED
                    if not is_pv: reduction += _LMR_NON_PV_RED

                    reduced_depth = max(1, depth - 1 - reduction)
                    val = -self._alpha_beta(state, reduced_depth, -(alpha+1), -alpha, ply + 1, move, True, False)
                    if val <= alpha:
                        needs_full = False
                    elif _const.DEBUG:
                        self.dbg_lmr_researches += 1

                if needs_full:
                    if legal_moves_count == 1:
                        value = -self._alpha_beta(state, child_depth, -beta, -alpha, ply + 1, move, True, is_pv)
                    else:
                        value = -self._alpha_beta(state, child_depth, -(alpha + 1), -alpha, ply + 1, move, True, False)
                        if alpha < value < beta:
                            if _const.DEBUG: self.dbg_pvs_researches += 1
                            value = -self._alpha_beta(state, child_depth, -beta, -alpha, ply + 1, move, True, is_pv)
                else:
                    value = val

                unmake_move(state, move)

                if value >= beta:
                    if _const.DEBUG:
                        self.dbg_beta_cutoff_idx.append(legal_moves_count - 1)
                        is_cap = is_capture(move)
                        is_tt  = (tt_move != 0 and move == tt_move)
                        is_kil = (move == k1 or move == k2)
                        if is_tt:        self.dbg_cutoff_by_tt     += 1
                        elif is_kil:     self.dbg_cutoff_by_killer += 1
                        elif is_cap:     self.dbg_cutoff_by_cap    += 1
                        else:            self.dbg_cutoff_by_quiet  += 1
                    self.tt.store(<unsigned long long>state.hash, <short>depth,
                                  _score_to_tt(beta, ply),
                                  <unsigned char>_FLAG_LB, move)
                    self.ordering.store_killer(depth, move)
                    self.ordering.store_history(move, depth)
                    self.ordering.store_countermove(previous_move, move)
                    for i in range(quiet_moves_count):
                        q = quiet_moves_tried[i]
                        if q != move:
                            self.ordering.apply_history_malus(q, depth)
                    return beta

                if value > best_value:
                    best_value = value
                    best_move = move

                if value > alpha: alpha = value

            stage += 1

        if legal_moves_count == 0:
            if in_check: return -_INFINITY + ply
            return 0

        if best_move is None:
            return alpha

        flag = _FLAG_EXACT
        if best_value <= alpha_orig: flag = _FLAG_UB

        self.tt.store(<unsigned long long>state.hash, <short>depth,
                      _score_to_tt(best_value, ply),
                      <unsigned char>flag,
                      <unsigned int>best_move if best_move is not None else 0)

        return best_value

    cdef int _quiescence(self, State state, int alpha, int beta, int ply) except? -32768:
        cdef int mating_value, evaluation, delta
        cdef int i, score
        cdef unsigned int move
        cdef bint in_check, legal_moves_found
        cdef unsigned int tt_move
        cdef MoveList moves
        cdef int scores[256]
        cdef signed char see_cache[256]
        cdef unsigned long long key
        # TT probe output
        cdef short         _tt_depth
        cdef int           _tt_score
        cdef unsigned char _tt_flag
        cdef unsigned int  _tt_move_raw
        cdef bint          _tt_hit

        self.nodes_searched += 1
        if _const.DEBUG: self.dbg_qnodes += 1

        key = <unsigned long long>state.hash

        if ply > self.seldepth: self.seldepth = ply

        mating_value = _INFINITY - ply
        if mating_value < beta:
            beta = mating_value
            if alpha >= mating_value:
                return mating_value

        _tt_hit = self.tt.probe(key, &_tt_depth, &_tt_score, &_tt_flag, &_tt_move_raw)

        if _tt_hit:
            _tt_score = _score_from_tt(_tt_score, ply)
            if _tt_flag == _FLAG_EXACT: return _tt_score
            elif _tt_flag == _FLAG_LB:
                if _tt_score >= beta: return _tt_score
            elif _tt_flag == _FLAG_UB:
                if _tt_score <= alpha: return _tt_score

        in_check = is_in_check(state, state.is_white)

        if not in_check:
            evaluation = evaluate(state, self.pawn_hash)

            if evaluation >= beta:
                if _const.DEBUG: self.dbg_qstandpat += 1
                return beta

            delta = _QUEEN_VAL + _PAWN_VAL
            if evaluation < alpha - delta:
                if _const.DEBUG: self.dbg_qdelta_prunes += 1
                return alpha

            if evaluation > alpha:
                alpha = evaluation

        if in_check:
            generate_check_evasion_move_list(state, &moves)
        else:
            generate_pseudo_legal_move_list(state, &moves, True)

        if moves.count == 0:
            if in_check:
                return -_INFINITY + ply
            return alpha

        tt_move = _tt_move_raw if (_tt_hit and _tt_move_raw != 0) else 0

        legal_moves_found = False

        score_move_list(&moves, scores, see_cache, state, self.ordering, tt_move, 0, 0, 0, 0)

        for i in range(moves.count):
            pick_next_move_list(&moves, scores, see_cache, i)
            move = moves.moves[i]

            if not in_check and is_capture(move):
                if _const.DEBUG: self.dbg_qsee_tests += 1
                if see_cache[i] != 1:
                    if _const.DEBUG: self.dbg_qsee_prunes += 1
                    continue

            make_move(state, move)

            if is_in_check(state, not state.is_white):
                unmake_move(state, move)
                continue

            legal_moves_found = True

            score = -self._quiescence(state, -beta, -alpha, ply + 1)
            unmake_move(state, move)

            if score >= beta:
                return beta
            if score > alpha:
                alpha = score

        if in_check and not legal_moves_found:
            return -_INFINITY + ply

        return alpha

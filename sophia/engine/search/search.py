import time
import threading
import engine.core.constants as _const
from engine.core.constants import (
    WHITE, BLACK, INFINITY,
    MAX_DEPTH, TIME_CHECK_NODES, INFINITE_TIME,
    PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
    MASK_SOURCE, NULL, PIECE_VALUES,
    RAZOR_MARGIN, STATIC_NULL_MARGIN, FUTILITY_MARGIN,
    LMR_BASE_REDUCTION, LMR_MOVE_THRESHOLD,
    LMP_BASE, LMP_MULTIPLIER,
    NMP_BASE_REDUCTION, NMP_DEPTH_REDUCTION, NMP_EVAL_MARGIN,
    CHECK_EXTENSION,
    CONTEMPT, REPETITION_PENALTY_WINNING, REPETITION_PENALTY_EQUAL,
    REPETITION_PENALTY_SLIGHT, SLIGHTLY_BETTER_THRESHOLD,
    CLEARLY_WINNING_THRESHOLD, CLEARLY_LOSING_THRESHOLD,
    FIFTY_MOVE_CONTEMPT_BASE, FIFTY_MOVE_SCALE_START,
)
from engine.core.move import (
    CAPTURE_FLAG, PROMO_FLAG, EP_FLAG,
    move_to_uci, SHIFT_TARGET
)
from engine.moves.generator import generate_pseudo_legal_moves
from engine.board.move_exec import (
    make_move, unmake_move,
    make_null_move, unmake_null_move,
    is_repetition, has_insufficient_material
)
from engine.moves.legality import is_in_check
from engine.search.transposition import (
    TranspositionTable,
    FLAG_EXACT, FLAG_LOWERBOUND, FLAG_UPPERBOUND
)
from engine.search.evaluation import evaluate, PawnHashTable
from engine.search.ordering import MoveOrdering, pick_next_move
from engine.search.see import see_fast
from engine.uci.utils import send_command, send_info_string
from engine.search.syzygy import SyzygyHandler
from engine.search.utils import _get_cp_score

class TimeoutError(Exception):
    """Raised when search runs out of time"""
    pass

class SearchEngine:
    def __init__(self, time_limit=2000, tt_size_mb=64):
        self.time_limit = time_limit
        self.tt = TranspositionTable(tt_size_mb)
        self.pawn_hash = PawnHashTable(32)
        self.syzygy = SyzygyHandler()
        self.ordering = MoveOrdering()
        self.nodes_searched = 0
        self.depth_reached = 0
        self.seldepth = 0
        self.tbhits = 0
        self.start_time = 0.0
        self.root_colour = WHITE
        
        # dynamic aspiration windows
        self.aspiration_min = 35
        self.aspiration_max = 500
        self.aspiration_current = int((self.aspiration_min + self.aspiration_max) * 0.8)
        self.aspiration_stability_count = 0
        
        self.opponent_time_ms = INFINITE_TIME
        self.nodes_limit = None

        # hard and soft time limits for better time management
        self.hard_time_limit = 0.0
        self.soft_time_limit = 0.0

        self.stop_flag = threading.Event()
        self.ponder_move = None  # second move of PV from last completed depth

        # debug counters (only meaningful when DEBUG=True)
        # pruning: attempts vs cutoffs (rate = cutoffs/attempts tells you how effective each is)
        self.dbg_nmp_attempts     = 0  # nodes where NMP conditions were met
        self.dbg_nmp_cutoffs      = 0  # NMP searches that beat beta
        self.dbg_rfp_attempts     = 0  # nodes where RFP conditions were met
        self.dbg_rfp_cutoffs      = 0  # RFP cutoffs (static_eval - margin >= beta)
        self.dbg_snmp_attempts    = 0  # nodes where static NMP conditions were met
        self.dbg_snmp_cutoffs     = 0  # static NMP cutoffs (static_eval - STATIC_NULL_MARGIN >= beta)
        self.dbg_razor_attempts   = 0  # nodes where razoring conditions were met
        self.dbg_razor_cutoffs    = 0  # razor qsearch confirmed below alpha
        self.dbg_futility_skips   = 0  # moves skipped by futility pruning
        self.dbg_lmp_skips        = 0  # moves skipped by LMP
        self.dbg_lmr_reductions   = 0  # moves searched at reduced depth
        self.dbg_lmr_researches   = 0  # LMR reductions that beat alpha and triggered re-search
        self.dbg_pvs_researches   = 0  # PVS null-window searches that triggered full re-search
        self.dbg_check_extensions = 0  # check extensions applied
        self.dbg_iid_triggers     = 0  # IID searches triggered
        self.dbg_iid_tt_hits      = 0  # IID triggers that produced a TT move after searching
        # TT: finer breakdown
        self.dbg_tt_exact_used    = 0  # FLAG_EXACT hits used to return immediately
        self.dbg_tt_bound_cutoff  = 0  # bound hits that caused alpha>=beta
        self.dbg_tt_bound_noncutoff = 0  # bound hits that updated alpha/beta but didn't cut
        self.dbg_tt_shallow       = 0  # TT hit but depth too low to use (had to re-search)
        # quiescence
        self.dbg_qnodes           = 0  # quiescence nodes searched
        self.dbg_qstandpat        = 0  # stand-pat cutoffs (eval >= beta in qsearch)
        self.dbg_qdelta_prunes    = 0  # delta prunes (eval < alpha - big_delta)
        # ordering quality
        self.dbg_beta_cutoff_idx  = []  # move index of each beta cutoff (0 = first move)
        self.dbg_cutoff_by_tt     = 0  # beta cutoffs where the cutting move was the TT move
        self.dbg_cutoff_by_killer = 0  # beta cutoffs where the cutting move was a killer
        self.dbg_cutoff_by_cap    = 0  # beta cutoffs by captures
        self.dbg_cutoff_by_quiet  = 0  # beta cutoffs by quiet moves
        # aspiration
        self.dbg_asp_fail_low     = 0  # aspiration fail-lows
        self.dbg_asp_fail_high    = 0  # aspiration fail-highs
        self.dbg_asp_fail_both    = 0  # aspiration failed on both sides (full window fallback)
        # draws / terminals
        self.dbg_repetition_draws = 0  # nodes returning via repetition detection
        self.dbg_fifty_move_draws = 0  # nodes entering 50-move contempt path
        self.dbg_insuf_mat_draws  = 0  # nodes returning via insufficient material
        # syzygy
        self.dbg_syzygy_probes    = 0  # in-search syzygy WDL probes
        self.dbg_syzygy_hits      = 0  # successful syzygy probes
    
    def _check_time(self):
        if self.stop_flag.is_set():
            raise TimeoutError("stop")

        if self.nodes_limit is not None and self.nodes_searched >= self.nodes_limit:
            raise TimeoutError("nodes limit reached")

        elapsed = time.time() - self.start_time

        # hard limit: stop immediately
        if elapsed >= self.hard_time_limit:
            raise TimeoutError("hard time limit exceeded")
    
    def _get_pv_line(self, state, max_depth=20):
        pv_moves = []
        undo_stack = []
        seen_hashes = {state.hash}

        for _ in range(max_depth):
            tt_entry = self.tt.probe(state.hash)

            if not tt_entry or tt_entry.best_move is None: break

            move = tt_entry.best_move
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
            if wdl > 0: score = INFINITY - ply - abs(dtz)
            elif wdl < 0: score = -INFINITY + ply + abs(dtz)
            else: score = 0

            score_str = _get_cp_score(score)
            self.tbhits += 1

            send_command(f"info depth {abs(dtz)} score {score_str} pv {syzygy_move} tbhits {self.tbhits} string syzygy hit")

            self.tt.store(state.hash, MAX_DEPTH, score, FLAG_EXACT, None)

            return syzygy_move
        
        self.opponent_time_ms = opp_time_ms
        self.nodes_limit = nodes_limit

        self.nodes_searched = 0
        self.seldepth = 0
        self.tbhits = 0
        self.ponder_move = None
        self.start_time = time.time()
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
            # if explicit movetime, hard limit is strict
            self.hard_time_limit = self.soft_time_limit
        else:
            # dynamic time management
            self.hard_time_limit = min(self.soft_time_limit * 1.5, self.time_limit / 1000.0 + 0.5)
        
        self.depth_reached = 0
        
        #self.aspiration_current = int((self.aspiration_min + self.aspiration_max) * 0.8)
        #self.aspiration_stability_count = 0

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
            if (m & CAPTURE_FLAG) or (m & PROMO_FLAG): captures.append(m)
            else: quiet.append(m)
        moves = captures + quiet
        
        best_move_so_far = moves[0]
        current_depth = 1
        current_score = 0
        
        # wrap in try-except to catch timeout error
        try:
            while True:
                if depth_limit is not None and current_depth > depth_limit:
                    break

                if best_move_so_far in moves:
                    moves.remove(best_move_so_far)
                    moves.insert(0, best_move_so_far)
                
                alpha = -INFINITY
                beta = INFINITY
                
                if current_depth > 2:
                    alpha = current_score - self.aspiration_current
                    beta = current_score + self.aspiration_current
                    
                    best_move, score = self._search_root(state, current_depth, moves, alpha, beta)
                    
                    if score <= alpha or score >= beta:
                        if _const.DEBUG:
                            if score <= alpha and score >= beta: self.dbg_asp_fail_both += 1
                            elif score <= alpha: self.dbg_asp_fail_low += 1
                            else: self.dbg_asp_fail_high += 1
                        send_info_string(f'aspiration failed: {self.aspiration_current}')
                        self.aspiration_current = min(self.aspiration_current * 2, self.aspiration_max)
                        self.aspiration_stability_count = 0

                        alpha = current_score - self.aspiration_current
                        beta = current_score + self.aspiration_current

                        best_move, score = self._search_root(state, current_depth, moves, alpha, beta)

                        if score <= alpha or score >= beta:
                            send_info_string(f'aspiration failed again: {self.aspiration_current}')
                            self.aspiration_stability_count = 0
                            alpha = -INFINITY
                            beta = INFINITY
                            best_move, score = self._search_root(state, current_depth, moves, alpha, beta)
                    else:
                        self.aspiration_stability_count += 1
                        if self.aspiration_stability_count >= 3:
                            self.aspiration_current = max(self.aspiration_min, int(self.aspiration_current * 0.8))
                            #self.aspiration_stability_count = 0
                            if self.aspiration_current > self.aspiration_min: send_info_string(f'aspiration tightened: {self.aspiration_current}')
                else:
                    best_move, score = self._search_root(state, current_depth, moves, -INFINITY, INFINITY)

                best_move_so_far = best_move
                current_score = score

                self.depth_reached = current_depth

                elapsed = time.time() - self.start_time
                nps = int(self.nodes_searched / elapsed) if elapsed > 0 else 0

                score_str = _get_cp_score(score)

                hashfull = self.tt.get_hashfull()
                pv_string = self._get_pv_line(state, current_depth)

                # cache ponder move from PV while TT is freshly populated
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

                if abs(score) >= INFINITY - 1000:
                    break
                
                if not is_movetime and depth_limit is None and nodes_limit is None:
                    time_usage_pct = 0.7 if self.time_limit > 120000 else 0.9
                    elapsed = time.time() - self.start_time
                    if elapsed > self.soft_time_limit * time_usage_pct:
                        break
                    
                current_depth += 1
                if current_depth > MAX_DEPTH: break
                    
        except TimeoutError:
            pass
                
        return best_move_so_far

    def _search_root(self, state, depth, moves, alpha, beta):
        tt_entry = self.tt.probe(state.hash)
        tt_move = tt_entry.best_move if tt_entry else None
        
        k1 = self.ordering.killer_moves[depth][0]
        k2 = self.ordering.killer_moves[depth][1]
        counter = self.ordering.get_countermove(None)

        best_move = moves[0]
        best_value = -INFINITY * 10
        ply = 0
        
        for i in range(len(moves)):
            pick_next_move(moves, i, state, self.ordering, tt_move, counter, depth, k1, k2)
            move = moves[i]
            
            make_move(state, move)

            if i == 0:
                value = -self._alpha_beta(state, depth - 1, -beta, -alpha, ply + 1, move, is_pv=True)
            else:
                value = -self._alpha_beta(state, depth - 1, -(alpha + 1), -alpha, ply + 1, move, is_pv=False)
                if alpha < value < beta:
                    value = -self._alpha_beta(state, depth - 1, -beta, -alpha, ply + 1, move, is_pv=True)
            
            unmake_move(state, move)
            
            if value > best_value:
                best_value = value
                best_move = move
                
            if value > alpha:
                alpha = value
                if alpha >= beta: return best_move, alpha

        self.tt.store(state.hash, depth, best_value, FLAG_EXACT, best_move)
            
        return best_move, best_value

    def _alpha_beta(self, state, depth, alpha, beta, ply, previous_move=None, allow_null=True, is_pv=False):
        if ply > self.seldepth: self.seldepth = ply

        self.nodes_searched += 1

        # check time more frequently when low on time
        check_interval = TIME_CHECK_NODES if self.time_limit > 10000 else 255
        if (self.nodes_searched & check_interval) == 0:
            self._check_time()

        mating_value = INFINITY - ply
        if mating_value < beta:
            beta = mating_value
            if alpha >= mating_value:
                return mating_value
        
        mated_value = -INFINITY + ply
        if mated_value > alpha:
            alpha = mated_value
            if beta <= mated_value:
                return mated_value
        
        is_threefold, is_fivefold = is_repetition(state)

        if is_threefold or is_fivefold:
            if _const.DEBUG: self.dbg_repetition_draws += 1
            static_eval = evaluate(state, self.pawn_hash)

            if is_fivefold:
                if static_eval > CLEARLY_WINNING_THRESHOLD:
                    return -REPETITION_PENALTY_WINNING
                elif static_eval > SLIGHTLY_BETTER_THRESHOLD:
                    return -REPETITION_PENALTY_SLIGHT
                elif static_eval < CLEARLY_LOSING_THRESHOLD:
                    return 0
                else:
                    return -CONTEMPT

            if static_eval > CLEARLY_WINNING_THRESHOLD:
                return -REPETITION_PENALTY_WINNING
            elif static_eval > SLIGHTLY_BETTER_THRESHOLD:
                return -REPETITION_PENALTY_SLIGHT
            elif static_eval >= -SLIGHTLY_BETTER_THRESHOLD:
                return -REPETITION_PENALTY_EQUAL
            elif static_eval < CLEARLY_LOSING_THRESHOLD:
                return 0
            else:
                return -CONTEMPT

        # 50-move rule with SCALED contempt
        if state.halfmove_clock >= FIFTY_MOVE_SCALE_START:
            if _const.DEBUG: self.dbg_fifty_move_draws += 1
            static_eval = evaluate(state, self.pawn_hash)

            if state.halfmove_clock >= 100:
                if static_eval > CLEARLY_WINNING_THRESHOLD:
                    return static_eval - FIFTY_MOVE_CONTEMPT_BASE
                elif static_eval < CLEARLY_LOSING_THRESHOLD:
                    return 0
                else:
                    return -CONTEMPT
            else:
                progress = (state.halfmove_clock - FIFTY_MOVE_SCALE_START) / (100 - FIFTY_MOVE_SCALE_START)
                scaled_contempt = int(FIFTY_MOVE_CONTEMPT_BASE * progress)

                if static_eval > CLEARLY_WINNING_THRESHOLD:
                    return static_eval - scaled_contempt
                elif static_eval < CLEARLY_LOSING_THRESHOLD:
                    return -scaled_contempt // 2
                else:
                    return -scaled_contempt

        # insufficient material
        if has_insufficient_material(state):
            if _const.DEBUG: self.dbg_insuf_mat_draws += 1
            static_eval = evaluate(state, self.pawn_hash)
            if static_eval > SLIGHTLY_BETTER_THRESHOLD:
                return -CONTEMPT
            return 0

        all_pieces = state.bitboards[WHITE] | state.bitboards[BLACK]
        if all_pieces.bit_count() <= 5:
            if _const.DEBUG: self.dbg_syzygy_probes += 1
            wdl = self.syzygy.probe_wdl(state)
            if wdl is not None:
                if _const.DEBUG: self.dbg_syzygy_hits += 1
                self.tbhits += 1
                dtz = self.syzygy.probe_dtz(state)
                TB_WIN_SCORE = INFINITY - 1000

                if wdl > 0: score = TB_WIN_SCORE - ply - abs(dtz)
                elif wdl < 0: score = -TB_WIN_SCORE + ply + abs(dtz)
                else: score = 0

                self.tt.store(state.hash, depth, score, FLAG_EXACT, None)
                return score

        tt_entry = self.tt.probe(state.hash)
        if tt_entry and tt_entry.depth >= depth:
            if tt_entry.flag == FLAG_EXACT:
                if _const.DEBUG: self.dbg_tt_exact_used += 1
                return tt_entry.score
            elif tt_entry.flag == FLAG_LOWERBOUND: alpha = max(alpha, tt_entry.score)
            elif tt_entry.flag == FLAG_UPPERBOUND: beta = min(beta, tt_entry.score)
            if alpha >= beta:
                if _const.DEBUG: self.dbg_tt_bound_cutoff += 1
                return tt_entry.score
            if _const.DEBUG: self.dbg_tt_bound_noncutoff += 1
        elif _const.DEBUG and tt_entry and tt_entry.depth < depth:
            self.dbg_tt_shallow += 1

        if depth <= 0: return self._quiescence(state, alpha, beta, ply)

        in_check = is_in_check(state, state.is_white)

        # check extension
        if in_check:
            depth += CHECK_EXTENSION
            if _const.DEBUG: self.dbg_check_extensions += 1

        # IID
        if is_pv and depth >= 4 and tt_entry is None:
            if _const.DEBUG: self.dbg_iid_triggers += 1
            reduced_depth = depth - 2
            self._alpha_beta(state, reduced_depth, alpha, beta, ply, previous_move, allow_null=True, is_pv=True)
            tt_entry = self.tt.probe(state.hash)
            if _const.DEBUG and tt_entry: self.dbg_iid_tt_hits += 1

        # get static eval for pruning decisions
        static_eval = evaluate(state, self.pawn_hash) if not in_check else 0

        # razoring (depth 1-3)
        if not is_pv and not in_check and depth <= 3 and allow_null:
            if depth < len(RAZOR_MARGIN) and static_eval + RAZOR_MARGIN[depth] < alpha:
                if _const.DEBUG: self.dbg_razor_attempts += 1
                razor_score = self._quiescence(state, alpha - 1, alpha, ply)
                if razor_score < alpha:
                    if _const.DEBUG: self.dbg_razor_cutoffs += 1
                    return razor_score

        # reverse futility pruning
        if not is_pv and not in_check and depth <= 3 and allow_null:
            rfp_margin = 120 * depth
            if _const.DEBUG: self.dbg_rfp_attempts += 1
            if static_eval - rfp_margin >= beta:
                if _const.DEBUG: self.dbg_rfp_cutoffs += 1
                return static_eval - rfp_margin

        # static null move pruning
        if not is_pv and not in_check and depth <= 3 and allow_null:
            if _const.DEBUG: self.dbg_snmp_attempts += 1
            if static_eval - STATIC_NULL_MARGIN >= beta:
                if _const.DEBUG: self.dbg_snmp_cutoffs += 1
                return static_eval

        # adaptive null move pruning
        if allow_null and depth >= 3 and not in_check and not is_pv:
            if _const.DEBUG: self.dbg_nmp_attempts += 1
            make_null_move(state)

            # adaptive reduction
            reduction = NMP_BASE_REDUCTION
            if depth >= 6: reduction = NMP_DEPTH_REDUCTION
            if static_eval > beta + NMP_EVAL_MARGIN: reduction += 1

            val = -self._alpha_beta(state, depth - 1 - reduction, -beta, -beta + 1, ply + 1, None, allow_null=False, is_pv=False)
            unmake_null_move(state)

            if val >= beta:
                if _const.DEBUG: self.dbg_nmp_cutoffs += 1
                return beta

        # futility pruning
        do_futility = False
        if not is_pv and not in_check and depth <= 3 and allow_null:
            if depth < len(FUTILITY_MARGIN):
                futility_margin = FUTILITY_MARGIN[depth]
                if static_eval + futility_margin < alpha:
                    do_futility = True

        moves = generate_pseudo_legal_moves(state)

        tt_move = tt_entry.best_move if tt_entry else None
        k1 = self.ordering.killer_moves[depth][0]
        k2 = self.ordering.killer_moves[depth][1]
        counter = self.ordering.get_countermove(previous_move)
        
        best_value = -INFINITY * 10
        best_move = None
        legal_moves_count = 0
        quiet_moves_tried = []

        time_pressure_mode = self.opponent_time_ms < 10_000

        for i in range(len(moves)):
            pick_next_move(moves, i, state, self.ordering, tt_move, counter, depth, k1, k2)
            move = moves[i]
            
            make_move(state, move)
            
            if is_in_check(state, not state.is_white):
                unmake_move(state, move)
                continue
            
            legal_moves_count += 1
            
            gives_check = is_in_check(state, state.is_white)

            is_interesting = (move & CAPTURE_FLAG) or (move & EP_FLAG) or (move & PROMO_FLAG)

            if gives_check and time_pressure_mode:
                is_interesting = True

            if not is_interesting:
                quiet_moves_tried.append(move)

            if do_futility and not is_interesting and not gives_check:
                if _const.DEBUG: self.dbg_futility_skips += 1
                unmake_move(state, move)
                continue

            # late move pruning
            if not is_pv and not in_check and not is_interesting and depth <= 4:
                lmp_threshold = LMP_BASE + depth * depth * LMP_MULTIPLIER
                if legal_moves_count > lmp_threshold:
                    if _const.DEBUG: self.dbg_lmp_skips += 1
                    unmake_move(state, move)
                    continue

            # SEE pruning
            if (move & CAPTURE_FLAG) and depth <= 6 and not gives_check:
                if not see_fast(state, move, threshold=0):
                    unmake_move(state, move)
                    continue

            needs_full = True

            # late move reduction
            if depth >= 3 and legal_moves_count >= LMR_MOVE_THRESHOLD and not is_interesting and not in_check and not gives_check:
                if _const.DEBUG: self.dbg_lmr_reductions += 1
                reduction = LMR_BASE_REDUCTION
                if legal_moves_count >= 10: reduction = 2
                if not is_pv: reduction += 1
                if gives_check and time_pressure_mode:
                    reduction = max(0, reduction - 1)

                reduced_depth = max(1, depth - 1 - reduction)
                val = -self._alpha_beta(state, reduced_depth, -(alpha+1), -alpha, ply + 1, move, allow_null=True, is_pv=False)
                if val <= alpha:
                    needs_full = False
                elif _const.DEBUG:
                    self.dbg_lmr_researches += 1

            if needs_full:
                if legal_moves_count == 1:
                    value = -self._alpha_beta(state, depth - 1, -beta, -alpha, ply + 1, move, allow_null=True, is_pv=is_pv)
                else:
                    value = -self._alpha_beta(state, depth - 1, -(alpha + 1), -alpha, ply + 1, move, allow_null=True, is_pv=False)
                    if alpha < value < beta:
                        if _const.DEBUG: self.dbg_pvs_researches += 1
                        value = -self._alpha_beta(state, depth - 1, -beta, -alpha, ply + 1, move, allow_null=True, is_pv=is_pv)
            else:
                value = val

            unmake_move(state, move)

            if value >= beta:
                if _const.DEBUG:
                    self.dbg_beta_cutoff_idx.append(legal_moves_count - 1)
                    is_cap = bool(move & CAPTURE_FLAG)
                    is_tt  = (tt_move is not None and move == tt_move)
                    is_kil = (move == k1 or move == k2)
                    if is_tt:        self.dbg_cutoff_by_tt     += 1
                    elif is_kil:     self.dbg_cutoff_by_killer += 1
                    elif is_cap:     self.dbg_cutoff_by_cap    += 1
                    else:            self.dbg_cutoff_by_quiet  += 1
                self.tt.store(state.hash, depth, beta, FLAG_LOWERBOUND, move)
                self.ordering.store_killer(depth, move)
                self.ordering.store_history(move, depth)
                self.ordering.store_countermove(previous_move, move)
                for q in quiet_moves_tried:
                    if q != move:
                        self.ordering.apply_history_malus(q, depth)
                return beta
            
            if value > best_value:
                best_value = value
                best_move = move
                
            if value > alpha: alpha = value

        if legal_moves_count == 0:
            if in_check: return -INFINITY + ply
            return 0

        flag = FLAG_EXACT
        if best_value <= alpha: flag = FLAG_UPPERBOUND
        
        self.tt.store(state.hash, depth, best_value, flag, best_move)
            
        return best_value

    def _quiescence(self, state, alpha, beta, ply):
        self.nodes_searched += 1
        if _const.DEBUG: self.dbg_qnodes += 1

        if ply > self.seldepth: self.seldepth = ply

        mating_value = INFINITY - ply
        if mating_value < beta:
            beta = mating_value
            if alpha >= mating_value:
                return mating_value

        tt_entry = self.tt.probe(state.hash)
        
        if tt_entry:
            if tt_entry.flag == FLAG_EXACT: return tt_entry.score
            elif tt_entry.flag == FLAG_LOWERBOUND:
                if tt_entry.score >= beta: return tt_entry.score
            elif tt_entry.flag == FLAG_UPPERBOUND:
                if tt_entry.score <= alpha: return tt_entry.score

        in_check = is_in_check(state, state.is_white)
        
        if not in_check:
            evaluation = evaluate(state, self.pawn_hash)

            if evaluation >= beta:
                if _const.DEBUG: self.dbg_qstandpat += 1
                return beta

            delta = PIECE_VALUES[QUEEN] + PIECE_VALUES[PAWN]
            if evaluation < alpha - delta:
                if _const.DEBUG: self.dbg_qdelta_prunes += 1
                return alpha

            if evaluation > alpha:
                alpha = evaluation
        
        if in_check:
            moves = generate_pseudo_legal_moves(state, captures_only=False)
        else:
            moves = generate_pseudo_legal_moves(state, captures_only=True)
        
        tt_move = tt_entry.best_move if tt_entry else None
        
        legal_moves_found = False
        
        for i in range(len(moves)):
            pick_next_move(moves, i, state, self.ordering, tt_move, None, 0, None, None)
            move = moves[i]
            
            if not in_check and (move & CAPTURE_FLAG):
                if not see_fast(state, move, threshold=0):
                    continue
            
            make_move(state, move)
            
            if is_in_check(state, not state.is_white):
                unmake_move(state, move)
                continue
            
            legal_moves_found = True
            
            score = -self._quiescence(state, -beta, -alpha, ply + 1)
            unmake_move(state, move)
            
            if score >= beta: return beta
            if score > alpha: alpha = score
        
        if in_check and not legal_moves_found:
             return -INFINITY + ply

        return alpha
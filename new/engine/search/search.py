import time
from engine.core.constants import (
    WHITE, BLACK, INFINITY,
    MAX_DEPTH, TIME_CHECK_NODES,
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
    FIFTY_MOVE_CONTEMPT_BASE, FIFTY_MOVE_SCALE_START
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
        
        self.opponent_time_ms = 999999
        
        self.hard_time_limit = 0.0  # absolute maximum time
        self.soft_time_limit = 0.0  # preferred time to stop
    
    def _check_time(self):
        """Check if we've exceeded time limits - raises TimeoutError"""
        elapsed = time.time() - self.start_time
        
        # hard limit: MUST stop immediately
        if elapsed >= self.hard_time_limit:
            raise TimeoutError("Hard time limit exceeded")
        
        # soft limit: should stop at next opportunity
        if elapsed >= self.soft_time_limit:
            raise TimeoutError("Soft time limit exceeded")
    
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

    def get_best_move(self, state, opp_time_ms=999999):
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

        self.nodes_searched = 0
        self.seldepth = 0
        self.tbhits = 0
        self.start_time = time.time()
        self.root_colour = state.is_white
        
        # set time limits
        self.soft_time_limit = self.time_limit / 1000.0
        self.hard_time_limit = min(self.soft_time_limit * 1.5, self.time_limit / 1000.0 + 0.5)
        
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
            if (m & CAPTURE_FLAG) or (m & PROMO_FLAG): captures.append(m)
            else: quiet.append(m)
        moves = captures + quiet
        
        best_move_so_far = moves[0]
        current_depth = 1
        current_score = 0
        
        try:
            while True:
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

                send_command(f"info depth {current_depth} seldepth {self.seldepth} score {score_str} nodes {self.nodes_searched} nps {nps} time {int(elapsed * 1000)} hashfull {hashfull} tbhits {self.tbhits} pv {pv_string}")

                if abs(score) >= INFINITY - 1000:
                    break
                
                # stop if we've used 70% of soft time limit
                if elapsed > self.soft_time_limit * 0.7:
                    break
                    
                current_depth += 1
                if current_depth > MAX_DEPTH: break
                    
        except TimeoutError:
            pass  # Time's up, return best move found
                
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
        check_interval = TIME_CHECK_NODES if self.opponent_time_ms > 10000 else 255
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

        if state.halfmove_clock >= FIFTY_MOVE_SCALE_START:
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

        if has_insufficient_material(state):
            static_eval = evaluate(state, self.pawn_hash)
            if static_eval > SLIGHTLY_BETTER_THRESHOLD:
                return -CONTEMPT
            return 0

        all_pieces = state.bitboards[WHITE] | state.bitboards[BLACK]
        if all_pieces.bit_count() <= 5:
            wdl = self.syzygy.probe_wdl(state)
            if wdl is not None:
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
            if tt_entry.flag == FLAG_EXACT: return tt_entry.score
            elif tt_entry.flag == FLAG_LOWERBOUND: alpha = max(alpha, tt_entry.score)
            elif tt_entry.flag == FLAG_UPPERBOUND: beta = min(beta, tt_entry.score)
            if alpha >= beta: return tt_entry.score

        if depth <= 0: return self._quiescence(state, alpha, beta, ply)

        in_check = is_in_check(state, state.is_white)
        
        if in_check:
            depth += CHECK_EXTENSION

        if is_pv and depth >= 4 and tt_entry is None:
            reduced_depth = depth - 2
            self._alpha_beta(state, reduced_depth, alpha, beta, ply, previous_move, allow_null=True, is_pv=True)
            tt_entry = self.tt.probe(state.hash)

        static_eval = evaluate(state, self.pawn_hash) if not in_check else 0

        if not is_pv and not in_check and depth <= 3 and allow_null:
            if depth < len(RAZOR_MARGIN) and static_eval + RAZOR_MARGIN[depth] < alpha:
                razor_score = self._quiescence(state, alpha - 1, alpha, ply)
                if razor_score < alpha:
                    return razor_score

        if not is_pv and not in_check and depth <= 3 and allow_null:
            rfp_margin = 120 * depth
            if static_eval - rfp_margin >= beta:
                return static_eval - rfp_margin

        if not is_pv and not in_check and depth <= 3 and allow_null:
            if static_eval - STATIC_NULL_MARGIN >= beta:
                return static_eval

        if allow_null and depth >= 3 and not in_check and not is_pv:
            make_null_move(state)

            reduction = NMP_BASE_REDUCTION
            if depth >= 6: reduction = NMP_DEPTH_REDUCTION
            if static_eval > beta + NMP_EVAL_MARGIN: reduction += 1

            val = -self._alpha_beta(state, depth - 1 - reduction, -beta, -beta + 1, ply + 1, None, allow_null=False, is_pv=False)
            unmake_null_move(state)
            
            if val >= beta: return beta

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
        
        time_pressure_mode = (self.opponent_time_ms < 10000 and abs(best_value) < 100)
        
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
            
            if do_futility and not is_interesting and not gives_check:
                unmake_move(state, move)
                continue
            
            if not is_pv and not in_check and not is_interesting and depth <= 4:
                lmp_threshold = LMP_BASE + depth * depth * LMP_MULTIPLIER
                if legal_moves_count > lmp_threshold:
                    unmake_move(state, move)
                    continue
            
            if (move & CAPTURE_FLAG) and depth <= 6 and not gives_check:
                if not see_fast(state, move, threshold=0):
                    unmake_move(state, move)
                    continue
            
            needs_full = True

            if depth >= 3 and legal_moves_count >= LMR_MOVE_THRESHOLD and not is_interesting and not in_check and not gives_check:
                reduction = LMR_BASE_REDUCTION
                if legal_moves_count >= 10: reduction = 2
                if not is_pv: reduction += 1
                if gives_check and time_pressure_mode:
                    reduction = max(0, reduction - 1)
                
                reduced_depth = max(1, depth - 1 - reduction)
                val = -self._alpha_beta(state, reduced_depth, -(alpha+1), -alpha, ply + 1, move, allow_null=True, is_pv=False)
                if val <= alpha: needs_full = False
            
            if needs_full:
                if legal_moves_count == 1:
                    value = -self._alpha_beta(state, depth - 1, -beta, -alpha, ply + 1, move, allow_null=True, is_pv=is_pv)
                else:
                    value = -self._alpha_beta(state, depth - 1, -(alpha + 1), -alpha, ply + 1, move, allow_null=True, is_pv=False)
                    if alpha < value < beta:
                        value = -self._alpha_beta(state, depth - 1, -beta, -alpha, ply + 1, move, allow_null=True, is_pv=is_pv)
            else:
                value = val
            
            unmake_move(state, move)

            if value >= beta:
                self.tt.store(state.hash, depth, beta, FLAG_LOWERBOUND, move)
                self.ordering.store_killer(depth, move)
                self.ordering.store_history(move, depth)
                self.ordering.store_countermove(previous_move, move)
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
            
            if evaluation >= beta: return beta
            
            delta = PIECE_VALUES[QUEEN] + PIECE_VALUES[PAWN]
            if evaluation < alpha - delta:
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
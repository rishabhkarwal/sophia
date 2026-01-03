import time
from engine.core.constants import (
    WHITE, BLACK, INFINITY,
    MAX_DEPTH, TIME_CHECK_NODES,
    PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
    MASK_SOURCE, NULL, PIECE_VALUES
)
from engine.core.move import (
    CAPTURE_FLAG, PROMO_FLAG, EP_FLAG,
    move_to_uci, SHIFT_TARGET
)
from engine.moves.generator import generate_pseudo_legal_moves
from engine.board.move_exec import (
    make_move, unmake_move,
    make_null_move, unmake_null_move,
    is_repetition
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

class SearchEngine:
    def __init__(self, time_limit=2000, tt_size_mb=64):
        self.time_limit = time_limit
        self.tt = TranspositionTable(tt_size_mb)
        self.pawn_hash = PawnHashTable(32)
        self.syzygy = SyzygyHandler()
        self.ordering = MoveOrdering()
        self.nodes_searched = 0
        self.depth_reached = 0
        self.seldepth = 0 # selective depth tracking
        self.tbhits = 0 # tablebase hits
        self.start_time = 0.0
        self.root_colour = WHITE
        
        # dynamic aspiration windows
        self.aspiration_min = 50
        self.aspiration_max = 150
        self.aspiration_current = (self.aspiration_min + self.aspiration_max) // 3
        self.aspiration_stability_count = 0
        
        self.opponent_time_ms = 999999
        
        self.stopped = False
    
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
        
        self.stopped = False
        self.depth_reached = 0
        
        self.aspiration_current = (self.aspiration_min + self.aspiration_max) // 3
        self.aspiration_stability_count = 0

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
        
        while True:
            if best_move_so_far in moves:
                moves.remove(best_move_so_far)
                moves.insert(0, best_move_so_far)
            
            alpha = -INFINITY
            beta = INFINITY
            
            if current_depth > 1:
                alpha = current_score - self.aspiration_current
                beta = current_score + self.aspiration_current
                
                best_move, score = self._search_root(state, current_depth, moves, alpha, beta)
                
                if self.stopped: break 
                
                if score <= alpha or score >= beta:
                    send_info_string(f'aspiration failed: {self.aspiration_current}')
                    self.aspiration_current = min(self.aspiration_current * 2, self.aspiration_max)
                    self.aspiration_stability_count = 0
                    
                    alpha = current_score - self.aspiration_current
                    beta = current_score + self.aspiration_current
                    
                    best_move, score = self._search_root(state, current_depth, moves, alpha, beta)
                    
                    if self.stopped: break
                    
                    if score <= alpha or score >= beta:
                        send_info_string(f'aspiration failed again: {self.aspiration_current}')
                        alpha = -INFINITY
                        beta = INFINITY
                        
                        best_move, score = self._search_root(state, current_depth, moves, alpha, beta)
                else:
                    self.aspiration_stability_count += 1
                    if self.aspiration_stability_count >= 3:
                        self.aspiration_current = max(self.aspiration_min, int(self.aspiration_current * 0.75))
                        self.aspiration_stability_count = 0
                        send_info_string(f'aspiration tightened: {self.aspiration_current}')
            else:
                best_move, score = self._search_root(state, current_depth, moves, -INFINITY, INFINITY)

            if self.stopped: break

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
            
            elapsed = time.time() - self.start_time
            elapsed = elapsed * 1000
            if elapsed > self.time_limit * 0.9: break
                
            current_depth += 1
            if current_depth > MAX_DEPTH: break
                
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
                value = -self._alpha_beta(state, depth - 1, -beta, -alpha, ply + 1, move)
            else:
                value = -self._alpha_beta(state, depth - 1, -(alpha + 1), -alpha, ply + 1, move)
                if alpha < value < beta:
                    value = -self._alpha_beta(state, depth - 1, -beta, -alpha, ply + 1, move)
            
            if self.stopped:
                unmake_move(state, move)
                return best_move, -INFINITY
            
            unmake_move(state, move)
            
            if value > best_value:
                best_value = value
                best_move = move
                
            if value > alpha:
                alpha = value
                if alpha >= beta: return best_move, alpha

        if not self.stopped:
            self.tt.store(state.hash, depth, best_value, FLAG_EXACT, best_move)
            
        return best_move, best_value

    def _alpha_beta(self, state, depth, alpha, beta, ply, previous_move=None, allow_null=True):
        if self.stopped: return 0

        if ply > self.seldepth: self.seldepth = ply

        self.nodes_searched += 1

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

        if (self.nodes_searched & TIME_CHECK_NODES) == 0:
            if time.time() - self.start_time > self.time_limit / 1000.0: 
                self.stopped = True
                return 0
        
        is_threefold, is_fivefold = is_repetition(state)

        if is_threefold or is_fivefold:
            if alpha >= 100: return -50  # winning -> avoid draw
            elif alpha < -100: return 0   # losing -> draw is okay
            return -10  # equal -> slight penalty

        if state.halfmove_clock >= 100: return 0

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
        
        if not in_check and depth >= 4 and tt_entry is None: # IID
            reduced_depth = depth - 2
            self._alpha_beta(state, reduced_depth, alpha, beta, ply, previous_move, allow_null=True)
            tt_entry = self.tt.probe(state.hash)

        # reverse futility pruning
        if not in_check and depth <= 3 and allow_null:
            static_eval = evaluate(state, self.pawn_hash)
            rfp_margin = 120 * depth
            if static_eval - rfp_margin >= beta:
                return static_eval - rfp_margin

        # null move pruning
        if allow_null and depth >= 3 and not in_check:
            make_null_move(state)

            reduction = 2
            val = -self._alpha_beta(state, depth - 1 - reduction, -beta, -beta + 1, ply + 1, None, allow_null=False)
            unmake_null_move(state)
            
            if self.stopped: return 0
            if val >= beta: return beta

        # futility pruning
        do_futility = False
        if not in_check and depth <= 3 and allow_null:
            static_eval = evaluate(state, self.pawn_hash)
            futility_margin = 150 * depth
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
            
            if do_futility and not is_interesting:
                unmake_move(state, move)
                continue
            
            # late move pruning (LMP)
            # skip quiet moves after trying many moves at low depths
            if not in_check and not is_interesting and depth <= 4:
                lmp_threshold = 3 + depth * depth  # depth 1: 4 moves, depth 2: 7 moves, depth 3: 12 moves
                if legal_moves_count > lmp_threshold:
                    unmake_move(state, move)
                    continue
            
            # SEE pruning
            if (move & CAPTURE_FLAG) and depth <= 6 and not gives_check:
                if not see_fast(state, move, threshold=0):
                    unmake_move(state, move)
                    continue
            
            needs_full = True

            if depth >= 3 and legal_moves_count >= 3 and not is_interesting and not in_check:
                reduction = 1
                if legal_moves_count >= 10: reduction = 2
                if gives_check and time_pressure_mode:
                    reduction = max(0, reduction - 1)
                
                reduced_depth = max(1, depth - 1 - reduction)
                val = -self._alpha_beta(state, reduced_depth, -(alpha+1), -alpha, ply + 1, move, allow_null=True)
                if val <= alpha: needs_full = False
            
            if needs_full:
                if legal_moves_count == 1:
                    value = -self._alpha_beta(state, depth - 1, -beta, -alpha, ply + 1, move, allow_null=True)
                else:
                    value = -self._alpha_beta(state, depth - 1, -(alpha + 1), -alpha, ply + 1, move, allow_null=True)
                    if alpha < value < beta:
                        value = -self._alpha_beta(state, depth - 1, -beta, -alpha, ply + 1, move, allow_null=True)
            else:
                value = val

            if self.stopped:
                unmake_move(state, move)
                return 0
            
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
        
        if not self.stopped:
            self.tt.store(state.hash, depth, best_value, flag, best_move)
            
        return best_value

    def _quiescence(self, state, alpha, beta, ply):
        self.nodes_searched += 1
        if self.stopped: return 0

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
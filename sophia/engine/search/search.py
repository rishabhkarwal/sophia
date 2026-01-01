import time
from engine.core.constants import (
    WHITE, BLACK, MATE, INFINITY,
    MAX_DEPTH, TIME_CHECK_NODES,
    PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
    MASK_SOURCE, MASK_TARGET, NULL,
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
from engine.search.evaluation import evaluate
from engine.search.ordering import MoveOrdering
from engine.uci.utils import send_command, send_info_string
from engine.search.syzygy import SyzygyHandler

# pruning values for delta pruning
PIECE_VALUES = {
    PAWN >> 1: 100,
    KNIGHT >> 1: 320,
    BISHOP >> 1: 330,
    ROOK >> 1: 500,
    QUEEN >> 1: 900,
    KING >> 1: 20000
}

class SearchEngine:
    def __init__(self, time_limit=2000, tt_size_mb=64):
        self.time_limit = time_limit
        self.tt = TranspositionTable(tt_size_mb)
        self.syzygy = SyzygyHandler()
        self.ordering = MoveOrdering()
        self.nodes_searched = 0
        self.depth_reached = 0
        self.start_time = 0.0
        self.root_colour = WHITE
        self.first_aspiration_window = 35
        self.second_aspiration_window = 150
        
        self.stopped = False
    
    def _get_pv_line(self, state, max_depth=20):
        """Retrieves the principal variation line from the TT by walking the best moves found so far"""
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

    def _get_cp_score(self, score, max_mate_depth=MAX_DEPTH):
        if INFINITY - abs(score) < max_mate_depth:
            if score > 0:
                ply_to_mate = INFINITY - score
                mate_in = (ply_to_mate + 1) // 2
                score_str = f"mate {mate_in}"
            else:
                ply_to_mate = INFINITY + score
                mate_in = (ply_to_mate + 1) // 2
                score_str = f"mate -{mate_in}"
        else:
            score_str = f"cp {int(score)}"
        return score_str

    def get_best_move(self, state):
        # syzygy root probe
        syzygy_result = self.syzygy.get_best_move(state)
        if syzygy_result:
            syzygy_move, wdl, dtz = syzygy_result
            
            ply = 0
            if wdl > 0: score = INFINITY - ply - abs(dtz)
            elif wdl < 0: score = -INFINITY + ply + abs(dtz)
            else: score = 0

            score_str = self._get_cp_score(score)

            send_command(f"info depth {abs(dtz)} score {score_str} pv {syzygy_move} string syzygy hit")

            self.tt.store(state.hash, MAX_DEPTH, score, FLAG_EXACT, None)

            return syzygy_move

        self.nodes_searched = 0
        self.start_time = time.time()
        self.root_colour = state.is_white
        
        self.stopped = False
        self.depth_reached = 0

        # root must be legal

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
                # attempt 1: small window
                alpha = current_score - self.first_aspiration_window
                beta = current_score + self.first_aspiration_window
                
                best_move, score = self._search_root(state, current_depth, moves, alpha, beta)
                
                if self.stopped: break 
                
                # if score falls outside window, re-search
                if score <= alpha or score >= beta:
                    send_info_string(f'first aspiration failed: {self.first_aspiration_window}')
                    
                    # attempt 2: larger window
                    if score <= alpha: alpha = current_score - self.second_aspiration_window
                    if score >= beta:  beta = current_score + self.second_aspiration_window
                    
                    best_move, score = self._search_root(state, current_depth, moves, alpha, beta)
                    
                    if self.stopped: break
                    
                    if score <= alpha or score >= beta:
                        send_info_string(f'second aspiration failed: {self.second_aspiration_window}')
                        # attempt 3: full-window
                        if score <= alpha: alpha = -INFINITY
                        if score >= beta:  beta = INFINITY
                        
                        best_move, score = self._search_root(state, current_depth, moves, alpha, beta)
            else:
                best_move, score = self._search_root(state, current_depth, moves, -INFINITY, INFINITY)

            if self.stopped: break

            best_move_so_far = best_move
            current_score = score
            
            self.depth_reached = current_depth
            
            elapsed = time.time() - self.start_time
            nps = int(self.nodes_searched / elapsed) if elapsed > 0 else 0
            
            score_str = self._get_cp_score(score)

            hashfull = self.tt.get_hashfull()
            pv_string = self._get_pv_line(state, current_depth)

            send_command(f"info depth {current_depth} currmove {move_to_uci(best_move_so_far)} score {score_str} nodes {self.nodes_searched} nps {nps} time {int(elapsed * 1000)} hashfull {hashfull} pv {pv_string}")

            if abs(score) >= INFINITY - 1000:
                break
            
            elapsed = time.time() - self.start_time
            elapsed = elapsed * 1000
            # stop if > 90% of time used to prevent timing out in next depth
            if elapsed > self.time_limit * 0.9: break
                
            current_depth += 1
            if current_depth > MAX_DEPTH: break
                
        return best_move_so_far

    def _search_root(self, state, depth, moves, alpha, beta):
        tt_entry = self.tt.probe(state.hash)
        tt_move = tt_entry.best_move if tt_entry else None
        
        k1 = self.ordering.killer_moves[depth][0]
        k2 = self.ordering.killer_moves[depth][1]

        moves.sort(key=lambda m: self.ordering.get_move_score(m, tt_move, state, depth, k1, k2), reverse=True)

        best_move = moves[0]
        best_value = -INFINITY * 10
        ply = 0
        
        for i, move in enumerate(moves):
            make_move(state, move)

            # root moves are already legal, no check needed here
            if i == 0:
                value = -self._alpha_beta(state, depth - 1, -beta, -alpha, ply + 1)
            else:
                value = -self._alpha_beta(state, depth - 1, -(alpha + 1), -alpha, ply + 1)
                if alpha < value < beta:
                    value = -self._alpha_beta(state, depth - 1, -beta, -alpha, ply + 1)
            
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

    def _alpha_beta(self, state, depth, alpha, beta, ply, allow_null=True):
        if self.stopped: return 0

        self.nodes_searched += 1

        if (self.nodes_searched & TIME_CHECK_NODES) == 0:
            if time.time() - self.start_time > self.time_limit / 1000.0: 
                self.stopped = True
                return 0
        
        is_threefold, is_fivefold = is_repetition(state)
        if is_threefold:
            if alpha >= 100: return -50  # winning -> draw is bad
            elif alpha < -100: return 0  # losing -> draw is good
            return -20 # equal -> rather not draw
        if is_fivefold: return 0
        # 50-move rule (draw)
        if state.halfmove_clock >= 100: return 0

        # syzygy leaf probe
        wdl = self.syzygy.probe_wdl(state)
        if wdl is not None:
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

        if allow_null and depth >= 3 and not in_check:
            make_null_move(state)

            reduction = 2
            val = -self._alpha_beta(state, depth - 1 - reduction, -beta, -beta + 1, ply + 1, allow_null=False)
            unmake_null_move(state)
            
            if self.stopped: return 0 # return immediately if stopped inside recursion
            if val >= beta: return beta

        tt_move = tt_entry.best_move if tt_entry else None
        
        best_value = -INFINITY * 10
        best_move = None
        
        for i, move in enumerate(self._move_generator(state, tt_move, depth)):
            make_move(state, move)
            
            # optimisation: no legality check here
            # assume the move is legal; if it captures the king,
            # the recursive call will return bad score
            
            # LMR Logic
            is_interesting = (move & CAPTURE_FLAG) or (move & EP_FLAG) or (move & PROMO_FLAG)
            needs_full = True

            if depth >= 3 and i >= 3 and not is_interesting and not in_check:
                reduction = 1
                if i >= 10: reduction = 2
                reduced_depth = max(1, depth - 1 - reduction)
                val = -self._alpha_beta(state, reduced_depth, -(alpha+1), -alpha, ply + 1, allow_null=True)
                if val <= alpha: needs_full = False
            
            if needs_full:
                if i == 0:
                    value = -self._alpha_beta(state, depth - 1, -beta, -alpha, ply + 1, allow_null=True)
                else:
                    value = -self._alpha_beta(state, depth - 1, -(alpha + 1), -alpha, ply + 1, allow_null=True)
                    if alpha < value < beta:
                        value = -self._alpha_beta(state, depth - 1, -beta, -alpha, ply + 1, allow_null=True)
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
                return beta
            
            if value > best_value:
                best_value = value
                best_move = move
                
            if value > alpha: alpha = value

        # if best_value is still -INFINITY * 10 (no moves generated) 
        # OR extremely negative (all moves were illegal/king captured)
        if best_value <= -INFINITY + 2000:
            if in_check: return -INFINITY + ply # checkmate
            return 0 # stalemate

        flag = FLAG_EXACT
        if best_value <= alpha: flag = FLAG_UPPERBOUND
        
        if not self.stopped:
            self.tt.store(state.hash, depth, best_value, flag, best_move)
            
        return best_value

    def _quiescence(self, state, alpha, beta, ply):
        self.nodes_searched += 1
        if self.stopped: return 0

        tt_entry = self.tt.probe(state.hash)
        
        if tt_entry:
            if tt_entry.flag == FLAG_EXACT: return tt_entry.score
            elif tt_entry.flag == FLAG_LOWERBOUND: # position is at least equal to score
                if tt_entry.score >= beta: return tt_entry.score
            elif tt_entry.flag == FLAG_UPPERBOUND: # position is at most equal to score
                if tt_entry.score <= alpha: return tt_entry.score

        evaluation = evaluate(state, alpha, beta)
        
        if evaluation >= beta: return beta
        
        if evaluation > alpha:
            alpha = evaluation
            
        in_check = is_in_check(state, state.is_white)
        
        if in_check:
            moves = generate_pseudo_legal_moves(state, captures_only=False)
        else:
            moves = generate_pseudo_legal_moves(state, captures_only=True)
            
        scored_moves = []
        tt_move = None

        for m in moves:
            score = 0
            if (m & CAPTURE_FLAG):
                score = self.ordering.get_move_score(m, None, state, 0, None, None)
            scored_moves.append((score, m))
            
        scored_moves.sort(key=lambda x: x[0], reverse=True)
        
        for _, move in scored_moves:
            make_move(state, move)
            
            # optimisation: no legality check here
            
            score = -self._quiescence(state, -beta, -alpha, ply + 1)
            unmake_move(state, move)
            
            if score >= beta: return beta
            if score > alpha: alpha = score
        
        return alpha

    def _move_generator(self, state, tt_move, depth):
        """
        yields moves in stages
         tt move
         good captures (MVV-LVA)
         killer moves
         remaining moves (quiet)
        """
        if tt_move: yield tt_move

        captures = generate_pseudo_legal_moves(state, captures_only=True)
        
        captures.sort(key=lambda m: self.ordering.get_move_score(m, None, state, 0, None, None), reverse=True)
        
        for move in captures:
            if move == tt_move: continue
            yield move

        all_moves = generate_pseudo_legal_moves(state, captures_only=False) # maybe add a quiet only flag
 
        k1 = self.ordering.killer_moves[depth][0]
        k2 = self.ordering.killer_moves[depth][1]
        
        quiet_moves = []
        for move in all_moves:
            if move == tt_move: continue

            is_capture = (move & CAPTURE_FLAG) or (move & EP_FLAG) or (move & PROMO_FLAG)
            if is_capture: continue
            
            quiet_moves.append(move)

        quiet_moves.sort(key=lambda m: self.ordering.get_move_score(m, None, state, depth, k1, k2), reverse=True)

        for move in quiet_moves:
            yield move
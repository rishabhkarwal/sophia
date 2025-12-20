import time
from engine.core.constants import WHITE, BLACK
from engine.movegen.generator import get_legal_moves
from engine.board.move_exec import make_move, is_threefold_repetition
from engine.movegen.legality import is_in_check
from engine.search.transposition import TranspositionTable, FLAG_EXACT, FLAG_LOWERBOUND, FLAG_UPPERBOUND
from engine.search.evaluation import evaluate
from engine.search.ordering import MoveOrdering

class SearchEngine:
    def __init__(self, time_limit=1.0, tt_size_mb=64, debug=False):
        self.time_limit = time_limit
        self.tt = TranspositionTable(tt_size_mb)
        self.ordering = MoveOrdering()
        self.nodes_searched = 0
        self.sel_depth = 0  # Track max depth (selective depth)
        self.start_time = 0.0
        self.root_colour = WHITE
        self.delta_margin = 1000 
        self.debug = debug

    def get_best_move(self, state):
        """
        Iterative Deepening with Aspiration Windows.
        Returns the best move found within the time limit.
        """
        self.nodes_searched = 0
        self.sel_depth = 0
        self.start_time = time.time()
        self.root_colour = state.player
        
        moves = get_legal_moves(state)
        if not moves: return None
        
        # Initial rough sort
        moves.sort(key=lambda m: (m.is_capture, m.is_promotion), reverse=True)
        
        best_move_so_far = moves[0]
        current_depth = 1
        current_score = 0
        
        while True:
            try:
                if best_move_so_far in moves:
                    moves.remove(best_move_so_far)
                    moves.insert(0, best_move_so_far)
                
                alpha = -float('inf')
                beta = float('inf')
                window = 50
                
                # Aspiration Windows logic
                if current_depth > 1:
                    alpha = current_score - window
                    beta = current_score + window
                    
                    best_move, score = self._search_root(state, current_depth, moves, alpha, beta)
                    
                    if score <= alpha or score >= beta:
                        alpha = -float('inf')
                        beta = float('inf')
                        best_move, score = self._search_root(state, current_depth, moves, alpha, beta)
                else:
                    best_move, score = self._search_root(state, current_depth, moves, alpha, beta)

                best_move_so_far = best_move
                current_score = score
                
                elapsed = time.time() - self.start_time
                time_ms = int(elapsed * 1000)
                nps = int(self.nodes_searched / elapsed) if elapsed > 0 else 0
                
                if abs(score) > 90000:
                    if score > 0:
                        mate_in = (100000 - score + 1) // 2
                        score_str = f"mate {mate_in}"
                    else:
                        mate_in = (100000 + score + 1) // 2
                        score_str = f"mate -{mate_in}"
                else:
                    score_str = f"cp {score}"

                if self.debug: print(f"info depth {current_depth} seldepth {self.sel_depth} score {score_str} nodes {self.nodes_searched} nps {nps} time {time_ms}", flush=True)
                
                elapsed = time.time() - self.start_time
                if elapsed > self.time_limit / 2:
                    break
                    
                current_depth += 1
                if current_depth > 100: break
                
            except TimeoutError:
                break
                
        return best_move_so_far

    def _search_root(self, state, depth, moves, alpha, beta):
        tt_entry = self.tt.probe(state.hash)
        tt_move = tt_entry.best_move if tt_entry else None
        
        k1 = self.ordering.killer_moves[depth][0]
        k2 = self.ordering.killer_moves[depth][1]

        moves.sort(key=lambda m: self.ordering.get_move_score(m, tt_move, state, depth, k1, k2), reverse=True)

        best_move = moves[0]
        best_value = -float('inf')
        
        # Current Ply is 0 at root
        ply = 0
        
        for i, move in enumerate(moves):
            #if self.debug: print(f"info currmovenumber {i+1}", flush=True)

            next_state = make_move(state, move)
            
            if i == 0:
                value = -self._alpha_beta(next_state, depth - 1, -beta, -alpha, ply + 1)
            else:
                value = -self._alpha_beta(next_state, depth - 1, -(alpha + 1), -alpha, ply + 1)
                if alpha < value < beta:
                    value = -self._alpha_beta(next_state, depth - 1, -beta, -alpha, ply + 1)
            
            if value > best_value:
                best_value = value
                best_move = move
                
            if value > alpha:
                alpha = value
                if alpha >= beta:
                    return best_move, alpha
        
        self.tt.store(state.hash, depth, best_value, FLAG_EXACT, best_move)
        return best_move, best_value

    def _alpha_beta(self, state, depth, alpha, beta, ply, allow_null=True):
        self.nodes_searched += 1
        if (self.nodes_searched & 2047) == 0:
            if time.time() - self.start_time > self.time_limit:
                raise TimeoutError()
        
        # Update Selective Depth
        if ply > self.sel_depth:
            self.sel_depth = ply
        
        if is_threefold_repetition(state):
            return 0

        tt_entry = self.tt.probe(state.hash)
        if tt_entry and tt_entry.depth >= depth:
            if tt_entry.flag == FLAG_EXACT: return tt_entry.score
            elif tt_entry.flag == FLAG_LOWERBOUND: alpha = max(alpha, tt_entry.score)
            elif tt_entry.flag == FLAG_UPPERBOUND: beta = min(beta, tt_entry.score)
            if alpha >= beta: return tt_entry.score

        if depth <= 0:
            return self._quiescence(state, alpha, beta, ply)

        in_check = is_in_check(state, state.player)

        if allow_null and depth >= 3 and not in_check:
            try:
                null_state = type(state)(
                    state.bitboards, not state.player, state.castling, 
                    None, state.halfmove_clock + 1, state.fullmove_number, state.history
                )
                R = 2
                val = -self._alpha_beta(null_state, depth - 1 - R, -beta, -beta + 1, ply + 1, allow_null=False)
                if val >= beta: return beta
            except: pass

        moves = get_legal_moves(state)
        
        if not moves:
            if in_check: return -100000 + ply # Checkmate
            return 0 

        tt_move = tt_entry.best_move if tt_entry else None
        k1 = self.ordering.killer_moves[depth][0]
        k2 = self.ordering.killer_moves[depth][1]

        moves.sort(key=lambda m: self.ordering.get_move_score(m, tt_move, state, depth, k1, k2), reverse=True)
        
        best_value = -float('inf')
        best_move = None
        original_alpha = alpha
        
        for i, move in enumerate(moves):
            next_state = make_move(state, move)
            
            needs_full = True
            if depth >= 3 and i >= 3 and not move.is_capture and not move.is_promotion and not in_check:
                reduction = 1
                if i >= 10: reduction = 2
                reduced_depth = max(1, depth - 1 - reduction)
                val = -self._alpha_beta(next_state, reduced_depth, -(alpha+1), -alpha, ply + 1, allow_null=True)
                if val <= alpha: needs_full = False
            
            if needs_full:
                if i == 0:
                    value = -self._alpha_beta(next_state, depth - 1, -beta, -alpha, ply + 1, allow_null=True)
                else:
                    value = -self._alpha_beta(next_state, depth - 1, -(alpha + 1), -alpha, ply + 1, allow_null=True)
                    if alpha < value < beta:
                        value = -self._alpha_beta(next_state, depth - 1, -beta, -alpha, ply + 1, allow_null=True)
            else:
                value = val

            if value >= beta:
                self.tt.store(state.hash, depth, beta, FLAG_LOWERBOUND, move)
                self.ordering.store_killer(depth, move)
                self.ordering.store_history(move, depth)
                return beta
            
            if value > best_value:
                best_value = value
                best_move = move
                
            if value > alpha:
                alpha = value

        flag = FLAG_EXACT
        if best_value <= original_alpha: flag = FLAG_UPPERBOUND
        
        self.tt.store(state.hash, depth, best_value, flag, best_move)
        return best_value

    def _quiescence(self, state, alpha, beta, ply):
        self.nodes_searched += 1
        
        # Update Selective Depth in Quiescence
        if ply > self.sel_depth:
            self.sel_depth = ply
        
        in_check = is_in_check(state, state.player)
        
        if not in_check:
            stand_pat = evaluate(state)
            if stand_pat >= beta: return beta
            if stand_pat > alpha: alpha = stand_pat
            
            if stand_pat + self.delta_margin < alpha: 
                return alpha
            
            moves = get_legal_moves(state, captures_only=True)
        else:
            moves = get_legal_moves(state, captures_only=False)
            if not moves: return -100000 + ply

        moves.sort(key=lambda m: (m.is_capture, m.is_promotion), reverse=True)
        
        for move in moves:
            next_state = make_move(state, move)
            score = -self._quiescence(next_state, -beta, -alpha, ply + 1)
            
            if score >= beta: return beta
            if score > alpha: alpha = score
                
        return alpha
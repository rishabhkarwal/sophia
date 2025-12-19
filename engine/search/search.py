import time
from engine.core.constants import WHITE, BLACK
from engine.movegen.generator import get_legal_moves
from engine.board.move_exec import make_move, is_threefold_repetition
from engine.movegen.legality import is_in_check
from engine.search.transposition import TranspositionTable, FLAG_EXACT, FLAG_LOWERBOUND, FLAG_UPPERBOUND
from engine.search.evaluation import evaluate
from engine.search.ordering import MoveOrdering

class SearchEngine:
    def __init__(self, time_limit=1.0, tt_size_mb=64):
        self.time_limit = time_limit
        self.tt = TranspositionTable(tt_size_mb)
        self.ordering = MoveOrdering()
        self.nodes_searched = 0
        self.start_time = 0.0
        self.root_colour = WHITE
        # Delta Pruning Safety Margin (Queen + Pawn buffer)
        self.delta_margin = 1000 

    def get_best_move(self, state, debug=False):
        """
        Iterative Deepening with Aspiration Windows.
        Returns the best move found within the time limit.
        """
        self.nodes_searched = 0
        self.start_time = time.time()
        self.root_colour = state.player
        
        # 1. Generate and Sort Root Moves
        moves = get_legal_moves(state)
        if not moves: return None
        
        # Initial rough sort (Captures/Promotions first)
        moves.sort(key=lambda m: (m.is_capture, m.is_promotion), reverse=True)
        
        best_move_so_far = moves[0]
        current_depth = 1
        current_score = 0
        
        while True:
            try:
                # 2. Move Ordering Optimisation
                # If we found a best move last iteration, search it first now
                if best_move_so_far in moves:
                    moves.remove(best_move_so_far)
                    moves.insert(0, best_move_so_far)
                
                # 3. Aspiration Windows
                # Instead of searching (-inf, +inf), we search a small window around previous score.
                alpha = -float('inf')
                beta = float('inf')
                window = 50
                
                if current_depth > 1:
                    alpha = current_score - window
                    beta = current_score + window
                    
                    best_move, score = self._search_root(state, current_depth, moves, alpha, beta)
                    
                    # If score falls outside window, we must re-search with full bounds
                    if score <= alpha or score >= beta:
                        if debug: print(f"Aspiration fail @ Depth {current_depth} (Score: {score}) ∴ Re-searching...")
                        alpha = -float('inf')
                        beta = float('inf')
                        best_move, score = self._search_root(state, current_depth, moves, alpha, beta)
                else:
                    # First depth always uses full window
                    best_move, score = self._search_root(state, current_depth, moves, alpha, beta)

                best_move_so_far = best_move
                current_score = score
                
                if debug: 
                    elapsed = time.time() - self.start_time
                    nps = int(self.nodes_searched / elapsed) if elapsed > 0 else 0
                    print(f"Depth {current_depth} | Move: {best_move_so_far} | Score: {score:,} | Nodes: {self.nodes_searched:,} | NPS: {nps:,} | Time: {elapsed:.4f}")
                
                # 4. Time Management
                elapsed = time.time() - self.start_time
                if elapsed > self.time_limit / 2:
                    break
                    
                current_depth += 1
                if current_depth > 100: break
                
            except TimeoutError:
                # If we run out of time mid-search, return the best move from the previous completed depth
                break
                
        return best_move_so_far

    def _search_root(self, state, depth, moves, alpha, beta):
        """
        Root search handles the list of candidate moves directly.
        It uses PVS logic (full window for first move, zero window for others).
        """
        tt_entry = self.tt.probe(state.hash)
        tt_move = tt_entry.best_move if tt_entry else None
        
        k1 = self.ordering.killer_moves[depth][0]
        k2 = self.ordering.killer_moves[depth][1]

        # Sort moves using advanced ordering (TT, MVV-LVA, Killers, History)
        moves.sort(key=lambda m: self.ordering.get_move_score(m, tt_move, state, depth, k1, k2), reverse=True)

        best_move = moves[0]
        best_value = -float('inf')
        
        for i, move in enumerate(moves):
            # Check time strictly (but ensure we don't timeout inside Depth 1)
            # This fixes the "Missed Mate" bug by ensuring at least one ply finishes.
            # actually, removed check here to rely on alpha_beta's check or outer loop
            
            next_state = make_move(state, move)
            
            # Principal Variation Search (PVS)
            if i == 0:
                # First move: Full Window Search
                value = -self._alpha_beta(next_state, depth - 1, -beta, -alpha)
            else:
                # Late moves: Zero Window Search (Null Window)
                # Prove that this move is worse than alpha
                value = -self._alpha_beta(next_state, depth - 1, -(alpha + 1), -alpha)
                
                # If the move turned out to be better than alpha, we were wrong.
                # Re-search with full window.
                if alpha < value < beta:
                    value = -self._alpha_beta(next_state, depth - 1, -beta, -alpha)
            
            if value > best_value:
                best_value = value
                best_move = move
                
            if value > alpha:
                alpha = value
                # Aspiration High Fail at Root: Return immediately to widen window
                if alpha >= beta:
                    return best_move, alpha 
        
        self.tt.store(state.hash, depth, best_value, FLAG_EXACT, best_move)
        return best_move, best_value

    def _alpha_beta(self, state, depth, alpha, beta, allow_null=True):
        """
        The core recursive search function.
        Features: Transposition Table, Null Move Pruning, Check Extensions, LMR, PVS.
        """
        self.nodes_searched += 1
        
        # Periodic Time Check (every 2048 nodes)
        if (self.nodes_searched & 2047) == 0:
            if time.time() - self.start_time > self.time_limit:
                raise TimeoutError()
        
        if is_threefold_repetition(state):
            return 0

        # 1. Transposition Table Lookup
        tt_entry = self.tt.probe(state.hash)
        if tt_entry and tt_entry.depth >= depth:
            if tt_entry.flag == FLAG_EXACT:
                return tt_entry.score
            elif tt_entry.flag == FLAG_LOWERBOUND:
                alpha = max(alpha, tt_entry.score)
            elif tt_entry.flag == FLAG_UPPERBOUND:
                beta = min(beta, tt_entry.score)
            
            if alpha >= beta:
                return tt_entry.score

        # 2. Quiescence Search at Leaf Nodes
        if depth <= 0:
            return self._quiescence(state, alpha, beta)

        in_check = is_in_check(state, state.player)

        # 3. Null Move Pruning (NMP)
        # If giving the opponent a free move still fails high, our position is winning.
        # depth >= 3 condition prevents pruning in shallow searches where zugzwang is risky.
        if allow_null and depth >= 3 and not in_check:
            # Simple heuristic: Only null move if we have major pieces (avoids zugzwang)
            # For brevity, assuming we do (a robust engine checks bitboards here)
            try:
                # Create state with side to move swapped, clock incremented
                null_state = type(state)(
                    state.bitboards, not state.player, state.castling, 
                    None, state.halfmove_clock + 1, state.fullmove_number, state.history
                )
                
                # Reduction factor R
                R = 2
                if depth > 6: R = 3
                
                # Search with reduced depth
                val = -self._alpha_beta(null_state, depth - 1 - R, -beta, -beta + 1, allow_null=False)
                
                if val >= beta:
                    return beta
            except: 
                pass

        # 4. Move Generation & Ordering
        moves = get_legal_moves(state)
        
        if not moves:
            if in_check: return -100000 + depth # Checkmate (prefer faster mates)
            return 0 # Stalemate

        tt_move = tt_entry.best_move if tt_entry else None
        k1 = self.ordering.killer_moves[depth][0]
        k2 = self.ordering.killer_moves[depth][1]

        moves.sort(key=lambda m: self.ordering.get_move_score(m, tt_move, state, depth, k1, k2), reverse=True)
        
        best_value = -float('inf')
        best_move = None
        original_alpha = alpha
        
        for i, move in enumerate(moves):
            next_state = make_move(state, move)
            
            # 5. Late Move Reductions (LMR)
            # If a move is sorted late, is quiet, and we aren't in check, search it shallower.
            needs_full_search = True
            
            if depth >= 3 and i >= 3 and not move.is_capture and not move.is_promotion and not in_check:
                reduction = 1
                if i >= 10: reduction = 2
                if depth >= 6 and i >= 10: reduction = 3
                
                reduced_depth = max(1, depth - 1 - reduction)
                
                # Zero window search at reduced depth
                val = -self._alpha_beta(next_state, reduced_depth, -(alpha + 1), -alpha, allow_null=True)
                
                # If the reduced search failed low, we trust it.
                if val <= alpha:
                    needs_full_search = False
                else:
                    # If it failed high, the move is suspicious/good, re-search fully.
                    needs_full_search = True

            if needs_full_search:
                if i == 0:
                    value = -self._alpha_beta(next_state, depth - 1, -beta, -alpha, allow_null=True)
                else:
                    # PVS Zero Window
                    value = -self._alpha_beta(next_state, depth - 1, -(alpha + 1), -alpha, allow_null=True)
                    if alpha < value < beta:
                        value = -self._alpha_beta(next_state, depth - 1, -beta, -alpha, allow_null=True)
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

    def _quiescence(self, state, alpha, beta):
        """
        Quiescence Search: Searches only captures to solve the horizon effect.
        Includes Delta Pruning.
        """
        self.nodes_searched += 1
        
        in_check = is_in_check(state, state.player)
        
        # 1. Stand Pat (Evaluate current position)
        if not in_check:
            stand_pat = evaluate(state)
            if stand_pat >= beta: return beta
            if stand_pat > alpha: alpha = stand_pat
            
            # 2. Delta Pruning
            # If we are down by a lot (margin), and capturing won't help, prune.
            # Exception: If we are in check, we must search moves.
            if stand_pat + self.delta_margin < alpha:
                return alpha
            
            # Only search captures if not in check
            moves = get_legal_moves(state, captures_only=True)
        else:
            # If in check, we MUST search all moves to find an escape
            moves = get_legal_moves(state, captures_only=False)
            if not moves: return -100000 # Checkmate

        moves.sort(key=lambda m: (m.is_capture, m.is_promotion), reverse=True)
        
        for move in moves:
            next_state = make_move(state, move)
            score = -self._quiescence(next_state, -beta, -alpha)
            
            if score >= beta: return beta
            if score > alpha: alpha = score
                
        return alpha
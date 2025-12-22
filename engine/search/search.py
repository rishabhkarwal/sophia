import time
from engine.core.constants import WHITE, BLACK, INFINITY, MASK_FLAG
from engine.moves.generator import generate_pseudo_legal_moves
from engine.board.move_exec import make_move, unmake_move, make_null_move, unmake_null_move, is_threefold_repetition
from engine.moves.legality import is_in_check
from engine.search.transposition import TranspositionTable, FLAG_EXACT, FLAG_LOWERBOUND, FLAG_UPPERBOUND
from engine.search.evaluation import evaluate
from engine.search.ordering import MoveOrdering
from engine.uci.utils import send_command
from engine.core.move import CAPTURE, PROMOTION_N, EP_CAPTURE, PROMO_CAP_N, move_to_uci

class SearchEngine:
    def __init__(self, time_limit=2000, tt_size_mb=32, debug=False):
        self.time_limit = time_limit
        self.tt = TranspositionTable(tt_size_mb)
        self.ordering = MoveOrdering()
        self.nodes_searched = 0
        self.start_time = 0.0
        self.root_colour = WHITE
        self.aspiration_window = 50
        self.debug = debug

    def get_best_move(self, state):
        self.nodes_searched = 0
        self.start_time = time.time()
        self.root_colour = state.player
        
        moves = generate_pseudo_legal_moves(state)
        legal_moves = []
        for move in moves:
            undo = make_move(state, move)
            if not is_in_check(state, not state.player):
                legal_moves.append(move)
            unmake_move(state, move, undo)
            
        if not legal_moves: return None
        moves = legal_moves
        
        # sort logic: high bits for promotions (>=8) or captures (4, 5, >=12)
        moves.sort(key=lambda m: (m & MASK_FLAG), reverse=True)
        
        best_move_so_far = moves[0]
        current_depth = 1
        current_score = 0
        
        while True:
            try:
                if best_move_so_far in moves:
                    moves.remove(best_move_so_far)
                    moves.insert(0, best_move_so_far)
                
                alpha = -INFINITY * 10
                beta = INFINITY * 10
                window = self.aspiration_window
                
                if current_depth > 1:
                    alpha = current_score - window
                    beta = current_score + window
                    
                    best_move, score = self._search_root(state, current_depth, moves, alpha, beta)
                    
                    if score <= alpha or score >= beta:
                        alpha = -INFINITY * 10
                        beta = INFINITY * 10
                        best_move, score = self._search_root(state, current_depth, moves, alpha, beta)
                else:
                    best_move, score = self._search_root(state, current_depth, moves, alpha, beta)

                best_move_so_far = best_move
                current_score = score
                
                elapsed = time.time() - self.start_time
                nps = int(self.nodes_searched / elapsed) if elapsed > 0 else 0
                
                if INFINITY - abs(score) < 1000:
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

                hashfull = self.tt.get_hashfull()
                
                if self.debug: 
                    send_command(f"info depth {current_depth} currmove {move_to_uci(best_move_so_far)} score {score_str} nodes {self.nodes_searched} nps {nps} time {int(elapsed * 1000)} hashfull {hashfull}")
                
                elapsed = time.time() - self.start_time
                elapsed = elapsed * 1000
                # stop if > 90% of time used to prevent timing out in next depth
                if elapsed > self.time_limit * 0.9: break
                    
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
        best_value = -INFINITY * 10
        ply = 0
        
        for i, move in enumerate(moves):
            undo_info = make_move(state, move)
            # root moves are already legal, no check needed here
            if i == 0:
                value = -self._alpha_beta(state, depth - 1, -beta, -alpha, ply + 1)
            else:
                value = -self._alpha_beta(state, depth - 1, -(alpha + 1), -alpha, ply + 1)
                if alpha < value < beta:
                    value = -self._alpha_beta(state, depth - 1, -beta, -alpha, ply + 1)
            
            unmake_move(state, move, undo_info)
            
            if value > best_value:
                best_value = value
                best_move = move
                
            if value > alpha:
                alpha = value
                if alpha >= beta: return best_move, alpha
        
        self.tt.store(state.hash, depth, best_value, FLAG_EXACT, best_move)
        return best_move, best_value

    def _alpha_beta(self, state, depth, alpha, beta, ply, allow_null=True):
        self.nodes_searched += 1
        if (self.nodes_searched & 2047) == 0:
            if time.time() - self.start_time > self.time_limit / 1000.0: raise TimeoutError() # forgot to convert to ms
        
        if is_threefold_repetition(state): return 0
        # 50-move rule (draw)
        if state.halfmove_clock >= 100: return 0 # 100 halfmoves = 50 full moves

        tt_entry = self.tt.probe(state.hash)
        if tt_entry and tt_entry.depth >= depth:
            if tt_entry.flag == FLAG_EXACT: return tt_entry.score
            elif tt_entry.flag == FLAG_LOWERBOUND: alpha = max(alpha, tt_entry.score)
            elif tt_entry.flag == FLAG_UPPERBOUND: beta = min(beta, tt_entry.score)
            if alpha >= beta: return tt_entry.score

        if depth <= 0: return self._quiescence(state, alpha, beta, ply)

        in_check = is_in_check(state, state.player)

        if allow_null and depth >= 3 and not in_check:
            undo_info = make_null_move(state)
            try:
                reduction = 2 
                val = -self._alpha_beta(state, depth - 1 - reduction, -beta, -beta + 1, ply + 1, allow_null=False)
                if val >= beta: return beta
            except TimeoutError: raise
            except Exception: pass 
            finally: unmake_null_move(state, undo_info)

        moves = generate_pseudo_legal_moves(state)
        
        tt_move = tt_entry.best_move if tt_entry else None
        k1 = self.ordering.killer_moves[depth][0]
        k2 = self.ordering.killer_moves[depth][1]

        moves.sort(key=lambda m: self.ordering.get_move_score(m, tt_move, state, depth, k1, k2), reverse=True)
        
        best_value = -INFINITY * 10
        best_move = None
        original_alpha = alpha
        legal_moves_count = 0
        
        for i, move in enumerate(moves):
            undo_info = make_move(state, move)
            
            # check legality AFTER making the move
            if is_in_check(state, not state.player):
                unmake_move(state, move, undo_info)
                continue
            
            legal_moves_count += 1
            
            # LMR logic
            flag = (move & MASK_FLAG) >> 12
            is_interesting = (flag == CAPTURE or flag == EP_CAPTURE or flag >= PROMOTION_N)
            
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

            unmake_move(state, move, undo_info)

            if value >= beta:
                self.tt.store(state.hash, depth, beta, FLAG_LOWERBOUND, move)
                self.ordering.store_killer(depth, move)
                self.ordering.store_history(move, depth)
                return beta
            
            if value > best_value:
                best_value = value
                best_move = move
                
            if value > alpha: alpha = value

        if legal_moves_count == 0:
            if in_check: return -INFINITY + ply # checkmate
            return 0 # stalemate

        flag = FLAG_EXACT
        if best_value <= original_alpha: flag = FLAG_UPPERBOUND
        
        self.tt.store(state.hash, depth, best_value, flag, best_move)
        return best_value

    def _quiescence(self, state, alpha, beta, ply):
        self.nodes_searched += 1
        
        in_check = is_in_check(state, state.player)
        
        if not in_check:
            evaluation = evaluate(state)
            if evaluation >= beta: return beta
            if evaluation > alpha: alpha = evaluation
            moves = generate_pseudo_legal_moves(state, captures_only=True)
        else:
            moves = generate_pseudo_legal_moves(state, captures_only=False)
            
        moves.sort(key=lambda m: self.ordering.get_move_score(m, None, state, 0, None, None), reverse=True)
        
        legal_moves_found = False
        
        for move in moves:
            undo_info = make_move(state, move)
            
            # delayed legality check
            if is_in_check(state, not state.player):
                unmake_move(state, move, undo_info)
                continue
            
            legal_moves_found = True
            
            score = -self._quiescence(state, -beta, -alpha, ply + 1)
            unmake_move(state, move, undo_info)
            
            if score >= beta: return beta
            if score > alpha: alpha = score
        
        # if we were in check and found no legal moves => checkmate
        if in_check and not legal_moves_found:
             return -INFINITY + ply

        return alpha
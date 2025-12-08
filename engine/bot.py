from .move_exec import get_legal_moves, make_move, is_in_check
from .precomputed import init_tables
from .constants import ALL_PIECES, WHITE, BLACK
from .utils import BitBoard

import random
import time

from .transposition import TranspositionTable, FLAG_EXACT, FLAG_LOWERBOUND, FLAG_UPPERBOUND

init_tables() #initialises lookup tables

class Bot:
    def __init__(self, colour):
        self.colour = colour

    def __repr__(self):
        return self.__class__.__name__

    def get_best_move(state):
        raise NotImplementedError("")

class RandomBot(Bot):
    def get_best_move(self, state):
        """Picks a random legal move"""
        legal_moves = get_legal_moves(state)
        return random.choice(legal_moves)

class MaterialBot(Bot):
    VALUES = {
        'P': 100, 'N': 320, 'B': 330, 'R': 500, 'Q': 900, 'K': 20000,
    }

    def evaluate(self, state):
        score = 0
        for piece in ALL_PIECES:
            bb = state.bitboards.get(piece, 0)
            count = bb.bit_count()

            value = self.VALUES.get(piece.upper())
            if piece.isupper(): # white piece
                score += count * value
            else: # black piece
                score -= count * value
        return score if self.colour == WHITE else -score # perspective 

    def get_best_move(self, state):
        """Picks a legal move; yielding the one with the best material score at depth 1"""
        legal_moves = get_legal_moves(state)

        best_move = None
        best_eval = -float('inf')
        
        random.shuffle(legal_moves)
        
        for move in legal_moves:
            next_state = make_move(state, move)
            
            score = self.evaluate(next_state)
            
            if score > best_eval:
                best_eval = score
                best_move = move
        
        return best_move

class PositionalBot(MaterialBot): # as best move return is the same
    # Pawn: encourage advancing
    PSQT_PAWN = [
        0,  0,  0,  0,  0,  0,  0,  0,
        50, 50, 50, 50, 50, 50, 50, 50,
        10, 10, 20, 30, 30, 20, 10, 10,
        5,  5, 10, 25, 25, 10,  5,  5,
        0,  0,  0, 20, 20,  0,  0,  0,
        5, -5,-10,  0,  0,-10, -5,  5,
        5, 10, 10,-20,-20, 10, 10,  5,
        0,  0,  0,  0,  0,  0,  0,  0
    ]

    # Knight: strong centre, weak corners
    PSQT_KNIGHT = [
        -50,-40,-30,-30,-30,-30,-40,-50,
        -40,-20,  0,  0,  0,  0,-20,-40,
        -30,  0, 10, 15, 15, 10,  0,-30,
        -30,  5, 15, 20, 20, 15,  5,-30,
        -30,  0, 15, 20, 20, 15,  0,-30,
        -30,  5, 10, 15, 15, 10,  5,-30,
        -40,-20,  0,  5,  5,  0,-20,-40,
        -50,-40,-30,-30,-30,-30,-40,-50
    ]

    # Bishop: good on long diagonals, avoid corners
    PSQT_BISHOP = [
        -20,-10,-10,-10,-10,-10,-10,-20,
        -10,  0,  0,  0,  0,  0,  0,-10,
        -10,  0,  5, 10, 10,  5,  0,-10,
        -10,  5,  5, 10, 10,  5,  5,-10,
        -10,  0, 10, 10, 10, 10,  0,-10,
        -10, 10, 10, 10, 10, 10, 10,-10,
        -10,  5,  0,  0,  0,  0,  5,-10,
        -20,-10,-10,-10,-10,-10,-10,-20
    ]

    # Rook: 7th rank is good, centre files okay
    PSQT_ROOK = [
        0,  0,  0,  0,  0,  0,  0,  0,
        5, 10, 10, 10, 10, 10, 10,  5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        0,  0,  0,  5,  5,  0,  0,  0
    ]

    # Queen: generally good everywhere, slightly better in centre
    PSQT_QUEEN = [
        -20,-10,-10, -5, -5,-10,-10,-20,
        -10,  0,  0,  0,  0,  0,  0,-10,
        -10,  0,  5,  5,  5,  5,  0,-10,
        -5,  0,  5,  5,  5,  5,  0, -5,
        0,  0,  5,  5,  5,  5,  0, -5,
        -10,  5,  5,  5,  5,  5,  0,-10,
        -10,  0,  5,  0,  0,  0,  0,-10,
        -20,-10,-10, -5, -5,-10,-10,-20
    ]

    # King: encourage castling, stay in corners / behind pawns (middlegame)
    PSQT_KING = [
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -20,-30,-30,-40,-40,-30,-30,-20,
        -10,-20,-20,-20,-20,-20,-20,-10,
        20, 20,  0,  0,  0,  0, 20, 20,
        20, 30, 10,  0,  0, 10, 30, 20
    ]

    TABLES = {
        'P': PSQT_PAWN, 'N': PSQT_KNIGHT, 'B': PSQT_BISHOP, 
        'R': PSQT_ROOK, 'Q': PSQT_QUEEN, 'K': PSQT_KING
    }

    def evaluate(self, state):
        score = 0
        
        for piece in ALL_PIECES:
            bb = state.bitboards.get(piece, 0)
            if not bb: continue
            
            is_white = piece.isupper()
            piece_type = piece.upper()
            
            # material
            material = self.VALUES[piece.upper()]
            # PSQT
            table = self.TABLES[piece_type]
            
            for sq in BitBoard.bit_scan(bb): # bit scan needed as we need position
                if is_white:
                    table_idx = (7 - (sq // 8)) * 8 + (sq % 8) 
                    
                    pos_score = table[table_idx]
                    score += material + pos_score
                else:
                    table_idx = (sq // 8) * 8 + (sq % 8) # perspective ...
                    
                    pos_score = table[table_idx]
                    score -= (material + pos_score)

        return score if self.colour == WHITE else -score

class SearchTreeBot(PositionalBot): # will evaluate material and position
    def __init__(self, colour, depth=3):
        super().__init__(colour)
        self.depth = depth
        self.nodes_searched = 0

    def get_best_move(self, state):
        self.nodes_searched = 0
        
        moves = get_legal_moves(state)
        random.shuffle(moves) 

        best_move = moves[0]
        best_value = -float('inf')

        for move in moves:
            next_state = make_move(state, move)
            # start the recursive search
            # -search because the opponent tries to minimise OUR score | max(a, b) = -min(-a, -b)
            value = -self.negamax(next_state, self.depth - 1)
            
            if value > best_value:
                best_value = value
                best_move = move
                
        return best_move

    def negamax(self, state, depth):
        self.nodes_searched += 1

        if depth == 0:
            score = self.evaluate(state)
            if state.player != self.colour: # fix !
                return -score
            return score
            
        moves = get_legal_moves(state)

        if not moves:
            if is_in_check(state, state.player):
                return -float('inf') # checkmate
            else:
                return 0 #stalemate

        best_value = -float('inf')
        
        for move in moves:
            next_state = make_move(state, move)
            value = -self.negamax(next_state, depth - 1)
            best_value = max(best_value, value)
            
        return best_value

class AlphaBetaBot(PositionalBot):
    def __init__(self, colour, depth=4):
        super().__init__(colour)
        self.depth = depth
        self.nodes_searched = 0

    def get_best_move(self, state):
        self.nodes_searched = 0
        moves = get_legal_moves(state)
        if not moves: return None
        
        moves.sort(key=lambda m: (m.is_capture, m.is_promotion), reverse=True)
        
        best_move = moves[0]
        best_value = -float('inf')
        alpha = -float('inf')
        beta = float('inf')
        
        for move in moves:
            next_state = make_move(state, move)
            
            # -negamax with alpha-beta: -beta as alpha, -alpha as beta
            value = -self.alpha_beta(next_state, self.depth - 1, -beta, -alpha)
            
            if value > best_value:
                best_value = value
                best_move = move
            
            if value > alpha:
                alpha = value

        return best_move

    def alpha_beta(self, state, depth, alpha, beta):
        self.nodes_searched += 1
        if depth == 0:
            score = self.evaluate(state)
            if state.player != self.colour:
                return -score
            return score
        
        moves = get_legal_moves(state)
        
        if not moves:
            if is_in_check(state, state.player):
                return -100000 + depth # prefer faster mates (higher score)
            return 0 # stalemate

        # sort moves to improve pruning efficiency
        moves.sort(key=lambda m: (m.is_capture, m.is_promotion), reverse=True)
        
        best_value = -float('inf')
        
        for move in moves:
            next_state = make_move(state, move)
            value = -self.alpha_beta(next_state, depth - 1, -beta, -alpha)
            
            if value >= beta:
                # beta cutoff: opponent has a better move elsewhere, so they won't allow this
                return beta
            
            if value > best_value:
                best_value = value
                
            if value > alpha:
                alpha = value
                
        return best_value

class QuiescenceBot(AlphaBetaBot):
    def alpha_beta(self, state, depth, alpha, beta):   
        self.nodes_searched += 1 
        if depth == 0:
            return self.quiescence(state, alpha, beta)
        
        moves = get_legal_moves(state)
        
        if not moves:
            if is_in_check(state, state.player):
                return -100000 + depth
            return 0

        moves.sort(key=lambda m: (m.is_capture, m.is_promotion), reverse=True)
        
        for move in moves:
            next_state = make_move(state, move)
            value = -self.alpha_beta(next_state, depth - 1, -beta, -alpha)
            
            if value >= beta:
                return beta
            if value > alpha:
                alpha = value
                
        return alpha

    def quiescence(self, state, alpha, beta):
        self.nodes_searched += 1

        base_eval = self.evaluate(state)
        if state.player != self.colour:
            base_eval = -base_eval

        if base_eval >= beta:
            return beta
        
        if base_eval > alpha:
            alpha = base_eval
            
        capture_moves = get_legal_moves(state, captures_only=True)
    
        for move in capture_moves:
            next_state = make_move(state, move)
            score = -self.quiescence(next_state, -beta, -alpha)
            
            if score >= beta:
                return beta
            if score > alpha:
                alpha = score
                
        return alpha

class IterativeDeepeningBot(QuiescenceBot):
    def __init__(self, colour, time_limit=2.0):
        super().__init__(colour)
        self.time_limit = time_limit
        self.start_time = 0.0

    def get_best_move(self, state, debug=False):
        self.nodes_searched = 0
        self.start_time = time.time()
        
        moves = get_legal_moves(state)
        if not moves: return None
        
        #initial move ordering
        moves.sort(key=lambda m: (m.is_capture, m.is_promotion), reverse=True)
        
        best_move_so_far = moves[0]
        current_depth = 1
        
        while True:
            try:
                # optimisation: if we have a best move from the previous depth, search it first
                if best_move_so_far in moves:
                    moves.remove(best_move_so_far)
                    moves.insert(0, best_move_so_far)
                
                # search for this depth
                best_move, score = self.search_root(state, current_depth, moves)
                best_move_so_far = best_move
                
                if debug: print(f"Info: Depth {current_depth} | Move: {best_move_so_far} | Score: {score} | Nodes: {self.nodes_searched} | Time: {time.time() - self.start_time:.3f}s") # debug print
                
                # check if we have time for next depth
                elapsed = time.time() - self.start_time
                if elapsed > self.time_limit / 2:
                    break
                    
                current_depth += 1

                if current_depth > 100: break
                
            except TimeoutError:
                if debug: print(f"Info: Time limit reached at Depth {current_depth}")
                break
                
        return best_move_so_far

    def search_root(self, state, depth, sorted_moves):
        best_move = sorted_moves[0]
        best_value = -float('inf')
        alpha = -float('inf')
        beta = float('inf')
        
        for move in sorted_moves:
            if time.time() - self.start_time > self.time_limit:
                raise TimeoutError()
                
            next_state = make_move(state, move)
            value = -self.alpha_beta_timed(next_state, depth - 1, -beta, -alpha)
            
            if value > best_value:
                best_value = value
                best_move = move
            
            if value > alpha:
                alpha = value
                
        return best_move, best_value

    def alpha_beta_timed(self, state, depth, alpha, beta):
        """Alpha-beta with periodic time checks"""
        self.nodes_searched += 1
        
        # check time every 2048 nodes
        if self.nodes_searched & 2047 == 0:
            if time.time() - self.start_time > self.time_limit:
                raise TimeoutError()

        if depth == 0:
            return self.quiescence(state, alpha, beta)
        
        moves = get_legal_moves(state)
        
        if not moves:
            if is_in_check(state, state.player):
                return -100000 + depth
            return 0

        moves.sort(key=lambda m: (m.is_capture, m.is_promotion), reverse=True)
        
        for move in moves:
            next_state = make_move(state, move)
            value = -self.alpha_beta_timed(next_state, depth - 1, -beta, -alpha)
            
            if value >= beta:
                return beta
            if value > alpha:
                alpha = value
                
        return alpha

class TranspositionBot(PositionalBot):
    def __init__(self, colour, time_limit=2.0, tt_size_mb=64):
        super().__init__(colour)
        self.time_limit = time_limit
        self.tt = TranspositionTable(tt_size_mb)
        self.start_time = 0.0
        self.nodes_searched = 0

    def get_best_move(self, state, debug=False):
        self.nodes_searched = 0
        self.start_time = time.time()
        #self.tt.clear() # clear TT between moves or keep it (better performance)
        
        moves = get_legal_moves(state)
        if not moves: return None

        moves.sort(key=lambda m: (m.is_capture, m.is_promotion), reverse=True)
        
        best_move_so_far = moves[0]
        current_depth = 1
        
        while True:
            try:
                best_move, score = self.search_root(state, current_depth, moves)
                best_move_so_far = best_move
                
                if debug: print(f"Info: Depth {current_depth} | Move: {best_move} | Score: {score} | Nodes: {self.nodes_searched} | Time: {time.time() - self.start_time:.3f}s") # debug print

                elapsed = time.time() - self.start_time
                if elapsed > self.time_limit / 2:
                    break
                    
                current_depth += 1
                if current_depth > 100: break
                
            except TimeoutError:
                if debug: print(f"Info: Time limit reached at Depth {current_depth}")
                break

        return best_move_so_far

    def search_root(self, state, depth, moves):
        """Root search is special because we need to return the move, not just score"""
        best_move = moves[0]
        best_value = -float('inf')
        alpha = -float('inf')
        beta = float('inf')
        
        # retrieve TT entry for the root to improve sorting
        tt_entry = self.tt.probe(state.hash)
        tt_move = tt_entry.best_move if tt_entry else None
        
        # sort: TT move first, then captures
        if tt_move and tt_move in moves:
            moves.remove(tt_move)
            moves.insert(0, tt_move)
            
        for move in moves:
            if time.time() - self.start_time > self.time_limit:
                raise TimeoutError()
                
            next_state = make_move(state, move)
            value = -self.alpha_beta(next_state, depth - 1, -beta, -alpha)
            
            if value > best_value:
                best_value = value
                best_move = move
            
            if value > alpha:
                alpha = value
                
        # store root result
        self.tt.store(state.hash, depth, best_value, FLAG_EXACT, best_move)
        return best_move, best_value

    def alpha_beta(self, state, depth, alpha, beta):
        self.nodes_searched += 1
        if (self.nodes_searched & 2047) == 0:
            if time.time() - self.start_time > self.time_limit:
                raise TimeoutError()

        # transposition Table Lookup
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

        if depth == 0:
            return self.quiescence(state, alpha, beta)

        moves = get_legal_moves(state)
        
        if not moves:
            if is_in_check(state, state.player):
                return -100000 + depth # checkmate
            return 0 # stalemate

        # move prdering
        # if we had a TT hit, use that move first
        tt_move = tt_entry.best_move if tt_entry else None
        
        if tt_move:
            pass 

        # TT move prioritization
        moves.sort(key=lambda m: (
            m == tt_move,
            m.is_capture, 
            m.is_promotion
        ), reverse=True)

        best_value = -float('inf')
        best_move = None
        original_alpha = alpha
        
        for move in moves:
            next_state = make_move(state, move)
            value = -self.alpha_beta(next_state, depth - 1, -beta, -alpha)
            
            if value >= beta:
                # store LOWERBOUND (beta cutoff)
                self.tt.store(state.hash, depth, beta, FLAG_LOWERBOUND, move)
                return beta
            
            if value > best_value:
                best_value = value
                best_move = move
                
            if value > alpha:
                alpha = value

        # store result in TT
        flag = FLAG_EXACT
        if best_value <= original_alpha:
            flag = FLAG_UPPERBOUND
        
        self.tt.store(state.hash, depth, best_value, flag, best_move)
        
        return best_value

    def quiescence(self, state, alpha, beta):
        self.nodes_searched += 1
        
        base_eval = self.evaluate(state)
        if state.player != self.colour:
            base_eval = -base_eval

        if base_eval >= beta:
            return beta
        
        if base_eval > alpha:
            alpha = base_eval
            
        capture_moves = get_legal_moves(state, captures_only=True)

        capture_moves.sort(key=lambda m: (m.is_capture, m.is_promotion), reverse=True)
    
        for move in capture_moves:
            next_state = make_move(state, move)
            score = -self.quiescence(next_state, -beta, -alpha)
            
            if score >= beta:
                return beta
            if score > alpha:
                alpha = score
                
        return alpha
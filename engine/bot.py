from .move_exec import get_legal_moves, make_move, is_in_check, is_threefold_repetition
from .precomputed import init_tables
from .constants import ALL_PIECES, WHITE, BLACK, WHITE_PIECES, BLACK_PIECES
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
            
            if is_threefold_repetition(next_state):
                score = 0
            else:
                score = self.evaluate(next_state)
            
            if score > best_eval:
                best_eval = score
                best_move = move
        
        return best_move

class PositionalBot(MaterialBot):
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
            value = -self.negamax(next_state, self.depth - 1)
            
            if value > best_value:
                best_value = value
                best_move = move
                
        return best_move

    def negamax(self, state, depth):
        self.nodes_searched += 1

        if is_threefold_repetition(state):
            return 0

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
            
            value = -self.alpha_beta(next_state, self.depth - 1, -beta, -alpha)
            
            if value > best_value:
                best_value = value
                best_move = move
            
            if value > alpha:
                alpha = value

        return best_move

    def alpha_beta(self, state, depth, alpha, beta):
        self.nodes_searched += 1
        
        if is_threefold_repetition(state):
            return 0

        if depth <= 0:
            return self.quiescence(state, alpha, beta)
        
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

class AlphaBetaTTBot(PositionalBot):
    def __init__(self, colour, depth=4, tt_size_mb=64):
        super().__init__(colour)
        self.depth = depth
        self.nodes_searched = 0
        self.tt = TranspositionTable(tt_size_mb)

    def get_best_move(self, state):
        self.nodes_searched = 0

        moves = get_legal_moves(state)
        if not moves: return None
        
        tt_entry = self.tt.probe(state.hash)
        tt_move = tt_entry.best_move if tt_entry else None

        moves.sort(key=lambda m: (
            m == tt_move, 
            m.is_capture, 
            m.is_promotion
        ), reverse=True)
        
        best_move = moves[0]
        best_value = -float('inf')
        alpha = -float('inf')
        beta = float('inf')
        
        for move in moves:
            next_state = make_move(state, move)
            
            value = -self.alpha_beta(next_state, self.depth - 1, -beta, -alpha)
            
            if value > best_value:
                best_value = value
                best_move = move
            
            if value > alpha:
                alpha = value

        self.tt.store(state.hash, self.depth, best_value, FLAG_EXACT, best_move)

        return best_move

    def alpha_beta(self, state, depth, alpha, beta):
        self.nodes_searched += 1

        if is_threefold_repetition(state):
            return 0

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

        if depth <= 0:
            return self.quiescence(state, alpha, beta)
        
        moves = get_legal_moves(state)
        
        if not moves:
            if is_in_check(state, state.player):
                return -100000 + depth # Checkmate
            return 0 # Stalemate

        tt_move = tt_entry.best_move if tt_entry else None

        moves.sort(key=lambda m: (
            m == tt_move, 
            m.is_capture, 
            m.is_promotion
        ), reverse=True)
        
        best_value = -float('inf')
        best_move = None
        alpha_orig = alpha
        
        for move in moves:
            next_state = make_move(state, move)
            
            value = -self.alpha_beta(next_state, depth - 1, -beta, -alpha)
            
            if value >= beta:
                self.tt.store(state.hash, depth, beta, FLAG_LOWERBOUND, move)
                return beta
            
            if value > best_value:
                best_value = value
                best_move = move
                
            if value > alpha:
                alpha = value
        
        if best_value <= alpha_orig:
            flag = FLAG_UPPERBOUND
        else:
            flag = FLAG_EXACT
            
        self.tt.store(state.hash, depth, best_value, flag, best_move)
                
        return best_value

class QuiescenceBot(AlphaBetaBot):
    def alpha_beta(self, state, depth, alpha, beta):   
        self.nodes_searched += 1 
        
        if is_threefold_repetition(state):
            return 0

        if depth <= 0:
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

        in_check = is_in_check(state, state.player)

        if not in_check:
            base_eval = self.evaluate(state)
            if state.player != self.colour:
                base_eval = -base_eval

            if base_eval >= beta:
                return beta
            
            if base_eval > alpha:
                alpha = base_eval
        
        if in_check:
            moves = get_legal_moves(state)
            if not moves: 
                return -100000 
        else:
            moves = get_legal_moves(state, captures_only=True)

        moves.sort(key=lambda m: (m.is_capture, m.is_promotion), reverse=True)
    
        for move in moves:
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
                
                if debug: print(f"Depth {current_depth} | Move: {best_move_so_far} | Eval: {score} | Nodes: {self.nodes_searched} | Time: {time.time() - self.start_time:.3f}s")
                
                # check if we have time for next depth
                elapsed = time.time() - self.start_time
                if elapsed > self.time_limit / 2:
                    break
                    
                current_depth += 1

                if current_depth > 100: break
                
            except TimeoutError:
                #if debug: print(f"Info: Time limit reached at Depth {current_depth}")
                break
                
        return best_move_so_far

    def search_root(self, state, depth, sorted_moves):
        best_move = sorted_moves[0]
        best_value = -float('inf')
        alpha = -float('inf')
        beta = float('inf')
        
        for move in sorted_moves:
            # Reverted: Checking timeout here at depth=1 could cause us to miss mates
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

        if is_threefold_repetition(state):
            return 0

        if depth <= 0:
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

class KillerBot(PositionalBot):
    """
    Iterative Deepening
    Transposition Table (Zobrist Hashing)
    Killer Heuristic (Move Ordering)
    Quiescence Search
    """
    def __init__(self, colour, time_limit=2.0, tt_size_mb=64):
        super().__init__(colour)
        self.time_limit = time_limit
        self.tt = TranspositionTable(tt_size_mb)
        self.start_time = 0.0
        self.nodes_searched = 0
        
        # Killer Moves: [Depth][Slot] -> 2 slots per depth
        # Assume max depth 100
        self.killer_moves = [[None] * 2 for _ in range(102)]

        # Delta Pruning safety margin (Queen value + 100 pawn buffer)
        self.delta_margin = self.VALUES['Q'] + 100

    def store_killer(self, depth, move):
        """Stores a quiet move that caused a beta cutoff"""
        if move.is_capture: return # We only track quiet killer moves

        # If move is already the primary killer, do nothing
        if self.killer_moves[depth][0] == move:
            return

        # Shift old primary to secondary, save new move as primary
        self.killer_moves[depth][1] = self.killer_moves[depth][0]
        self.killer_moves[depth][0] = move

    def get_best_move(self, state, debug=False):
        self.nodes_searched = 0
        self.start_time = time.time()
        
        moves = get_legal_moves(state)
        if not moves: return None
        
        moves.sort(key=lambda m: (m.is_capture, m.is_promotion), reverse=True)
        
        best_move_so_far = moves[0]
        current_depth = 1
        
        while True:
            try:
                #if debug: print(f"Searching Depth {current_depth}...")
                
                best_move, score = self.search_root(state, current_depth, moves)
                best_move_so_far = best_move
                
                if debug: 
                    #elapsed = time.time() - self.start_time
                    #nps = int(self.nodes_searched / elapsed) if elapsed > 0 else 0
                    print(f"Depth {current_depth} | Eval: {score} | Move: {best_move} | Nodes: {self.nodes_searched:,}")

                elapsed = time.time() - self.start_time
                if elapsed > self.time_limit / 2:
                    break
                    
                current_depth += 1
                if current_depth > 100: break
                
            except TimeoutError:
                #if debug: print(f"Timeout at Depth {current_depth}")
                break
                
        return best_move_so_far

    def search_root(self, state, depth, moves):
        best_move = moves[0]
        best_value = -float('inf')
        alpha = -float('inf')
        beta = float('inf')

        tt_entry = self.tt.probe(state.hash)
        tt_move = tt_entry.best_move if tt_entry else None
        
        if tt_move and tt_move in moves:
            moves.remove(tt_move)
            moves.insert(0, tt_move)
            
        for move in moves:
            # FIX: Only timeout if we are deeper than depth 1
            if depth > 1 and time.time() - self.start_time > self.time_limit:
                raise TimeoutError()
                
            next_state = make_move(state, move)

            extension = 0
            if is_in_check(next_state, next_state.player):
                extension = 1

            value = -self.alpha_beta(next_state, depth - 1 + extension, -beta, -alpha)
            
            if value > best_value:
                best_value = value
                best_move = move
            
            if value > alpha:
                alpha = value
                
        self.tt.store(state.hash, depth, best_value, FLAG_EXACT, best_move)
        return best_move, best_value

    def alpha_beta(self, state, depth, alpha, beta):
        self.nodes_searched += 1
        if (self.nodes_searched & 2047) == 0:
            if time.time() - self.start_time > self.time_limit:
                raise TimeoutError()
        
        if is_threefold_repetition(state):
            return 0

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

        if depth <= 0:
            return self.quiescence(state, alpha, beta)

        moves = get_legal_moves(state)
        
        if not moves:
            if is_in_check(state, state.player):
                return -100000 + depth
            return 0 

        tt_move = tt_entry.best_move if tt_entry else None
        
        # Grab Killer moves for this depth
        killer_1 = self.killer_moves[depth][0]
        killer_2 = self.killer_moves[depth][1]

        # Sort Logic: TT -> Captures -> Killers -> Promotions -> Quiet
        moves.sort(key=lambda m: (
            m == tt_move,      # 1. TT Move
            m.is_capture,      # 2. Captures
            m == killer_1,     # 3. Killer Move 1
            m == killer_2,     # 4. Killer Move 2
            m.is_promotion     # 5. Promotions
        ), reverse=True)

        best_value = -float('inf')
        best_move = None
        original_alpha = alpha
        
        for move in moves:
            next_state = make_move(state, move)

            extension = 0
            if depth > 0:
                if is_in_check(next_state, next_state.player):
                    extension = 1

            value = -self.alpha_beta(next_state, depth - 1 + extension, -beta, -alpha)
            
            if value >= beta:
                # Update TT and Killer Moves
                self.tt.store(state.hash, depth, beta, FLAG_LOWERBOUND, move)
                self.store_killer(depth, move) # KILLER HEURISTIC STORE
                return beta
            
            if value > best_value:
                best_value = value
                best_move = move
                
            if value > alpha:
                alpha = value

        flag = FLAG_EXACT
        if best_value <= original_alpha:
            flag = FLAG_UPPERBOUND
        
        self.tt.store(state.hash, depth, best_value, flag, best_move)
        
        return best_value

    def quiescence(self, state, alpha, beta):
        self.nodes_searched += 1
        
        in_check = is_in_check(state, state.player)

        if not in_check:
            base_eval = self.evaluate(state)
            if state.player != self.colour:
                base_eval = -base_eval

            if base_eval >= beta:
                return beta
            
            if base_eval > alpha:
                alpha = base_eval
                
            # DELTA PRUNING
            if base_eval + self.delta_margin < alpha:
                return alpha
            
        if in_check:
            moves = get_legal_moves(state)
            if not moves:
                return -100000 
        else:
            moves = get_legal_moves(state, captures_only=True)

        moves.sort(key=lambda m: (m.is_capture, m.is_promotion), reverse=True)
    
        for move in moves:
            next_state = make_move(state, move)
            score = -self.quiescence(next_state, -beta, -alpha)
            
            if score >= beta:
                return beta
            if score > alpha:
                alpha = score
                
        return alpha

class HistoryBot(KillerBot):
    """
    Adds history heuristic to killer move bot for better ordering of quiet moves
    and MVV-LVA for capture ordering !
    """
    def __init__(self, colour, time_limit=2.0, tt_size_mb=64):
        super().__init__(colour, time_limit, tt_size_mb)
        # history table: 64x64 array [from_sq][to_sq]
        self.history_table = [[0] * 64 for _ in range(64)]

    def store_history(self, move, depth):
        """Update history score for a quiet move causing a cutoff"""
        if move.is_capture: return
        self.history_table[move.start][move.target] += depth * depth

    def get_mvv_lva_score(self, state, move):
        """
        Calculate MVV-LVA score for a capture move.
        Returns: (10 * Victim Value) - Aggressor Value
        """
        if not move.is_capture: return 0
        
        victim_val = 0
        aggressor_val = 0
        
        target_mask = 1 << move.target
        start_mask = 1 << move.start
        
        # Determine piece types by checking bitboards
        if state.player == WHITE:
            # Aggressor is White
            for p in WHITE_PIECES:
                if state.bitboards.get(p, 0) & start_mask:
                    aggressor_val = self.VALUES[p]
                    break
            # Victim is Black
            for p in BLACK_PIECES:
                if p != 'k':
                    if state.bitboards.get(p, 0) & target_mask:
                        victim_val = self.VALUES[p.upper()]
                        break
        else:
            # Aggressor is Black
            for p in BLACK_PIECES:
                if state.bitboards.get(p, 0) & start_mask:
                    aggressor_val = self.VALUES[p.upper()]
                    break
            # Victim is White
            for p in WHITE_PIECES:
                if p != 'K':
                    if state.bitboards.get(p, 0) & target_mask:
                        victim_val = self.VALUES[p]
                        break
                
        # En Passant check: if is a capture but no piece at target, victim is pawn
        if victim_val == 0:
            victim_val = 100 # Pawn value
            
        return (10 * victim_val) - aggressor_val

    def alpha_beta(self, state, depth, alpha, beta):
        self.nodes_searched += 1
        if (self.nodes_searched & 2047) == 0:
            if time.time() - self.start_time > self.time_limit:
                raise TimeoutError()
        
        if is_threefold_repetition(state):
            return 0

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

        if depth <= 0:
            return self.quiescence(state, alpha, beta)

        moves = get_legal_moves(state)
        
        if not moves:
            if is_in_check(state, state.player):
                return -100000 + depth
            return 0 

        tt_move = tt_entry.best_move if tt_entry else None
        
        killer_1 = self.killer_moves[depth][0]
        killer_2 = self.killer_moves[depth][1]

        # Improved Move Ordering:
        # 1. TT Move
        # 2. Captures sorted by MVV-LVA
        # 3. Killer Moves
        # 4. History Heuristic (Quiet moves)
        # 5. Rest
        
        def move_score(m):
            if m == tt_move:
                return 10000000 # Highest priority
            
            if m.is_capture:
                # MVV-LVA score range roughly -20000 to +200000
                # Pawn takes Queen: 9000 - 100 = 8900 (way cooler)
                # Queen takes Pawn: 1000 - 900 = 100
                return 1000000 + self.get_mvv_lva_score(state, m)
            
            if m == killer_1: return 900000
            if m == killer_2: return 800000
            
            return self.history_table[m.start][m.target]

        moves.sort(key=move_score, reverse=True)

        best_value = -float('inf')
        best_move = None
        original_alpha = alpha
        
        for move in moves:
            next_state = make_move(state, move)

            extension = 0
            if depth > 0:
                if is_in_check(next_state, next_state.player):
                    extension = 1

            value = -self.alpha_beta(next_state, depth - 1 + extension, -beta, -alpha)
            
            if value >= beta:
                # Update history & killers for quiet moves
                self.store_history(move, depth)
                self.store_killer(depth, move)
                self.tt.store(state.hash, depth, beta, FLAG_LOWERBOUND, move)
                return beta
            
            if value > best_value:
                best_value = value
                best_move = move
                
            if value > alpha:
                alpha = value

        flag = FLAG_EXACT
        if best_value <= original_alpha:
            flag = FLAG_UPPERBOUND
        
        self.tt.store(state.hash, depth, best_value, flag, best_move)
        
        return best_value

class PVSBot(HistoryBot):
    """
    Principal Variation Search (PVS)
    Relies heavily on good move ordering...
    Searches the first move with a full window, and subsequent moves with a zero-window
    to prove they are worse but if a move proves better, it re-searches it fully
    """
    def alpha_beta(self, state, depth, alpha, beta):
        self.nodes_searched += 1
        if (self.nodes_searched & 2047) == 0:
            if time.time() - self.start_time > self.time_limit:
                raise TimeoutError()
        
        if is_threefold_repetition(state):
            return 0

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

        if depth <= 0:
            return self.quiescence(state, alpha, beta)

        moves = get_legal_moves(state)
        
        if not moves:
            if is_in_check(state, state.player):
                return -100000 + depth
            return 0 

        tt_move = tt_entry.best_move if tt_entry else None
        
        killer_1 = self.killer_moves[depth][0]
        killer_2 = self.killer_moves[depth][1]

        def move_score(m):
            if m == tt_move: return 10000000
            if m.is_capture: return 1000000 + self.get_mvv_lva_score(state, m)
            if m == killer_1: return 900000
            if m == killer_2: return 800000
            return self.history_table[m.start][m.target]

        moves.sort(key=move_score, reverse=True)

        best_value = -float('inf')
        best_move = None
        original_alpha = alpha
        
        for i, move in enumerate(moves):
            next_state = make_move(state, move)

            extension = 0
            if depth > 0 and is_in_check(next_state, next_state.player):
                extension = 1

            if i == 0:
                # First move: full window search
                value = -self.alpha_beta(next_state, depth - 1 + extension, -beta, -alpha)
            else:
                # Late moves: zero-window search (alpha, alpha + 1)
                # Assume this move is worse than the best so far (alpha)
                value = -self.alpha_beta(next_state, depth - 1 + extension, -(alpha + 1), -alpha)
                
                # If value > alpha, zero-window assumption was wrong
                # This move is actually good - must re-search with full window
                if alpha < value < beta:
                    value = -self.alpha_beta(next_state, depth - 1 + extension, -beta, -alpha)
            
            if value >= beta:
                self.tt.store(state.hash, depth, beta, FLAG_LOWERBOUND, move)
                self.store_killer(depth, move)
                self.store_history(move, depth)
                return beta
            
            if value > best_value:
                best_value = value
                best_move = move
                
            if value > alpha:
                alpha = value

        flag = FLAG_EXACT
        if best_value <= original_alpha:
            flag = FLAG_UPPERBOUND
        
        self.tt.store(state.hash, depth, best_value, flag, best_move)
        
        return best_value

class LMRBot(PVSBot):
    """
    Late Move Reductions (LMR)
    Extends PVS: If a move is sorted late in the list (implying it's likely bad),
    and it is a 'quiet' move (no capture/promotion), search it with reduced depth
    If the reduced search creates a beta-cutoff, saves lots of time
    If it raises alpha, trust it and re-search properly
    """
    def alpha_beta(self, state, depth, alpha, beta):
        self.nodes_searched += 1
        if (self.nodes_searched & 2047) == 0:
            if time.time() - self.start_time > self.time_limit:
                raise TimeoutError()
        
        if is_threefold_repetition(state):
            return 0

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

        if depth <= 0:
            return self.quiescence(state, alpha, beta)

        moves = get_legal_moves(state)
        
        if not moves:
            if is_in_check(state, state.player):
                return -100000 + depth
            return 0 

        tt_move = tt_entry.best_move if tt_entry else None
        
        killer_1 = self.killer_moves[depth][0]
        killer_2 = self.killer_moves[depth][1]

        def move_score(m):
            if m == tt_move: return 10000000
            if m.is_capture: return 1000000 + self.get_mvv_lva_score(state, m)
            if m == killer_1: return 900000
            if m == killer_2: return 800000
            return self.history_table[m.start][m.target]

        moves.sort(key=move_score, reverse=True)

        best_value = -float('inf')
        best_move = None
        original_alpha = alpha
        
        in_check = is_in_check(state, state.player)

        for i, move in enumerate(moves):
            next_state = make_move(state, move)

            extension = 0
            if depth > 0 and is_in_check(next_state, next_state.player):
                extension = 1

            # LMR Logic conditions:
            # 1. Depth must be decent (>= 3)
            # 2. Move index must be late (>= 3 or 4)
            # 3. Not a tactical move (capture / promotion)
            # 4. Not in check (don't reduce escapes)
            # 5. Do not give check (extensions handle this, but don't reduce attacking moves)
            needs_full_search = True
            
            if depth >= 3 and i >= 3 and not move.is_capture and not move.is_promotion and not in_check and extension == 0:
                # Calculate reduction
                reduction = 1
                if i >= 10: reduction = 2
                if depth >= 6 and i >= 10: reduction = 3
                
                # Ensure we don't reduce below depth 1 !
                reduced_depth = max(1, depth - 1 - reduction)
                
                # Search with reduced depth and zero window
                value = -self.alpha_beta(next_state, reduced_depth, -(alpha + 1), -alpha)
                
                # If the reduced search returns valid score <= alpha, we are done (it failed low)
                # But if value > alpha, it means this move is actually better than expected
                # Must re-search fully
                if value <= alpha:
                    needs_full_search = False
                else:
                    needs_full_search = True # Result was too good, verify it

            if needs_full_search:
                if i == 0:
                    # PV Move: Full Window
                    value = -self.alpha_beta(next_state, depth - 1 + extension, -beta, -alpha)
                else:
                    # PVS Zero Window Search
                    value = -self.alpha_beta(next_state, depth - 1 + extension, -(alpha + 1), -alpha)
                    
                    # If failed high in zero window, re-search full window
                    if alpha < value < beta:
                        value = -self.alpha_beta(next_state, depth - 1 + extension, -beta, -alpha)
            
            if value >= beta:
                self.tt.store(state.hash, depth, beta, FLAG_LOWERBOUND, move)
                self.store_killer(depth, move)
                self.store_history(move, depth)
                return beta
            
            if value > best_value:
                best_value = value
                best_move = move
                
            if value > alpha:
                alpha = value

        flag = FLAG_EXACT
        if best_value <= original_alpha:
            flag = FLAG_UPPERBOUND
        
        self.tt.store(state.hash, depth, best_value, flag, best_move)
        
        return best_value

class NMPBot(LMRBot):
    """
    Null Move Pruning (NMP)
    If our position is strong enough that passing the move (doing nothing) still results in a beta-cutoff, we assume the position is winning and cut the search short
    """
    def alpha_beta(self, state, depth, alpha, beta, allow_null=True):
        self.nodes_searched += 1
        if (self.nodes_searched & 2047) == 0:
            if time.time() - self.start_time > self.time_limit:
                raise TimeoutError()
        
        if is_threefold_repetition(state):
            return 0

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

        if depth <= 0:
            return self.quiescence(state, alpha, beta)

        # Null move pruning
        if allow_null and depth >= 3 and not is_in_check(state, state.player):
            # Zugzwang check: Do we have major pieces
            # Null move pruning is succeptible to zugzwang positions as it will count a losing position; like zugzwang - a winning as it doesn't move
            has_pieces = False
            side_pieces = ['N','B','R','Q'] if state.player == WHITE else ['n','b','r','q']
            for p in side_pieces:
                if state.bitboards.get(p, 0) != 0:
                    has_pieces = True
                    break
            
            if has_pieces:
                # Create Null Move state
                try:
                    null_state = type(state)(
                        state.bitboards,
                        not state.player,
                        state.castling,
                        None, # En passant reset
                        state.halfmove_clock + 1,
                        state.fullmove_number, # Full move typically only increment on black
                        state.history
                    )
                    
                    R = 2
                    if depth > 6: R = 3
                    
                    # Search with reduced depth and zero window around beta
                    # We pass allow_null=False to prevent double null moves
                    val = -self.alpha_beta(null_state, depth - 1 - R, -beta, -beta + 1, allow_null=False)
                    
                    if val >= beta:
                        return beta
                except:
                    # Fallback
                    pass

        # Fall through to standard LMR search
        moves = get_legal_moves(state)
        
        if not moves:
            if is_in_check(state, state.player):
                return -100000 + depth
            return 0 

        tt_move = tt_entry.best_move if tt_entry else None
        
        killer_1 = self.killer_moves[depth][0]
        killer_2 = self.killer_moves[depth][1]

        def move_score(m):
            if m == tt_move: return 10000000
            if m.is_capture: return 1000000 + self.get_mvv_lva_score(state, m)
            if m == killer_1: return 900000
            if m == killer_2: return 800000
            return self.history_table[m.start][m.target]

        moves.sort(key=move_score, reverse=True)

        best_value = -float('inf')
        best_move = None
        original_alpha = alpha
        
        in_check = is_in_check(state, state.player)

        for i, move in enumerate(moves):
            next_state = make_move(state, move)

            # Check Extension
            extension = 0
            if depth > 0 and is_in_check(next_state, next_state.player):
                extension = 1

            # LMR Logic conditions
            needs_full_search = True
            
            if depth >= 3 and i >= 3 and not move.is_capture and not move.is_promotion and not in_check and extension == 0:
                reduction = 1
                if i >= 10: reduction = 2
                if depth >= 6 and i >= 10: reduction = 3
                
                reduced_depth = max(1, depth - 1 - reduction)
                
                value = -self.alpha_beta(next_state, reduced_depth, -(alpha + 1), -alpha, allow_null=True)
                
                if value <= alpha:
                    needs_full_search = False
                else:
                    needs_full_search = True 

            if needs_full_search:
                if i == 0:
                    # PV Move: Full Window
                    value = -self.alpha_beta(next_state, depth - 1 + extension, -beta, -alpha, allow_null=True)
                else:
                    # PVS Zero Window Search
                    value = -self.alpha_beta(next_state, depth - 1 + extension, -(alpha + 1), -alpha, allow_null=True)
                    
                    if alpha < value < beta:
                        value = -self.alpha_beta(next_state, depth - 1 + extension, -beta, -alpha, allow_null=True)
            
            if value >= beta:
                self.tt.store(state.hash, depth, beta, FLAG_LOWERBOUND, move)
                self.store_killer(depth, move)
                self.store_history(move, depth)
                return beta
            
            if value > best_value:
                best_value = value
                best_move = move
                
            if value > alpha:
                alpha = value

        flag = FLAG_EXACT
        if best_value <= original_alpha:
            flag = FLAG_UPPERBOUND
        
        self.tt.store(state.hash, depth, best_value, flag, best_move)
        
        return best_value

class AspirationBot(NMPBot):
    """
    Adds Aspiration Windows to the Iterative Deepening loop
    """
    def get_best_move(self, state, debug=False):
        self.nodes_searched = 0
        self.start_time = time.time()
        
        moves = get_legal_moves(state)
        if not moves: return None
        
        # Initial sort (search root will re-sort anyway)
        moves.sort(key=lambda m: (m.is_capture, m.is_promotion), reverse=True)
        
        best_move_so_far = moves[0]
        current_depth = 1
        current_score = 0
        
        while True:
            try:
                # Promote best move from previous iteration
                if best_move_so_far in moves:
                    moves.remove(best_move_so_far)
                    moves.insert(0, best_move_so_far)
                
                # Aspiration Windows
                alpha = -float('inf')
                beta = float('inf')
                window = 50
                
                # Only use aspiration windows if we have a previous score (depth > 1)
                if current_depth > 1:
                    alpha = current_score - window
                    beta = current_score + window
                    
                    best_move, score = self.search_root(state, current_depth, moves, alpha, beta)
                    
                    # Fail Low or High -> Re-search full window
                    if score <= alpha or score >= beta:
                        if debug: print(f"Depth {current_depth} aspiration fail: {score}. Re-searching")
                        alpha = -float('inf')
                        beta = float('inf')
                        best_move, score = self.search_root(state, current_depth, moves, alpha, beta)
                else:
                    best_move, score = self.search_root(state, current_depth, moves, alpha, beta)

                best_move_so_far = best_move
                current_score = score
                
                if debug: print(f"Depth {current_depth} | Move: {best_move_so_far} | Score: {score} | Nodes: {self.nodes_searched} | Time: {time.time() - self.start_time:.3f}s")
                
                elapsed = time.time() - self.start_time
                if elapsed > self.time_limit / 2:
                    break
                    
                current_depth += 1
                if current_depth > 100: break
                
            except TimeoutError:
                #if debug: print(f"Info: Time limit reached at Depth {current_depth}")
                break
                
        return best_move_so_far

    def search_root(self, state, depth, moves, alpha, beta):
        # Improve Root move ordering using History/Killer heuristics
        # This requires access to transposition table move if available
        tt_entry = self.tt.probe(state.hash)
        tt_move = tt_entry.best_move if tt_entry else None
        killer_1 = self.killer_moves[depth][0]
        killer_2 = self.killer_moves[depth][1]

        def move_score(m):
            if m == tt_move: return 10000000
            if m.is_capture: return 1000000 + self.get_mvv_lva_score(state, m)
            if m == killer_1: return 900000
            if m == killer_2: return 800000
            return self.history_table[m.start][m.target]

        # Re-sort moves at root for optimal PVS performance
        moves.sort(key=move_score, reverse=True)

        best_move = moves[0]
        best_value = -float('inf')
        
        # PVS Root Search
        for i, move in enumerate(moves):
            # Timeout Check: Only timeout if depth > 1
            if depth > 1 and time.time() - self.start_time > self.time_limit:
                raise TimeoutError()
                
            next_state = make_move(state, move)
            
            extension = 0
            if is_in_check(next_state, next_state.player):
                extension = 1
            
            if i == 0:
                # PV Move: Full window
                value = -self.alpha_beta(next_state, depth - 1 + extension, -beta, -alpha)
            else:
                # PVS: Zero window search
                value = -self.alpha_beta(next_state, depth - 1 + extension, -(alpha + 1), -alpha)
                # If failed high, re-search full window
                if alpha < value < beta:
                    value = -self.alpha_beta(next_state, depth - 1 + extension, -beta, -alpha)
            
            if value > best_value:
                best_value = value
                best_move = move
                
            if value > alpha:
                alpha = value
                # Note: At root, if found a move that exceeds beta (aspiration high fail),
                # return immediately so the outer loop can widen the window.
                if alpha >= beta:
                    return best_move, alpha # Return alpha (the high score) to trigger re-search
        
        self.tt.store(state.hash, depth, best_value, FLAG_EXACT, best_move)
        return best_move, best_value
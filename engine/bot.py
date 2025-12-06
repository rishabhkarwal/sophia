from .move_exec import get_legal_moves, make_move, is_in_check
from .precomputed import init_tables
from .constants import ALL_PIECES, WHITE, BLACK
from .utils import BitBoard

import random

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

    def get_best_move(self, state):
        
        
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

    def get_best_move(self, state):
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
        if depth == 0:
            score = self.evaluate(state)
            if state.player != self.colour:
                return -score
            return score
        
        moves = get_legal_moves(state)
        
        if not moves:
            if is_in_check(state, state.player):
                return -10000000 + depth # prefer faster mates (higher score)
            return 0 # stalemate

        # sort moves to improve pruning efficiency
        moves.sort(key=lambda m: (m.is_capture, m.is_promotion), reverse=True)
        
        best_value = -float('inf')
        
        for move in moves:
            next_state = make_move(state, move)
            value = -self.alpha_beta(next_state, depth - 1, -beta, -alpha)
            
            if value >= beta:
                # beta Cutoff: opponent has a better move elsewhere, so they won't allow this
                return beta
            
            if value > best_value:
                best_value = value
                
            if value > alpha:
                alpha = value
                
        return best_value
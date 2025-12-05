from .move_exec import get_legal_moves, make_move
from .precomputed import init_tables
from .constants import ALL_PIECES, WHITE, BLACK

import random

init_tables() #initialises lookup tables

class Bot:
    def __init__(self, colour):
        self.colour = colour

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

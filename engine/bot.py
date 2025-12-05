from .move_exec import get_legal_moves
from .precomputed import init_tables

import random

init_tables() #initialises lookup tables

class Bot:
    def __init__(self, colour):
        self.colour = colour

    def get_best_move(state):
        raise NotImplementedError("")

class RandomBot(Bot):
    def __init__(self, colour):
        super().__init__(colour)

    def get_best_move(self, state):
        """Pick a random legal move"""
        legal_moves = get_legal_moves(state)
        return random.choice(legal_moves)
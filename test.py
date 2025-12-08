from engine.bot import *
from engine.constants import WHITE, BLACK
from engine.fen_parser import load_from_fen

from time import time_ns
from random import choice
from tqdm import tqdm

from book import start_positions

positions = 10

results = []

for _ in range(positions):
    fen = choice(start_positions)

    state = load_from_fen(fen)
    colour = state.player
    bots = [IterativeDeepeningBot(colour, time_limit=5), TranspositionBot(colour, time_limit=5)]

    print(f'{fen}')
    for bot in bots:
        print(f'\n\t{bot}')
        start = time_ns()
        move = bot.get_best_move(state)
        dt = time_ns() - start

        results.append(f"{bot} : {move} | {bot.nodes_searched} | {dt / 1e9 : .4f}")

    results.append('\n')

print('\n'.join(results))


""" 
Testing framework to see performance difference between different implementations
"""
from engine.bot import *
from engine.constants import WHITE, BLACK
from engine.fen_parser import load_from_fen

from time import time_ns
from random import choice
from tqdm import tqdm

from book import start_positions

positions = 1

results = []

total_nodes_base = 0
total_time_base = 0
total_nodes_opt = 0
total_time_opt = 0

with tqdm(total=positions, unit='pos', dynamic_ncols=False) as pbar:
    for i in range(positions):
        fen = choice(start_positions)

        state = load_from_fen(fen)
        colour = state.player
        bots = [SearchTreeBot(colour, depth=3), AlphaBetaTTBot(colour, depth=3)]

        pbar.set_description(f"{fen}") 

        stats = []

        for idx, bot in enumerate(bots):
            pbar.set_postfix_str(f"{bot}")
            
            start = time_ns()
            move = bot.get_best_move(state)
            dt = time_ns() - start
            
            seconds = dt / 1e9
            stats.append((bot.nodes_searched, seconds))

            results.append(f"{bot} : {move} | {bot.nodes_searched} | {seconds : .4f}")
        
        if len(stats) == 2:
            total_nodes_base += stats[0][0]
            total_time_base += stats[0][1]
            
            total_nodes_opt += stats[1][0]
            total_time_opt += stats[1][1]

        pbar.update(1)

pbar.clear()

results.append('\n')

# print('\n'.join(results))

if total_nodes_base > 0 and total_time_opt > 0:
    overall_reduction = (1 - (total_nodes_opt / total_nodes_base)) * 100
    
    overall_speedup = total_time_base / total_time_opt
    
    print(f"Total Nodes: {total_nodes_base:,} -> {total_nodes_opt:,}")
    print(f"Total Time:  {total_time_base:.4f}s -> {total_time_opt:.4f}s")
    print(f"\n>>> OVERALL REDUCTION: {overall_reduction:.2f}%")
    print(f">>> OVERALL SPEEDUP:   {overall_speedup:.2f}x")

"""
100 positions
Depth 3


Total Nodes: 4,157,204 -> 260,015
Total Time:  352.6991s -> 46.3694s

>>> OVERALL REDUCTION: 93.75%
>>> OVERALL SPEEDUP:   7.61x

----------------------------------------
Total Nodes: 4,109,146 -> 264,666
Total Time:  513.2383s -> 70.9421s

>>> OVERALL REDUCTION: 93.56%
>>> OVERALL SPEEDUP:   7.23x
"""

"""
10 positions
Depth 4


Total Nodes: 12,950,225 -> 200,034
Total Time:  1564.7936s -> 71.9068s

>>> OVERALL REDUCTION: 98.46%
>>> OVERALL SPEEDUP:   21.76x
"""

"""
startpos
Depth 5

Total Nodes: 5,072,212 -> 1,070,650 SECOND IS ACC DEPTH 6 !!
Total Time:  598.5430s -> 299.7969s

>>> OVERALL REDUCTION: 78.89%
>>> OVERALL SPEEDUP:   2.00x
"""
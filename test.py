from engine.bot import *
from engine.constants import WHITE, BLACK
from engine.fen_parser import load_from_fen

from time import time_ns
from random import choice
from tqdm import tqdm

from book import start_positions

positions = 10

try:
    for _ in range(positions):
        fen = choice(start_positions)

        state = load_from_fen(fen)
        colour = state.player
        bots = [AlphaBetaBot(colour, depth=3), TranspositionBot(colour, time_limit=2)]

        print(f'\n{fen}')
        for bot in bots:
            print(f'  {str(bot).replace('Bot', ''):<15}\t', end='', flush=True)
            start = time_ns()
            move = bot.get_best_move(state)
            dt = time_ns() - start

            print(f": {move} | {bot.nodes_searched} | {dt / 1e9 : .4f}")
except KeyboardInterrupt:
    pass


""" 
Testing framework to see performance difference between different implementation

rnbqk2r/1p2bppp/p2ppn2/6B1/3NP3/2N5/PPP1BPPP/R2QK2R w KQkq -
  AlphaBeta             : O-O | 2755 |  0.6964
  Transposition         : d1d3 | 9905 |  1.3227

rnbqkb1r/pp1ppppp/5n2/2p5/2P1P3/2N5/PP1P1PPP/R1BQKBNR b KQkq -
  AlphaBeta             : d8a5 | 1839 |  0.5454
  Transposition         : b8c6 | 12623 |  2.0607

r1bq1rk1/pp2ppbp/2np1np1/8/3PP3/2N2N2/PP2BPPP/R1BQ1RK1 w - -
  AlphaBeta             : d1a4 | 5236 |  1.0515
  Transposition         : c1e3 | 17111 |  2.1039

rnbqk2r/pp2bppp/4pn2/2pp4/2PP4/5NP1/PP2PPBP/RNBQ1RK1 b kq -
  AlphaBeta             : d5c4 | 1550 |  0.3552
  Transposition         : d5c4 | 12014 |  2.1855

r1bqkb1r/pp1p1ppp/2n2n2/8/3NP3/2N5/PP3PPP/R1BQKB1R b KQkq -
  AlphaBeta             : c6d4 | 1329 |  0.5141
  Transposition         : d7d5 | 13403 |  2.1331

rn1qkb1r/pp3ppp/2p1pn2/8/3PB3/5N2/PPP2PPP/R1BQ1RK1 w kq -
  AlphaBeta             : c1g5 | 1699 |  0.4569
  Transposition         : c1g5 | 22198 |  2.8909

rnbqkb1r/pp1p1ppp/4p3/2pnP3/8/2P2N2/PP1P1PPP/RNBQKB1R w KQkq -
  AlphaBeta             : f1c4 | 3239 |  0.5508
  Transposition         : c3c4 | 14098 |  2.1963

rnbqkbnr/ppp2ppp/8/3pp3/8/2P5/PPQPPPPP/RNB1KBNR w KQkq -
  AlphaBeta             : g1f3 | 2498 |  0.5776
  Transposition         : g1f3 | 5748 |  1.1329

r2qkb1r/pp3ppp/2n1pn2/2pp1b2/3P1B2/2P1PN2/PP1N1PPP/R2QKB1R w KQkq -
  AlphaBeta             : f3h4 | 2544 |  0.7757
  Transposition         : f1b5 | 13169 |  2.1284

rnbqk1nr/ppp2p1p/3b4/8/3P2p1/5N2/PPP1P1PP/RNBQKB1R w KQkq -
  AlphaBeta             : c1g5 | 2279 |  0.6189
  Transposition         : f3g5 | 12963 |  1.9652
"""
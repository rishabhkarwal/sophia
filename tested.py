from engine.fen_parser import load_from_fen

from engine.bot import PVSBot as Bot

position = "8/4B3/8/4p2P/5k2/1K5p/8/8 w - - 0 1"
state = load_from_fen(position)
colour = state.player

engine = Bot(colour, time_limit=5)

engine.get_best_move(state, debug=True)

"""
PVS:
Depth 1 | Eval: 265 | Move: b3a2 | Nodes: 37
Depth 2 | Eval: 225 | Move: b3a2 | Nodes: 109
Depth 3 | Eval: 235 | Move: b3a2 | Nodes: 761
Depth 4 | Eval: 190 | Move: e7a3 | Nodes: 2,518
Depth 5 | Eval: -510 | Move: b3a2 | Nodes: 8,021
Depth 6 | Eval: -510 | Move: b3a2 | Nodes: 15,894
Depth 7 | Eval: -535 | Move: b3a2 | Nodes: 37,702

History:
Depth 1 | Eval: 265 | Move: b3a2 | Nodes: 37
Depth 2 | Eval: 225 | Move: b3a2 | Nodes: 109
Depth 3 | Eval: 235 | Move: b3a2 | Nodes: 759
Depth 4 | Eval: 190 | Move: e7a3 | Nodes: 2,514
Depth 5 | Eval: -510 | Move: b3a2 | Nodes: 8,034
Depth 6 | Eval: -510 | Move: b3a2 | Nodes: 15,769
Depth 7 | Eval: -535 | Move: b3a2 | Nodes: 36,265

Killer:
Depth 1 | Eval: 265 | Move: b3a2 | Nodes: 37
Depth 2 | Eval: 225 | Move: b3a2 | Nodes: 109
Depth 3 | Eval: 235 | Move: b3a2 | Nodes: 765
Depth 4 | Eval: 175 | Move: e7b4 | Nodes: 2,065
Depth 5 | Eval: 185 | Move: e7f8 | Nodes: 8,949
Depth 6 | Eval: -515 | Move: e7b4 | Nodes: 18,500
Depth 7 | Eval: -510 | Move: e7b4 | Nodes: 35,765

Iterative Deepening:
Depth 1 | Move: b3a2 | Eval: 265 | Nodes: 37 | Time: 0.002s
Depth 2 | Move: b3a2 | Eval: 225 | Nodes: 109 | Time: 0.010s
Depth 3 | Move: b3a2 | Eval: 235 | Nodes: 765 | Time: 0.062s
Depth 4 | Move: e7b4 | Eval: 175 | Nodes: 2391 | Time: 0.362s
Depth 5 | Move: e7f8 | Eval: 185 | Nodes: 14029 | Time: 1.543s
"""
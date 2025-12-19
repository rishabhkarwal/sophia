from engine.board.fen_parser import load_from_fen
from engine.search.search import SearchEngine

position = "8/4B3/8/4p2P/5k2/1K5p/8/8 w - - 0 1"
state = load_from_fen(position)

print(f"Testing Position: {position}\n")

engine = SearchEngine(time_limit=5.0, tt_size_mb=64)


best_move = engine.get_best_move(state, debug=True)

print(f"\nBest Move: {best_move}")

"""
Testing Position: 8/4B3/8/4p2P/5k2/1K5p/8/8 w - - 0 1

Depth 1 | Move: b3c4 | Score: 191 | Nodes: 41 | NPS: 28,527 | Time: 0.0014
Depth 2 | Move: b3c4 | Score: 160 | Nodes: 113 | NPS: 16,689 | Time: 0.0068
Depth 3 | Move: b3c4 | Score: 180 | Nodes: 769 | NPS: 17,679 | Time: 0.0435
Aspiration fail @ Depth 4 (Score: 130) ∴ Re-searching...
Depth 4 | Move: e7b4 | Score: 114 | Nodes: 2,514 | NPS: 11,597 | Time: 0.2168
Depth 5 | Move: e7b4 | Score: 151 | Nodes: 4,402 | NPS: 14,159 | Time: 0.3109
Aspiration fail @ Depth 6 (Score: 101) ∴ Re-searching...
Depth 6 | Move: e7b4 | Score: -550 | Nodes: 13,799 | NPS: 11,515 | Time: 1.1983
Depth 7 | Move: e7b4 | Score: -532 | Nodes: 19,810 | NPS: 12,187 | Time: 1.6255
Depth 8 | Move: e7b4 | Score: -557 | Nodes: 37,260 | NPS: 11,689 | Time: 3.1874

Best Move: e7b4
"""
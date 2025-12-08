from engine.game import Game
from engine.bot import *
from engine.constants import WHITE, BLACK

if __name__ == "__main__":
    game = Game(IterativeDeepeningBot(WHITE, time_limit=5), TranspositionBot(BLACK, time_limit=5, tt_size_mb=128))
    #results = game.test(50)
    #print(results)

    game.run(debug=True)

"""
Testing:  20%|---  | 10/50 [1:38:03<6:32:13, 588.34s/game, => White (IterativeDeepeningBot): 0, Black (TranspositionBot): 0, Draw: 10]

White (IterativeDeepeningBot): 0.0%
Black (TranspositionBot): 0.0%
Draw: 100%
        50-move rule: 10
        Stalemate: 0


Test results from new test.py to compare iterative deepening approaches

rnbqk1nr/p1ppppbp/1p4p1/8/2PP4/2N5/PP2PPPP/R1BQKBNR w KQkq -

        IterativeDeepeningBot
Info: Depth 1 | Move: g1f3 | Score: 145 | Nodes: 74 | Time: 0.004s
Info: Depth 2 | Move: g1f3 | Score: 95 | Nodes: 1253 | Time: 0.126s
Info: Depth 3 | Move: g1f3 | Score: 135 | Nodes: 11239 | Time: 0.809s
Info: Time limit reached at Depth 4

        TranspositionBot
Info: Depth 1 | Move: g1f3 | Score: 145 | Nodes: 74 | Time: 0.003s
Info: Depth 2 | Move: g1f3 | Score: 95 | Nodes: 1253 | Time: 0.130s
Info: Depth 3 | Move: g1f3 | Score: 135 | Nodes: 6231 | Time: 0.515s
Info: Time limit reached at Depth 4
rnbqkb1r/pp1ppppp/5n2/2p5/2P1P3/2N5/PP1P1PPP/R1BQKBNR b KQkq -

        IterativeDeepeningBot
Info: Depth 1 | Move: b8c6 | Score: 10 | Nodes: 57 | Time: 0.003s
Info: Depth 2 | Move: b8c6 | Score: -40 | Nodes: 365 | Time: 0.054s
Info: Depth 3 | Move: b8c6 | Score: 0 | Nodes: 3905 | Time: 0.315s
Info: Depth 4 | Move: b8c6 | Score: -20 | Nodes: 25428 | Time: 2.528s

        TranspositionBot
Info: Depth 1 | Move: b8c6 | Score: 10 | Nodes: 57 | Time: 0.003s
Info: Depth 2 | Move: b8c6 | Score: -40 | Nodes: 365 | Time: 0.048s
Info: Depth 3 | Move: b8c6 | Score: 0 | Nodes: 2877 | Time: 0.258s
Info: Depth 4 | Move: b8c6 | Score: -20 | Nodes: 15837 | Time: 1.825s
Info: Time limit reached at Depth 5
r1bq1rk1/pp2ppbp/2np1np1/8/3PP3/2N2N2/PP2BPPP/R1BQ1RK1 w - -

        IterativeDeepeningBot
Info: Depth 1 | Move: c1e3 | Score: 90 | Nodes: 123 | Time: 0.007s
Info: Depth 2 | Move: c1f4 | Score: 70 | Nodes: 31069 | Time: 3.095s

        TranspositionBot
Info: Depth 1 | Move: c1e3 | Score: 90 | Nodes: 123 | Time: 0.008s
Info: Depth 2 | Move: c1f4 | Score: 70 | Nodes: 30462 | Time: 2.949s
rnbqk2r/pp2bppp/4pn2/2pp4/2PP4/5NP1/PP2PPBP/RNBQ1RK1 b kq -

        IterativeDeepeningBot
Info: Depth 1 | Move: d5c4 | Score: 90 | Nodes: 106 | Time: 0.006s
Info: Depth 2 | Move: d5c4 | Score: 50 | Nodes: 475 | Time: 0.067s
Info: Depth 3 | Move: d5c4 | Score: 50 | Nodes: 4378 | Time: 0.437s
Info: Time limit reached at Depth 4

        TranspositionBot
Info: Depth 1 | Move: d5c4 | Score: 90 | Nodes: 106 | Time: 0.006s
Info: Depth 2 | Move: d5c4 | Score: 50 | Nodes: 475 | Time: 0.082s
Info: Depth 3 | Move: d5c4 | Score: 50 | Nodes: 3416 | Time: 0.341s
Info: Depth 4 | Move: d5c4 | Score: 50 | Nodes: 15518 | Time: 2.223s
Info: Time limit reached at Depth 5
r1bqkb1r/pp1p1ppp/2n2n2/8/3NP3/2N5/PP3PPP/R1BQKB1R b KQkq -

        IterativeDeepeningBot
Info: Depth 1 | Move: d7d5 | Score: -20 | Nodes: 197 | Time: 0.017s
Info: Depth 2 | Move: d7d5 | Score: -25 | Nodes: 1910 | Time: 0.231s
Info: Depth 3 | Move: f8b4 | Score: -15 | Nodes: 14295 | Time: 1.839s
Info: Depth 4 | Move: f8b4 | Score: -15 | Nodes: 34420 | Time: 4.934s

        TranspositionBot
Info: Depth 1 | Move: d7d5 | Score: -20 | Nodes: 197 | Time: 0.017s
Info: Depth 2 | Move: d7d5 | Score: -25 | Nodes: 1910 | Time: 0.213s
Info: Depth 3 | Move: f8b4 | Score: -15 | Nodes: 15639 | Time: 1.486s
Info: Depth 4 | Move: f8b4 | Score: -15 | Nodes: 33206 | Time: 4.349s
rn1qkb1r/pp3ppp/2p1pn2/8/3PB3/5N2/PPP2PPP/R1BQ1RK1 w kq -

        IterativeDeepeningBot
Info: Depth 1 | Move: c1g5 | Score: 145 | Nodes: 470 | Time: 0.045s
Info: Depth 2 | Move: c1g5 | Score: 100 | Nodes: 2261 | Time: 0.226s
Info: Depth 3 | Move: c1g5 | Score: 110 | Nodes: 11983 | Time: 1.105s
Info: Time limit reached at Depth 4

        TranspositionBot
Info: Depth 1 | Move: c1g5 | Score: 145 | Nodes: 470 | Time: 0.107s
Info: Depth 2 | Move: c1g5 | Score: 100 | Nodes: 2261 | Time: 0.485s
Info: Depth 3 | Move: c1g5 | Score: 110 | Nodes: 5956 | Time: 0.915s
Info: Time limit reached at Depth 4
rnbqkb1r/pp1p1ppp/4p3/2pnP3/8/2P2N2/PP1P1PPP/RNBQKB1R w KQkq -

        IterativeDeepeningBot
Info: Depth 1 | Move: d2d4 | Score: 45 | Nodes: 63 | Time: 0.006s
Info: Depth 2 | Move: c3c4 | Score: 20 | Nodes: 1557 | Time: 0.378s
Info: Depth 3 | Move: c3c4 | Score: 70 | Nodes: 6424 | Time: 1.296s
Info: Time limit reached at Depth 4

        TranspositionBot
Info: Depth 1 | Move: d2d4 | Score: 45 | Nodes: 63 | Time: 0.014s
Info: Depth 2 | Move: c3c4 | Score: 20 | Nodes: 1557 | Time: 0.343s
Info: Depth 3 | Move: c3c4 | Score: 70 | Nodes: 4126 | Time: 0.997s
Info: Time limit reached at Depth 4
rnbqkbnr/ppp2ppp/8/3pp3/8/2P5/PPQPPPPP/RNB1KBNR w KQkq -

        IterativeDeepeningBot
Info: Depth 1 | Move: g1f3 | Score: -40 | Nodes: 59 | Time: 0.008s
Info: Depth 2 | Move: g1f3 | Score: -90 | Nodes: 3672 | Time: 0.717s
Info: Depth 3 | Move: g1f3 | Score: -50 | Nodes: 10165 | Time: 1.760s
Info: Time limit reached at Depth 4

        TranspositionBot
Info: Depth 1 | Move: g1f3 | Score: -40 | Nodes: 59 | Time: 0.007s
Info: Depth 2 | Move: g1f3 | Score: -90 | Nodes: 3672 | Time: 0.806s
Info: Depth 3 | Move: g1f3 | Score: -50 | Nodes: 5748 | Time: 1.154s
Info: Time limit reached at Depth 4
r2qkb1r/pp3ppp/2n1pn2/2pp1b2/3P1B2/2P1PN2/PP1N1PPP/R2QKB1R w KQkq -

        IterativeDeepeningBot
Info: Depth 1 | Move: f1b5 | Score: 0 | Nodes: 383 | Time: 0.107s
Info: Depth 2 | Move: f1b5 | Score: -10 | Nodes: 3538 | Time: 0.912s
Info: Depth 3 | Move: f1b5 | Score: 0 | Nodes: 20668 | Time: 3.753s

        TranspositionBot
Info: Depth 1 | Move: f1b5 | Score: 0 | Nodes: 383 | Time: 0.081s
Info: Depth 2 | Move: f1b5 | Score: -10 | Nodes: 3532 | Time: 0.671s
Info: Depth 3 | Move: f1b5 | Score: 0 | Nodes: 20190 | Time: 3.899s
rnbqk1nr/ppp2p1p/3b4/8/3P2p1/5N2/PPP1P1PP/RNBQKB1R w KQkq -

        IterativeDeepeningBot
Info: Depth 1 | Move: c1g5 | Score: 140 | Nodes: 177 | Time: 0.037s
Info: Depth 2 | Move: c1g5 | Score: 90 | Nodes: 945 | Time: 0.227s
Info: Depth 3 | Move: f3g5 | Score: 120 | Nodes: 13310 | Time: 2.347s
Info: Time limit reached at Depth 4

        TranspositionBot
Info: Depth 1 | Move: c1g5 | Score: 140 | Nodes: 177 | Time: 0.029s
Info: Depth 2 | Move: c1g5 | Score: 90 | Nodes: 945 | Time: 0.183s
Info: Depth 3 | Move: f3g5 | Score: 120 | Nodes: 12963 | Time: 2.367s
Info: Time limit reached at Depth 4
"""
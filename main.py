from engine.game import Game
from engine.bot import *
from engine.constants import WHITE, BLACK

if __name__ == "__main__":
    game = Game(white_player=SearchTreeBot(WHITE), black_player=AlphaBetaBot(BLACK, depth=5))
    results = game.test(100)
    print(results)

    #game.run(delay=2)

"""
Testing:  67%|---                                           | 67/100 [=> White (SearchTreeBot): 0, Black (AlphaBetaBot): 27, Draw: 40]

Depth of 5 proven to perform better than depth 3
Have implemented alpha-beta pruning (& move-ordering)
Captures and promotions checked first
This doesn't impact chosen move; just the time it takes -> pruning is more efficient
"""
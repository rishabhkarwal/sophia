from engine.game import Game
from engine.bot import *
from engine.constants import WHITE, BLACK

if __name__ == "__main__":
    game = Game(white_player=QuiescenceBot(WHITE, depth=3), black_player=AlphaBetaBot(BLACK, depth=3))
    results = game.test(100)
    print(results)

    #game.run(delay=0)

"""
Testing:  35%|---                                | 35/100 [5:30:59<10:14:42, 567.42s/game, => White (QuiescenceBot): 35, Black (AlphaBetaBot): 0, Draw: 0]

Continues searching a 'noisy' position until it becomes 'quiet' -> helps tactics from being missed
"""
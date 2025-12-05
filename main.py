from engine.game import Game
from engine.bot import RandomBot, MaterialBot
from engine.constants import WHITE, BLACK

if __name__ == "__main__":
    game = Game(MaterialBot(WHITE), RandomBot(BLACK))
    results = game.test(1000)
    print(results)

"""
Testing: 100%|---| 1000/1000 [01:44<00:00,  9.56game/s, => White: 243, Black: 1, Draw: 756]

White: 24.3%
Black: 0.1%
Draw: 75.6%
"""
from engine.game import Game
from engine.bot import *
from engine.constants import WHITE, BLACK

if __name__ == "__main__":
    player_1 = HistoryBot(WHITE, time_limit=2, tt_size_mb=32)
    player_2 = PVSBot(BLACK, time_limit=2, tt_size_mb=32)
    game = Game(player_1, player_2)
    
    results = game.test(10)
    print(results)

    #game.run(debug=True)

"""
Testing:  100%|---| 10/10 [42:19<0:00, 163.98s/game, => HistoryBot (White): 2, PVSBot (Black): 3, Draw: 5] 

HistoryBot (White): 20.0%
PVSBot (Black): 30.0%
Draw: 50.0%
        50-Move Rule: 0
        Stalemate: 0
        Threefold Repetition: 5

Principal-Variation ASSUMES first ordered move is best and so searches it completely and searches subsequent to a reduced depth until proven wrong
"""
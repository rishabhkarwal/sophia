from engine.game import Game
from engine.bot import *
from engine.constants import WHITE, BLACK

if __name__ == "__main__":
    player_1 = AspirationBot(WHITE, time_limit=3, tt_size_mb=32)
    player_2 = NMPBot(BLACK, time_limit=3, tt_size_mb=32)
    game = Game(player_1, player_2)
    
    results = game.test(10)
    print(results)

    #game.run(debug=True)

"""
Testing:  60%|--- | 6/10 [39:01<26:00, 390.18s/game, => AspirationBot (White): 1, NMPBot (Black): 0, Draw: 5]    

AspirationBot (White): 14.29%
NMPBot (Black): 0.0%
Draw: 71.43%
        50-Move Rule: 0
        Stalemate: 0
        Threefold Repetition: 5

Currently, loop searches every depth with a full window (-infinity, +infinity)
This forces the engine to search for "mate scores" even when the position is likely just "slightly winning" (e.g., +0.5)

Aspiration Windows optimise this by guessing that the score for Depth N will be roughly similar to Depth N-1

We search with a narrow window around the previous score and if result falls within this window then we save a lot of time ! 

This makes the engine significantly faster in stable positions
"""
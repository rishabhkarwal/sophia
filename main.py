from engine.game import Game
from engine.bot import *
from engine.constants import WHITE, BLACK

if __name__ == "__main__":
    player_1 = PositionalBot(WHITE)
    player_2 = PhasePositionalBot(BLACK)
    game = Game(player_1, player_2)
    
    results = game.test(1000)
    print(results)

    #game.run(debug=True)

"""
Testing: 100%|---| 1000/1000 [04:05<00:00,  4.08game/s, => PositionalBot (White): 21, PhasePositionalBot (Black): 109, Draw: 870]

PositionalBot (White): 2.1%
PhasePositionalBot (Black): 10.9%
Draw: 87.0%
        50-Move Rule: 133
        Stalemate: 228
        Threefold Repetition: 509

As it is only a depth 1 bot; most games are draws and are random BUT it rarely loses to old PSQT based bot

New PSQT bot now looks at game phase to assign values to squares => can have differing PSQT based on whether its middlegame or endgame

Allows kings to be pushed to the corners in middlegame; and then pushed to centre in endgame

"""
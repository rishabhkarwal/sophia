from engine.game import Game
from engine.bot import *
from engine.constants import WHITE, BLACK

if __name__ == "__main__":
    player_1 = KillerBot(WHITE, time_limit=2, tt_size_mb=32)
    player_2 = HistoryBot(BLACK, time_limit=2, tt_size_mb=32)
    game = Game(player_1, player_2)
    
    results = game.test(10)
    print(results)

    #game.run(debug=True)

"""
Testing:  50%|---  | 5/10 [13:39<13:39, 163.98s/game, => HistoryBot (White): 3, KillerBot (Black): 0, Draw: 2] 

HistoryBot (White): 60.0%
KillerBot (Black): 0.0%
Draw: 40.0%
        50-Move Rule: 0
        Stalemate: 0
        Threefold Repetition: 2

Implemented history heuristic: tracks moves that caused beta-cutoffs (these proved to be good) and add them to move ordering to make it faster

        # 1. TT Move
        # 2. Captures sorted by MVV-LVA
        # 3. Killer Moves
        # 4. History Heuristic (Quiet moves)
        # 5. Rest


MVV-LVA (Most Valuable Victim - Least Valuable Aggressor): Prioritises captures where a low-value piece takes a high-value piece

        (Pawn takes Queen) is checked before (Rook takes Queen)
"""
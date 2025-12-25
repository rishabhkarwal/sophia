from engine.uci.handler import UCI
from engine.core.move import move_to_uci

import cProfile
import pstats

def test(position='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1', time_limit=2.0):
        uci = UCI()

        print(f'Testing Position: {position}\n')

        position_args = ['fen'] + position.split()
        uci.handle_position(position_args)

        uci.engine.time_limit = time_limit * 1000

        profiler = cProfile.Profile()
        profiler.enable()
        
        best_move = uci.engine.get_best_move(uci.state)

        profiler.disable()
    
        print(f'\nBest Move: {move_to_uci(best_move)}\n\n')
        
        stats = pstats.Stats(profiler).sort_stats('cumulative')
        stats.print_stats(30)


if __name__ == '__main__':
        fen = '5B2/1P2P2P/2P1r3/2b1p3/6p1/2K2P1k/p7/nN5B w - - 0 1'
        time = 60
        test(position=fen, time_limit=time)
        
"""
pypy3 profiler.py
"""

"""

SCENARIO:

    Position:    5B2/1P2P2P/2P1r3/2b1p3/6p1/2K2P1k/p7/nN5B w - - 0 1 

    Time Limit: 60 seconds


Search Depth:   10
Nodes/Sec:      ~30,597
Total Time:     60.044s
Function Calls: 126,800,167


Search Log:

    info depth 1 currmove h7h8q score cp 1659 nodes 2636 nps 2999 time 878 hashfull 0 pv h7h8q
    info depth 2 currmove h7h8q score cp 1659 nodes 4930 nps 3678 time 1340 hashfull 0 pv h7h8q h3g3
    info depth 3 currmove h7h8q score cp 1659 nodes 7462 nps 4218 time 1768 hashfull 0 pv h7h8q h3g3 b7b8q
    info depth 4 currmove h7h8q score cp 1659 nodes 21038 nps 6193 time 3396 hashfull 0 pv h7h8q h3g3 b7b8q c5e7
    info depth 5 currmove h7h8q score cp 1584 nodes 65361 nps 9848 time 6636 hashfull 0 pv h7h8q h3g3 b7b8q a1b3 b8e5
    info depth 6 currmove h7h8q score cp 1584 nodes 118493 nps 11516 time 10288 hashfull 3 pv h7h8q h3g3 b7b8q a1b3 b8e5 e6e5
    info depth 7 currmove h7h8q score cp 1584 nodes 181402 nps 14498 time 12512 hashfull 5 pv h7h8q h3g3 b7b8q a1b3 b8e5 e6e5 h8e5
    info depth 8 currmove h7h8q score cp 1584 nodes 432461 nps 19590 time 22074 hashfull 21 pv h7h8q h3g3 b7b8q a1b3 b8e5 e6e5 h8e5 g3h3
    info depth 9 currmove h7h8q score cp 1722 nodes 739522 nps 23640 time 31282 hashfull 29 pv h7h8q h3g3 b7b8q c5e7 f3g4 e7f8 h8f8 g3g4 f8f2
    info depth 10 currmove h7h8q score cp 1723 nodes 1344457 nps 27703 time 48529 hashfull 63 pv h7h8q h3g3 b7b8q a1b3 b8e5 e6e5 h8e5 g3h3 e5h5 h3g3


Profile Stats:

     ncalls  tottime  percall  cumtime  percall  filename:lineno(function)
          1    0.001    0.001   60.044   60.044  engine/search/search.py:76(get_best_move)
         13    0.002    0.000   60.030    4.618  engine/search/search.py:173(_search_root)
 352288/283    2.009    0.000   60.022    0.212  engine/search/search.py:209(_alpha_beta)
1484768/241    6.942    0.000   50.943    0.000  engine/search/search.py:321(_quiescence)
     593232    2.404    0.000   12.668    0.000  engine/moves/generator.py:34(generate_pseudo_legal_moves)
    1328643    9.524    0.000   11.243    0.000  engine/search/evaluation.py:137(evaluate)
    2849564    9.811    0.000   10.013    0.000  engine/board/move_exec.py:45(make_move)
    2849559    6.493    0.000    6.605    0.000  engine/board/move_exec.py:193(unmake_move)
    4407858    1.200    0.000    6.146    0.000  engine/moves/legality.py:57(is_in_check)
    4407858    4.803    0.000    4.803    0.000  engine/moves/legality.py:17(is_square_attacked)
     593245    2.565    0.000    3.430    0.000  {method 'sort' of 'list' objects}
     593232    2.227    0.000    2.559    0.000  engine/moves/generator.py:222(_gen_queen_moves)
     593232    1.673    0.000    1.915    0.000  engine/moves/generator.py:205(_gen_rook_moves)
     593232    1.509    0.000    1.861    0.000  engine/moves/generator.py:60(_gen_pawn_moves)
     593232    1.514    0.000    1.686    0.000  engine/moves/generator.py:188(_gen_bishop_moves)
   34162197    1.183    0.000    1.183    0.000  {method 'bit_length' of 'int' objects}

"""
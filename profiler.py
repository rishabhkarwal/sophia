from engine.uci.handler import UCI
from engine.core.move import move_to_uci

import cProfile
import pstats

def test(position='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1', time_limit=2.0):
        uci = UCI(debug=True)

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
        stats.print_stats(10)


if __name__ == '__main__':
        fen = '8/3K4/1k6/8/8/8/7p/8 w - - 0 1'
        time = 5
        test(position=fen, time_limit=time)
        

"""
SCENARIO:
    Position:    8/3K4/1k6/8/8/8/7p/8 w - - 0 1 
    Time Limit: 5 seconds

Search Depth:   14
Nodes/Sec:      ~41,200
Total Time:     5.049s
Function Calls: 6,375,825

Search Log:
    info depth 1 currmove d7e6 score cp -914 nodes 30 nps 29167 time 1 hashfull 0
    info depth 2 currmove d7e6 score cp -914 nodes 70 nps 27485 time 2 hashfull 0
    info depth 3 currmove d7d6 score cp -911 nodes 331 nps 28837 time 11 hashfull 0
    info depth 4 currmove d7d6 score cp -975 nodes 900 nps 32092 time 28 hashfull 0
    info depth 5 currmove d7e7 score cp -923 nodes 1489 nps 31843 time 46 hashfull 0
    info depth 6 currmove d7d6 score cp -996 nodes 4317 nps 32632 time 132 hashfull 1
    info depth 7 currmove d7e6 score cp -996 nodes 8465 nps 33997 time 248 hashfull 4
    info depth 8 currmove d7e6 score cp -995 nodes 16584 nps 37360 time 443 hashfull 6
    info depth 9 currmove d7e6 score cp -995 nodes 21781 nps 37570 time 579 hashfull 9
    info depth 10 currmove d7e6 score cp -997 nodes 42445 nps 39373 time 1077 hashfull 15
    info depth 11 currmove d7e6 score cp -996 nodes 75833 nps 39345 time 1927 hashfull 28
    info depth 12 currmove d7e6 score cp -998 nodes 106541 nps 40122 time 2655 hashfull 36
    info depth 13 currmove d7e6 score cp -998 nodes 150982 nps 40489 time 3728 hashfull 52
    info depth 14 currmove d7e6 score cp 998 nodes 208122 nps 41224 time 5048 hashfull 67

Profile Stats:
     ncalls  tottime  percall  cumtime  percall  filename:lineno(function)
          1    0.000    0.000    5.049    5.049  engine/search/search.py:23(get_best_move)
         18    0.000    0.000    5.043    0.280  engine/search/search.py:105(_search_root)
 128252/108    0.662    0.000    5.042    0.047  engine/search/search.py:141(_alpha_beta)
79870/65157    0.160    0.000    1.816    0.000  engine/search/search.py:238(_quiescence)
      58255    0.188    0.000    0.987    0.000  engine/moves/generator.py:35(generate_pseudo_legal_moves)
      67445    0.509    0.000    0.725    0.000  engine/search/evaluation.py:177(evaluate)
     151735    0.647    0.000    0.715    0.000  engine/board/move_exec.py:47(make_move)
     256754    0.244    0.000    0.629    0.000  engine/moves/legality.py:52(is_in_check)

"""
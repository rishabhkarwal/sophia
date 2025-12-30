import sys
import os
import cProfile
import pstats
import io
import re

def setup(engine_name):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    target_dir = os.path.join(base_dir, engine_name)

    if target_dir not in sys.path: sys.path.insert(0, target_dir)
    
    print(f"Engine: {engine_name.capitalize()}")

def pretty_print(profiler, n_stats=30):
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream).sort_stats('tottime')
    stats.print_stats(n_stats)
    raw_output = stream.getvalue()

    calls_match = re.search(r"(\d+) function calls", raw_output)
    total_calls = f"{int(calls_match.group(1)):,}" if calls_match else "N/A"

    header_regex = r"ncalls\s+tottime\s+percall\s+cumtime\s+percall\s+filename:lineno\(function\)"
    match = re.search(header_regex, raw_output)

    n = 100

    print("\n" + "=" * n)
    print(f"Total Function Calls: {total_calls}")
    print("-" * n)

    print(f"{'n-calls':^15}   {'tot-time':^8}   {'per-call':^8}   {'cum-time':^8}   {'function'}")
    print("-" * n)

    if match:
        table_content = raw_output[match.end():]
        
        for line in table_content.strip().split('\n'):
            if not line.strip(): continue
            
            parts = line.split()
            if len(parts) < 6: continue
            
            ncalls = parts[0]
            tottime = parts[1]
            percall_1 = parts[2]
            cumtime = parts[3]
            
            full_path = " ".join(parts[5:])

            path_clean_match = re.search(r"((?:moves|board|search|core|uci)[\\/].+)", full_path)
            
            if path_clean_match:
                clean_path = path_clean_match.group(1).replace('\\', '/')
            else:
                clean_path = full_path

            print(f"{ncalls:^15}   {tottime:^8}   {percall_1:^8}   {cumtime:^8}   {clean_path}")
            
    print("-" * n)
    print("\n")

def run(position, time_sec):
    try:
        from engine.uci.handler import UCI
        from engine.core.move import move_to_uci
    except ImportError as e:
        print(f"ERROR: Could not import engine modules\n{e}")
        return

    uci = UCI()
    
    print(f'\n\nPosition: {position}')
    uci.handle_position(['fen'] + position.split())

    uci.engine.time_limit = int(time_sec * 1000)

    print(f'Time: {time_sec}s\n')

    profiler = cProfile.Profile()
    profiler.enable()

    best_move = uci.engine.get_best_move(uci.state)

    profiler.disable()

    if isinstance(best_move, int):
        move_str = move_to_uci(best_move)
    else:
        move_str = str(best_move)

    print(f'\nBest Move: {move_str}')
    pretty_print(profiler)

if __name__ == '__main__':
    engine_choice = sys.argv[1] if len(sys.argv) > 1 else 'sophia'

    setup(engine_choice)

    FEN = 'r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1'
    TIME_LIMIT = 100 # long enough to let JIT optimise

    run(FEN, TIME_LIMIT)

"""pypy3 profiler.py indigo"""
"""pypy3 profiler.py sophia"""


"""
Indigo

Position: r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1
Time: 100s

info depth 1 currmove e2a6 score cp 42 nodes 1662 nps 2322 time 715 hashfull 0 pv e2a6
info depth 2 currmove e2a6 score cp 42 nodes 4945 nps 3024 time 1634 hashfull 0 pv e2a6 h3g2
info depth 3 currmove e2a6 score cp 42 nodes 12683 nps 4634 time 2736 hashfull 0 pv e2a6 h3g2 f3g2
info depth 4 currmove e2a6 score cp 42 nodes 62608 nps 6421 time 9750 hashfull 2 pv e2a6 h3g2 f3g2 b4c3
info depth 5 currmove e2a6 score cp 29 nodes 148250 nps 8885 time 16683 hashfull 3 pv e2a6 b4c3 d2c3 e6d5 e1c1
info depth 6 currmove e2a6 score cp 29 nodes 311641 nps 11699 time 26638 hashfull 12 pv e2a6 b4c3 d2c3 e6d5 e1c1 h3g2
info depth 7 currmove e2a6 score cp 29 nodes 670174 nps 15615 time 42918 hashfull 19 pv e2a6 b4c3 d2c3 e6d5 e1c1 h3g2 f3g2
info string aspiration failed - 40
info nodes 2025472 nps 20206 time 100240 hashfull 63

Best Move: e2a6

====================================================================================================
Total Function Calls: 229,130,929
----------------------------------------------------------------------------------------------------
    n-calls       tot-time   per-call   cum-time   function
----------------------------------------------------------------------------------------------------
    1605401        19.006     0.000      22.417    search/evaluation.py:268(evaluate)
    3791449        18.597     0.000      19.311    board/move_exec.py:47(make_move)
    3791446        10.093     0.000      10.289    board/move_exec.py:216(unmake_move)
    6135598        8.998      0.000      8.998     moves/legality.py:12(is_square_attacked)
1744381/184292     8.296      0.000      86.760    search/search.py:311(_quiescence)
    666102         3.805      0.000      8.145     {method 'sort' of 'list' objects}
    3198435        3.273      0.000      3.397     search/ordering.py:29(_get_mvv_lva_score)
    666093         3.224      0.000      3.581     moves/generator.py:188(_gen_bishop_moves)
    666093         2.666      0.000      18.179    moves/generator.py:35(generate_pseudo_legal_moves)
    666093         2.567      0.000      3.139     moves/generator.py:62(_gen_pawn_moves)
   74433707        2.389      0.000      2.389     {method 'bit_length' of 'int' objects}
  281091/422       2.338      0.000     100.223    search/search.py:199(_alpha_beta)
    666093         2.045      0.000      2.223     moves/generator.py:205(_gen_rook_moves)
    666093         1.749      0.000      1.956     moves/generator.py:222(_gen_queen_moves)
    5615544        1.654      0.000      10.078    moves/legality.py:52(is_in_check)
    666093         1.583      0.000      1.798     moves/generator.py:151(_gen_king_moves)
   24227269        1.421      0.000      1.421     {method 'bit_count' of 'int' objects}
    666093         1.359      0.000      1.603     moves/generator.py:135(_gen_knight_moves)
   14960393        0.852      0.000      0.852     {method 'append' of 'list' objects}
   37517511        0.641      0.000      0.641     {method 'upper' of 'str' objects}
    4042699        0.404      0.000      0.404     {method 'lower' of 'str' objects}
   11169224        0.378      0.000      3.775     search/ordering.py:62(get_move_score)
    281090         0.377      0.000      0.382     board/move_exec.py:24(is_threefold_repetition)
    215382         0.375      0.000      1.212     moves/generator.py:167(_gen_castling_moves)
   11168840        0.357      0.000      0.357     moves/generator.py:27(_pack)
    7771804        0.357      0.000      3.426     search/search.py:324(<lambda>)
     76404         0.304      0.000      0.460     search/transposition.py:35(store)
    3396988        0.208      0.000      0.914     search/search.py:248(<lambda>)
    3791446        0.177      0.000      0.177     {method 'pop' of 'list' objects}
     74803         0.117      0.000      0.117     <string>:2(__init__)
----------------------------------------------------------------------------------------------------
"""

"""
Sophia

Position: r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1
Time: 100s

info depth 1 currmove e2a6 score cp 42 nodes 1389 nps 2384 time 582 hashfull 0 pv e2a6
info depth 2 currmove e2a6 score cp 42 nodes 4031 nps 2933 time 1374 hashfull 0 pv e2a6 h3g2
info depth 3 currmove e2a6 score cp 42 nodes 13058 nps 4657 time 2803 hashfull 0 pv e2a6 h3g2 f3g2
info depth 4 currmove e2a6 score cp 42 nodes 45439 nps 6589 time 6895 hashfull 2 pv e2a6 h3g2 f3g2 b4c3
info depth 5 currmove e2a6 score cp 29 nodes 120127 nps 9664 time 12429 hashfull 3 pv e2a6 b4c3 d2c3 e6d5 e1c1
info depth 6 currmove e2a6 score cp 29 nodes 246552 nps 12251 time 20124 hashfull 12 pv e2a6 b4c3 d2c3 e6d5 e1c1 h3g2
info depth 7 currmove e2a6 score cp 29 nodes 594954 nps 17856 time 33318 hashfull 20 pv e2a6 b4c3 d2c3 e6d5 e1c1 h3g2 f3g2
info depth 8 currmove e2a6 score cp 29 nodes 1131758 nps 21286 time 53167 hashfull 62 pv e2a6 b4c3 d2c3 e6d5 e1c1 h3g2 f3g2 d5e4
info string first aspiration failed - 35
info nodes 2820096 nps 28118 time 100293 hashfull 103

Best Move: e2a6

====================================================================================================
Total Function Calls: 221,650,801
----------------------------------------------------------------------------------------------------
    n-calls       tot-time   per-call   cum-time   function
----------------------------------------------------------------------------------------------------
    2130265        24.176     0.000      28.574    search/evaluation.py:137(evaluate)
2130265/550317     14.137     0.000      81.354    search/search.py:355(_quiescence)
    4420745        13.771     0.000      14.217    board/move_exec.py:49(make_move)
    5676037        9.493      0.000      9.493     moves/legality.py:17(is_square_attacked)
    4420739        6.391      0.000      6.522     board/move_exec.py:204(unmake_move)
   93743893        3.055      0.000      3.055     {method 'bit_length' of 'int' objects}
    658241         2.847      0.000      3.520     {method 'sort' of 'list' objects}
    658232         2.737      0.000      3.112     moves/generator.py:223(_gen_queen_moves)
    658232         2.583      0.000      3.219     moves/generator.py:61(_gen_pawn_moves)
  689831/433       2.558      0.000     100.269    search/search.py:243(_alpha_beta)
    658232         2.299      0.000      17.811    moves/generator.py:35(generate_pseudo_legal_moves)
   33848139        2.247      0.000      2.247     {method 'bit_count' of 'int' objects}
    5083353        2.212      0.000      10.647    moves/legality.py:57(is_in_check)
    658232         1.859      0.000      2.032     moves/generator.py:206(_gen_rook_moves)
    658232         1.648      0.000      1.924     moves/generator.py:136(_gen_knight_moves)
    658232         1.544      0.000      1.722     moves/generator.py:189(_gen_bishop_moves)
    658232         1.540      0.000      1.738     moves/generator.py:152(_gen_king_moves)
   20434695        1.191      0.000      1.191     {method 'append' of 'list' objects}
    689830         0.495      0.000      0.508     board/move_exec.py:18(is_threefold_repetition)
    3689740        0.472      0.000      0.472     search/ordering.py:34(_get_mvv_lva_score)
    186746         0.445      0.000      1.765     moves/generator.py:168(_gen_castling_moves)
    7264525        0.435      0.000      0.907     search/ordering.py:55(get_move_score)
   10288404        0.362      0.000      0.362     core/move.py:60(_pack)
    4562978        0.250      0.000      0.566     search/search.py:293(<lambda>)
    103730         0.243      0.000      0.433     search/transposition.py:35(store)
    689876         0.173      0.000      0.205     search/transposition.py:45(probe)
    101715         0.154      0.000      0.154     <string>:2(__init__)
     99819         0.132      0.000      0.179     moves/generator.py:124(_add_promotions)
    4420739        0.131      0.000      0.131     {method 'pop' of 'list' objects}
    2134212        0.129      0.000      0.129     {built-in function min}
----------------------------------------------------------------------------------------------------
"""

"""
Engine: Sophia

Position: r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1
Time: 1200s

info depth 1 currmove e2a6 score cp 42 nodes 1389 nps 2848 time 487 hashfull 0 pv e2a6
info depth 2 currmove e2a6 score cp 42 nodes 4031 nps 2429 time 1659 hashfull 0 pv e2a6 h3g2
info depth 3 currmove e2a6 score cp 42 nodes 13058 nps 4024 time 3244 hashfull 0 pv e2a6 h3g2 f3g2
info depth 4 currmove e2a6 score cp 42 nodes 45439 nps 6336 time 7171 hashfull 2 pv e2a6 h3g2 f3g2 b4c3
info depth 5 currmove e2a6 score cp 29 nodes 120127 nps 9081 time 13227 hashfull 3 pv e2a6 b4c3 d2c3 e6d5 e1c1
info depth 6 currmove e2a6 score cp 29 nodes 246552 nps 11844 time 20815 hashfull 12 pv e2a6 b4c3 d2c3 e6d5 e1c1 h3g2
info depth 7 currmove e2a6 score cp 29 nodes 594954 nps 17707 time 33599 hashfull 20 pv e2a6 b4c3 d2c3 e6d5 e1c1 h3g2 f3g2
info depth 8 currmove e2a6 score cp 29 nodes 1131758 nps 21117 time 53593 hashfull 62 pv e2a6 b4c3 d2c3 e6d5 e1c1 h3g2 f3g2 d5e4
info string first aspiration failed - 35
info depth 9 currmove e2a6 score cp -35 nodes 4103178 nps 31075 time 132037 hashfull 114 pv e2a6 b4c3 d2c3 e6d5 e5g4 e7e4 f3e4 f6e4 c3g7
info depth 10 currmove e2a6 score cp -19 nodes 7922486 nps 29919 time 264794 hashfull 314 pv e2a6 e6d5 c3d5 e7e5 d5f6 g7f6 a1b1 h3g2 f3g2 e5d6
info string first aspiration failed - 35
info depth 11 currmove e2a6 score cp -54 nodes 18960468 nps 32328 time 586488 hashfull 511 pv e2a6 e6d5 e5g6 f7g6 c3e2 d5e4 f3g3 h3g2 g3g2 c7c5
info depth 12 currmove e2a6 score cp -21 nodes 36241658 nps 31647 time 1145150 hashfull 833 pv e2a6 e6d5 e5g6 f7g6 c3e2 f6e4 e1c1 e4d2 d1d2 e7g5 g2g3

Best Move: e2a6

====================================================================================================
Total Function Calls: 3,085,417,370
----------------------------------------------------------------------------------------------------
    n-calls       tot-time   per-call   cum-time   function
----------------------------------------------------------------------------------------------------
   28720494       288.126     0.000     342.801    search/evaluation.py:137(evaluate)
   81973777       137.010     0.000     137.010    moves/legality.py:17(is_square_attacked)
   62510464       128.563     0.000     132.511    board/move_exec.py:49(make_move)
28720494/5425395   118.595     0.000     928.225    search/search.py:355(_quiescence)
   62510464        84.780     0.000      86.414    board/move_exec.py:204(unmake_move)
   10358503        43.329     0.000      51.503    {method 'sort' of 'list' objects}
  1263399493       39.260     0.000      39.260    {method 'bit_length' of 'int' objects}
   10358490        36.807     0.000      43.871    moves/generator.py:61(_gen_pawn_moves)
   10358490        35.509     0.000      39.016    moves/generator.py:206(_gen_rook_moves)
   440290811       28.553     0.000      28.553    {method 'bit_count' of 'int' objects}
   10358490        25.457     0.000     222.383    moves/generator.py:35(generate_pseudo_legal_moves)
  7521164/672      23.961     0.000     1145.124   search/search.py:243(_alpha_beta)
   10358490        22.633     0.000      25.272    moves/generator.py:223(_gen_queen_moves)
   10358490        21.718     0.000      24.136    moves/generator.py:189(_gen_bishop_moves)
   10358490        19.668     0.000      22.743    moves/generator.py:136(_gen_knight_moves)
   10358490        17.022     0.000      19.018    moves/generator.py:152(_gen_king_moves)
   72965376        16.824     0.000     138.802    moves/legality.py:57(is_in_check)
   309677361       13.176     0.000      13.176    {method 'append' of 'list' objects}
    7521164        5.831      0.000      5.952     board/move_exec.py:18(is_threefold_repetition)
    2978227        4.570      0.000      22.869    moves/generator.py:168(_gen_castling_moves)
   54057802        4.332      0.000      4.332     search/ordering.py:34(_get_mvv_lva_score)
    7521256        4.191      0.000      4.521     search/transposition.py:45(probe)
   109926880       4.053      0.000      8.385     search/ordering.py:55(get_move_score)
   70814435        4.028      0.000      7.096     search/search.py:293(<lambda>)
   158990566       3.197      0.000      3.197     core/move.py:60(_pack)
    1604441        3.195      0.000      5.187     search/transposition.py:35(store)
   62510464        1.634      0.000      1.634     {method 'pop' of 'list' objects}
    1357282        1.599      0.000      1.599     <string>:2(__init__)
   28783998        1.096      0.000      1.096     {built-in function min}
   88176083        1.077      0.000      1.077     search/search.py:380(<lambda>)
   18739744        1.074      0.000      1.074     {built-in function abs}
    145265         1.046      0.000      1.046     board/move_exec.py:29(make_null_move)
    7521164        0.738      0.000      1.372     search/syzygy.py:107(probe_wdl)
    9125697        0.724      0.000      0.724     search/transposition.py:32(_get_index)
    1663535        0.414      0.000      0.754     moves/generator.py:124(_add_promotions)
    1424058        0.339      0.000      0.339     search/ordering.py:17(store_killer)
    1929304        0.266      0.000      0.266     {built-in function max}
    145265         0.261      0.000      0.261     board/move_exec.py:43(unmake_null_move)
    1424058        0.178      0.000      0.178     search/ordering.py:26(store_history)
    372820         0.157      0.000      0.285     search/evaluation.py:114(get_mop_up_score)
    7521164        0.122      0.000      0.122     {built-in function len}
     3654          0.021      0.000      0.021     {built-in function time.time}
      14           0.006      0.000     1145.141   search/search.py:207(_search_root)
      14           0.004      0.000      0.004     uci/utils.py:1(send_command)
       1           0.001      0.001     1145.151   search/search.py:91(get_best_move)
      76           0.001      0.000      0.001     {method 'add' of 'set' objects}
       1           0.001      0.001      0.001     {method 'disable' of '_lsprof.Profiler' objects}
      12           0.001      0.000      0.005     search/search.py:52(_get_pv_line)
      672          0.000      0.000      0.001     search/search.py:214(<lambda>)
      12           0.000      0.000      0.000     {method 'join' of 'str' objects}
      88           0.000      0.000      0.000     core/move.py:63(move_to_uci)
      32           0.000      0.000      0.000     <frozen importlib._bootstrap>:198(cb)
      12           0.000      0.000      0.000     search/search.py:77(_get_cp_score)
      88           0.000      0.000      0.000     search/search.py:75(<genexpr>)
      12           0.000      0.000      0.000     search/transposition.py:57(get_hashfull)
      28           0.000      0.000      0.000     {built-in function _codecs.utf_8_encode}
      12           0.000      0.000      0.000     {method 'insert' of 'list' objects}
      12           0.000      0.000      0.000     {method 'remove' of 'list' objects}
       1           0.000      0.000      0.000     search/syzygy.py:24(get_best_move)
      32           0.000      0.000      0.000     {method 'get' of 'dict' objects}
      32           0.000      0.000      0.000     {built-in function _imp.acquire_lock}
      32           0.000      0.000      0.000     {built-in function _imp.release_lock}
       2           0.000      0.000      0.001     uci/utils.py:4(send_info_string)
----------------------------------------------------------------------------------------------------
"""
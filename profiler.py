import sys
import os
import cProfile
import pstats
import io
import re
import time

BAR_WIDTH = 100

def setup(engine_name):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    target_dir = os.path.join(base_dir, engine_name)

    if target_dir not in sys.path: sys.path.insert(0, target_dir)
    
    print(f'Engine: {target_dir}')

def pretty_print(profiler, n_stats=15):
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream).sort_stats('tottime')
    stats.print_stats(n_stats)
    raw_output = stream.getvalue()

    calls_match = re.search(r'(\d+) function calls', raw_output)
    total_calls = f'{int(calls_match.group(1)):,}' if calls_match else 'N/A'

    header_regex = r'ncalls\s+tottime\s+percall\s+cumtime\s+percall\s+filename:lineno\(function\)'
    match = re.search(header_regex, raw_output)

    print('\n' + '=' * BAR_WIDTH)
    print(f'Total Function Calls: {total_calls}')
    print('-' * BAR_WIDTH)

    print(f"{'n-calls':^15}   {'tot-time':^8}   {'per-call':^8}   {'cum-time':^8}   {'function'}")
    print('-' * BAR_WIDTH)

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
            
            full_path = ' '.join(parts[5:])

            path_clean_match = re.search(r'((?:moves|board|search|core|uci)[\\/].+)', full_path)
            
            if path_clean_match:
                clean_path = path_clean_match.group(1).replace('\\', '/')
            else:
                clean_path = full_path

            print(f'{ncalls:^15}   {tottime:^8}   {percall_1:^8}   {cumtime:^8}   {clean_path}')
            
    print('-' * BAR_WIDTH)
    print('\n')

def run(position, time_sec, engine_name):
    try:
        from engine.uci.handler import UCI
        from engine.core.move import move_to_uci
    except ImportError as e:
        print(f'ERROR: Could not import engine modules\n{e}')
        return

    uci = UCI()
    
    print(f'\n\nPosition: {position}')
    uci.handle_position(['fen'] + position.split())

    uci.engine.time_limit = int(time_sec * 1000)

    print(f'Time: {time_sec}s\n')

    profiler = cProfile.Profile()
    profiler.enable()

    t_start = time.time()
    best_move = uci.engine.get_best_move(uci.state)
    t_end = time.time()

    profiler.disable()

    elapsed = t_end - t_start
    nodes = uci.engine.nodes_searched
    nps = int(nodes / elapsed) if elapsed > 0 else 0
    depth = uci.engine.depth_reached

    if isinstance(best_move, int):
        move_str = move_to_uci(best_move)
    else:
        move_str = str(best_move)

    print('\n' + '=' * BAR_WIDTH + '\n')
    print(f'Engine: {engine_name.capitalize()}\n')

    print(f'Nodes: {nodes:,}')
    print(f'NPS:   {nps:,}')
    print(f'Time:  {elapsed:.2f}s')
    print(f'Depth: {depth}')
    print(f'Move:  {move_str}')

    pretty_print(profiler)

if __name__ == '__main__':
    engine_choice = sys.argv[1] if len(sys.argv) > 1 else 'sophia'

    setup(engine_choice)

    FEN = 'r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1'
    TIME_LIMIT = 120 # long enough to let JIT optimise

    run(FEN, TIME_LIMIT, engine_choice)

"""python profiler.py sophia"""

"""
Position: r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1
Time: 120s

info depth 1 seldepth 18 score cp 112 nodes 2392 nps 472063 time 5 hashfull 0 tbhits 0 pv d5e6
info depth 2 seldepth 18 score cp 112 nodes 5014 nps 579233 time 8 hashfull 0 tbhits 0 pv d5e6 d7e6
info string aspiration fail-low: delta = 25
info depth 3 seldepth 18 score cp 81 nodes 9196 nps 637892 time 14 hashfull 0 tbhits 0 pv d5e6 e7e6 e2a6
info depth 4 seldepth 18 score cp 81 nodes 12104 nps 630022 time 19 hashfull 0 tbhits 0 pv d5e6 e7e6 e2a6 h3g2
info string aspiration fail-low: delta = 25
info string aspiration fail-low: delta = 75
info depth 5 seldepth 20 score cp 0 nodes 31188 nps 653041 time 47 hashfull 0 tbhits 0 pv e2a6 b4c3 d2c3 e6d5 e4d5
info depth 6 seldepth 22 score cp 0 nodes 50460 nps 690446 time 73 hashfull 0 tbhits 0 pv e2a6 b4c3 d2c3 e6d5 e4d5 h3g2
info string aspiration fail-low: delta = 25
info depth 7 seldepth 22 score cp -28 nodes 117172 nps 735413 time 159 hashfull 0 tbhits 0 pv e2a6 e6d5 e1g1 h3g2 g1g2 b4c3 d2c3
info depth 8 seldepth 22 score cp -29 nodes 199835 nps 749447 time 266 hashfull 0 tbhits 0 pv e2a6 e6d5 e1g1 b4c3 d2c3 f6e4 e5c6 e4c3
info string aspiration fail-low: delta = 25
info depth 9 seldepth 26 score cp -69 nodes 489957 nps 756609 time 647 hashfull 0 tbhits 0 pv e2a6 e6d5 e1g1 h3g2 f3g2 e7e5 c3b5 d5d4 d2b4
info depth 10 seldepth 27 score cp -82 nodes 926345 nps 761550 time 1216 hashfull 0 tbhits 0 pv e2a6 b4c3 d2c3 e6d5 e1g1 d5e4 f3g3 h3g2 g3g2 d7d5
info depth 11 seldepth 29 score cp -106 nodes 1631127 nps 769390 time 2120 hashfull 0 tbhits 0 pv e2a6 b4c3 d2c3 e6d5 e1g1 d5e4 f3e2 h3g2 g1g2 f6d5 e2e4
info depth 12 seldepth 31 score cp -91 nodes 3170668 nps 776089 time 4085 hashfull 0 tbhits 0 pv d5e6 e7e6 e2a6 h3g2 f3g2 e6e5 f2f4 e5a5 c3b5 e8d8 e4e5 a5a6
info depth 13 seldepth 33 score cp -91 nodes 5779054 nps 796035 time 7259 hashfull 0 tbhits 0 pv d5e6 e7e6 e2a6 h3g2 f3g2 e6e5 f2f4 e5a5 c3b5 e8d8 e4e5 a5a6 e5f6
info string aspiration fail-low: delta = 25
info depth 14 seldepth 33 score cp -127 nodes 17903784 nps 812067 time 22047 hashfull 0 tbhits 0 pv d5e6 e7e6 e2a6 h3g2 f3g2 e6e5 f2f4 e5a5 c3b5 e8d8 e4e5 f6d5 g2g5 d8e8
info string aspiration fail-high: delta = 25
info depth 15 seldepth 36 score cp -102 nodes 30311151 nps 824773 time 36750 hashfull 0 tbhits 0 pv d5e6 e7e6 e2a6 h3g2 f3g2 e6e5 e1f1
info depth 16 seldepth 36 score cp -78 nodes 59300634 nps 832396 time 71240 hashfull 0 tbhits 0 pv d5e6

====================================================================================================

Engine: Sophia

Nodes: 100,744,192
NPS:   836,014
Time:  120.51s
Depth: 16
Move:  d5e6

====================================================================================================
Total Function Calls: 33,852
----------------------------------------------------------------------------------------------------
    n-calls       tot-time   per-call   cum-time   function
----------------------------------------------------------------------------------------------------
     33762         0.002      0.000      0.002     /opt/homebrew/Cellar/python@3.12/3.12.13_2/Frameworks/Python.framework/Versions/3.12/lib/python3.12/threading.py:601(is_set)
      23           0.001      0.000      0.001     {built-in method builtins.print}
      16           0.000      0.000      0.000     search/utils.py:55(_get_cp_score)
       1           0.000      0.000      0.000     {method 'disable' of '_lsprof.Profiler' objects}
       7           0.000      0.000      0.000     uci/utils.py:4(send_info_string)
      23           0.000      0.000      0.001     uci/utils.py:1(send_command)
      16           0.000      0.000      0.000     {built-in method builtins.abs}
       1           0.000      0.000      0.000     search/syzygy.py:24(get_best_move)
       2           0.000      0.000      0.000     {built-in method time.time}
       1           0.000      0.000      0.000     {method 'bit_count' of 'int' objects}
----------------------------------------------------------------------------------------------------
"""
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

"""pypy3 profiler.py sophia"""

"""
Position: r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1
Time: 120s

info depth 1 seldepth 23 score cp -13 nodes 7571 nps 2958 time 2558 hashfull 0 tbhits 0 pv d5e6
info depth 2 seldepth 23 score cp -13 nodes 15546 nps 4119 time 3774 hashfull 0 tbhits 0 pv d5e6 e7e6
info depth 3 seldepth 23 score cp -21 nodes 22486 nps 4751 time 4731 hashfull 0 tbhits 0 pv e2a6 b4c3 d2c3
info depth 4 seldepth 31 score cp -21 nodes 53317 nps 6187 time 8617 hashfull 0 tbhits 0 pv e2a6 b4c3 d2c3 h3g2
info string aspiration tightened: 50
info depth 5 seldepth 31 score cp -21 nodes 114304 nps 7748 time 14751 hashfull 0 tbhits 0 pv e2a6 b4c3 d2c3 h3g2 f3g2
info depth 6 seldepth 31 score cp -21 nodes 191655 nps 8812 time 21747 hashfull 0 tbhits 0 pv e2a6 b4c3 d2c3 h3g2 f3g2 e6d5
info depth 7 seldepth 31 score cp -21 nodes 261233 nps 9261 time 28206 hashfull 1 tbhits 0 pv e2a6 b4c3 d2c3 e6d5 e4d5 h3g2 f3g2
info string aspiration tightened: 50
info depth 8 seldepth 33 score cp -21 nodes 413892 nps 10907 time 37946 hashfull 4 tbhits 0 pv e2a6 b4c3 d2c3 e6d5 e4d5 h3g2 f3g2 b6d5
info depth 9 seldepth 33 score cp -70 nodes 685335 nps 12795 time 53560 hashfull 7 tbhits 0 pv e2a6 b4c3 d2c3 e6d5 e5g6 f7g6 c3f6 g7f6 f3f6
info string aspiration failed: 50
info depth 10 seldepth 33 score cp -120 nodes 1249922 nps 15651 time 79859 hashfull 19 tbhits 0 pv e2a6 b4c3 d2c3 e6d5 e5g4 d5e4 g4f6 e7f6

====================================================================================================

Engine: Sophia

Nodes: 2,134,016
NPS:   17,735
Time:  120.33s
Depth: 10
Move:  e2a6

====================================================================================================
Total Function Calls: 369,971,004
----------------------------------------------------------------------------------------------------
    n-calls       tot-time   per-call   cum-time   function
----------------------------------------------------------------------------------------------------
    1842319        21.412     0.000      33.718    search/evaluation.py:327(evaluate)
    5561083        20.021     0.000      20.738    board/move_exec.py:103(make_move)
    8032266        9.207      0.000      9.502     moves/legality.py:67(is_in_check)
 1882438/86098     8.958      0.000     103.402    search/search.py:526(_quiescence)
    5561083        8.361      0.000      8.654     board/move_exec.py:308(unmake_move)
    5560982        6.787      0.000      10.199    search/ordering.py:134(pick_next_move)
    956053         4.688      0.000      5.323     moves/generator.py:224(_gen_queen_moves)
  251578/571       4.124      0.000     120.286    search/search.py:258(_alpha_beta)
    956053         3.481      0.000      22.738    moves/generator.py:35(generate_pseudo_legal_moves)
    1842319        3.231      0.000      3.901     search/evaluation.py:159(get_pawn_hash)
   84693156        2.849      0.000      2.849     {method 'bit_length' of 'int' objects}
    956053         2.787      0.000      3.469     moves/generator.py:62(_gen_pawn_moves)
    956053         2.553      0.000      2.799     moves/generator.py:207(_gen_rook_moves)
   98467167        2.540      0.000      3.259     search/ordering.py:100(get_move_score)
    2861656        2.345      0.000      2.345     search/evaluation.py:276(evaluate_king_safety_simple)
----------------------------------------------------------------------------------------------------
"""
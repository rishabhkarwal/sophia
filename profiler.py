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

info depth 1 currmove e2a6 score cp 5 nodes 3709 nps 5191 time 714 hashfull 0 pv e2a6
info depth 2 currmove e2a6 score cp 5 nodes 7235 nps 5799 time 1247 hashfull 0 pv e2a6 b4c3
info depth 3 currmove e2a6 score cp 5 nodes 10960 nps 6358 time 1723 hashfull 0 pv e2a6 b4c3 d2c3
info string aspiration tightened: 35
info depth 4 currmove e2a6 score cp 5 nodes 59975 nps 8410 time 7131 hashfull 0 pv e2a6 b4c3 d2c3 h3g2
info depth 5 currmove e2a6 score cp 5 nodes 138650 nps 11265 time 12307 hashfull 0 pv e2a6 b4c3 d2c3 h3g2 f3g2
info depth 6 currmove e2a6 score cp 5 nodes 258322 nps 13782 time 18742 hashfull 2 pv e2a6 b4c3 d2c3 h3g2 f3g2 e6d5
info string aspiration tightened: 35
info depth 7 currmove e2a6 score cp 5 nodes 434558 nps 17057 time 25476 hashfull 4 pv e2a6 b4c3 d2c3 e6d5 e4d5 h3g2 f3g2
info string aspiration failed: 35
info depth 8 currmove e2a6 score cp -42 nodes 1080333 nps 22500 time 48014 hashfull 12 pv e2a6 b4c3 d2c3 e6d5 e5g4 h3g2 f3g2 d5e4
info depth 9 currmove e2a6 score cp -74 nodes 2064727 nps 26372 time 78289 hashfull 27 pv e2a6 b4c3 d2c3 e6d5 e5g4 d5e4 g4f6 g7f6 f3f6

====================================================================================================

Engine: Sophia

Nodes: 3,463,168
NPS:   27,402
Time:  126.38s
Depth: 9
Move:  e2a6

====================================================================================================
Total Function Calls: 271,125,164
----------------------------------------------------------------------------------------------------
    n-calls       tot-time   per-call   cum-time   function
----------------------------------------------------------------------------------------------------
    7834920        26.463     0.000      27.303    board/move_exec.py:61(make_move)
3048292/188118     15.419     0.000     111.482    search/search.py:471(_quiescence)
    7834920        11.363     0.000      11.687    board/move_exec.py:266(unmake_move)
   11742389        11.117     0.000      11.473    moves/legality.py:67(is_in_check)
    2978605        9.386      0.000      14.620    search/evaluation.py:233(evaluate)
    1448699        7.863      0.000      7.863     {method 'sort' of 'list' objects}
    1505706        5.930      0.000      6.656     moves/generator.py:224(_gen_queen_moves)
    1505706        3.898      0.000      4.216     moves/generator.py:207(_gen_rook_moves)
    1505706        3.886      0.000      29.317    moves/generator.py:35(generate_pseudo_legal_moves)
    1505706        3.756      0.000      4.562     moves/generator.py:62(_gen_pawn_moves)
  414876/517       3.190      0.000     126.321    search/search.py:273(_alpha_beta)
    2978605        3.129      0.000      3.310     search/evaluation.py:176(_evaluate_pawn_structure_fast)
    1505706        2.813      0.000      3.124     moves/generator.py:190(_gen_bishop_moves)
    1505706        2.424      0.000      2.755     moves/generator.py:153(_gen_king_moves)
    1505706        2.408      0.000      2.789     moves/generator.py:137(_gen_knight_moves)
----------------------------------------------------------------------------------------------------
"""
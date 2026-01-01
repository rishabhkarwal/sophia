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
    TIME_LIMIT = 100 # long enough to let JIT optimise

    run(FEN, TIME_LIMIT, engine_choice)

"""pypy3 profiler.py sophia"""

"""
Engine: Indigo

Nodes: 1,691,648
NPS:   16,678
Time:  101.42s
Depth: 7
Move:  e2a6

====================================================================================================
Total Function Calls: 190,602,353
----------------------------------------------------------------------------------------------------
    n-calls       tot-time   per-call   cum-time   function
----------------------------------------------------------------------------------------------------
    3199274        19.369     0.000      20.146    board/move_exec.py:47(make_move)
    1329557        18.210     0.000      21.485    search/evaluation.py:268(evaluate)
    5136675        9.398      0.000      9.398     moves/legality.py:12(is_square_attacked)
    3199270        8.899      0.000      9.063     board/move_exec.py:216(unmake_move)
1445872/165887     6.977      0.000      85.166    search/search.py:315(_quiescence)
    554260         3.983      0.000      8.719     {method 'sort' of 'list' objects}
    2646273        3.543      0.000      3.673     search/ordering.py:29(_get_mvv_lva_score)
    554251         3.483      0.000      3.787     moves/generator.py:205(_gen_rook_moves)
  245776/398       3.309      0.000     101.401    search/search.py:203(_alpha_beta)
    554251         2.768      0.000      3.428     moves/generator.py:62(_gen_pawn_moves)
    554251         2.664      0.000      19.360    moves/generator.py:35(generate_pseudo_legal_moves)
   61743955        2.292      0.000      2.292     {method 'bit_length' of 'int' objects}
    554251         1.889      0.000      2.103     moves/generator.py:222(_gen_queen_moves)
    554251         1.865      0.000      2.072     moves/generator.py:188(_gen_bishop_moves)
    554251         1.767      0.000      1.972     moves/generator.py:151(_gen_king_moves)
----------------------------------------------------------------------------------------------------
"""

"""
====================================================================================================

Engine: Sophia

Nodes: 4,595,712
NPS:   45,707
Time:  100.55s
Depth: 8
Move:  e2a6

====================================================================================================
Total Function Calls: 240,745,127
----------------------------------------------------------------------------------------------------
    n-calls       tot-time   per-call   cum-time   function
----------------------------------------------------------------------------------------------------
    3806128        30.287     0.000      36.369    search/evaluation.py:137(evaluate)
    3954690        19.821     0.000      20.573    board/move_exec.py:57(make_move)
3830156/633091     7.147      0.000      86.889    search/search.py:373(_quiescence)
    3954690        6.939      0.000      7.163     board/move_exec.py:221(unmake_move)
   106097618       3.489      0.000      3.489     {method 'bit_length' of 'int' objects}
   45741113        3.232      0.000      3.232     {method 'bit_count' of 'int' objects}
    595727         2.898      0.000      17.937    moves/generator.py:35(generate_pseudo_legal_moves)
    595727         2.850      0.000      3.134     moves/generator.py:206(_gen_rook_moves)
    595727         2.753      0.000      3.369     moves/generator.py:61(_gen_pawn_moves)
  765556/437       2.473      0.000     100.447    search/search.py:255(_alpha_beta)
    621663         2.444      0.000      2.444     moves/legality.py:18(is_square_attacked)
    595736         2.247      0.000      2.602     {method 'sort' of 'list' objects}
    595727         1.944      0.000      2.150     moves/generator.py:223(_gen_queen_moves)
    595727         1.733      0.000      1.890     moves/generator.py:189(_gen_bishop_moves)
    595727         1.621      0.000      1.895     moves/generator.py:136(_gen_knight_moves)
----------------------------------------------------------------------------------------------------
"""
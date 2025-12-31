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

    if isinstance(best_move, int):
        move_str = move_to_uci(best_move)
    else:
        move_str = str(best_move)

    print('\n' + '=' * BAR_WIDTH + '\n')
    print(f'Engine: {engine_name.capitalize()}\n')

    print(f'Nodes: {nodes:,}')
    print(f'NPS:   {nps:,}')
    print(f'Time:  {elapsed:.2f}s')
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
Engine: Previous

Nodes: 3,190,784
NPS:   31,906
Time:  100.01s
Move:  e2a6

====================================================================================================
Total Function Calls: 253,099,276
----------------------------------------------------------------------------------------------------
    n-calls       tot-time   per-call   cum-time   function
----------------------------------------------------------------------------------------------------
    2376081        25.989     0.000      30.451    search/evaluation.py:137(evaluate)
    4984029        13.558     0.000      13.970    board/move_exec.py:49(make_move)
2384826/648529     13.212     0.000      81.167    search/search.py:358(_quiescence)
    6393855        7.597      0.000      7.597     moves/legality.py:18(is_square_attacked)
    4984022        6.628      0.000      6.744     board/move_exec.py:204(unmake_move)
   104657674       3.145      0.000      3.145     {method 'bit_length' of 'int' objects}
    729431         2.875      0.000      3.536     {method 'sort' of 'list' objects}
    729422         2.852      0.000      3.223     moves/generator.py:223(_gen_queen_moves)
  805958/444       2.633      0.000      99.980    search/search.py:246(_alpha_beta)
    729422         2.621      0.000      3.165     moves/generator.py:61(_gen_pawn_moves)
   37817822        2.248      0.000      2.248     {method 'bit_count' of 'int' objects}
    729422         2.195      0.000      17.273    moves/generator.py:35(generate_pseudo_legal_moves)
    729422         1.909      0.000      2.088     moves/generator.py:206(_gen_rook_moves)
    5719047        1.700      0.000      8.487     moves/legality.py:67(is_in_check)
    729422         1.542      0.000      1.721     moves/generator.py:189(_gen_bishop_moves)
----------------------------------------------------------------------------------------------------
"""

"""
Engine: Sophia

Nodes: 3,835,904
NPS:   38,316
Time:  100.11s
Move:  e2a6

====================================================================================================
Total Function Calls: 230,144,788
----------------------------------------------------------------------------------------------------
    n-calls       tot-time   per-call   cum-time   function
----------------------------------------------------------------------------------------------------
    5740778        21.927     0.000      22.479    board/move_exec.py:49(make_move)
    2810604        15.547     0.000      18.463    search/evaluation.py:137(evaluate)
    5740770        8.047      0.000      8.193     board/move_exec.py:204(unmake_move)
    7382395        7.773      0.000      7.773     moves/legality.py:18(is_square_attacked)
2820166/827453     5.401      0.000      73.539    search/search.py:358(_quiescence)
  1015738/466      5.276      0.000     100.081    search/search.py:246(_alpha_beta)
    840911         3.849      0.000      4.195     moves/generator.py:206(_gen_rook_moves)
    840920         3.804      0.000      4.681     {method 'sort' of 'list' objects}
    840911         3.435      0.000      4.128     moves/generator.py:61(_gen_pawn_moves)
    840911         3.151      0.000      23.217    moves/generator.py:35(generate_pseudo_legal_moves)
   78297818        2.491      0.000      2.491     {method 'bit_length' of 'int' objects}
    840911         2.337      0.000      2.606     moves/generator.py:189(_gen_bishop_moves)
    840911         2.299      0.000      2.550     moves/generator.py:223(_gen_queen_moves)
    840911         2.112      0.000      2.458     moves/generator.py:136(_gen_knight_moves)
    840911         1.987      0.000      2.231     moves/generator.py:152(_gen_king_moves)
----------------------------------------------------------------------------------------------------
"""
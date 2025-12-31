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

def pretty_print(profiler, n_stats=15):
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

"""pypy3 profiler.py sophia"""



"""
Previous:

info nodes 3233792 nps 32314 time 100073 hashfull 108

====================================================================================================
Total Function Calls: 252,288,876
----------------------------------------------------------------------------------------------------
    n-calls       tot-time   per-call   cum-time   function
----------------------------------------------------------------------------------------------------
    2420389        24.532     0.000      28.990    search/evaluation.py:137(evaluate)
    5053899        13.543     0.000      13.947    board/move_exec.py:49(make_move)
2420389/654839     13.289     0.000      80.697    search/search.py:359(_quiescence)
    6481578        9.612      0.000      9.612     moves/legality.py:17(is_square_attacked)
    5053890        6.550      0.000      6.670     board/move_exec.py:204(unmake_move)
   106492973       3.142      0.000      3.142     {method 'bit_length' of 'int' objects}
    741387         3.057      0.000      3.732     {method 'sort' of 'list' objects}
    741378         2.783      0.000      3.320     moves/generator.py:61(_gen_pawn_moves)
    741378         2.780      0.000      3.148     moves/generator.py:223(_gen_queen_moves)
  813403/444       2.585      0.000     100.011    search/search.py:247(_alpha_beta)
   38506118        2.247      0.000      2.247     {method 'bit_count' of 'int' objects}
    5800889        2.225      0.000      10.815    moves/legality.py:57(is_in_check)
    741378         2.205      0.000      17.674    moves/generator.py:35(generate_pseudo_legal_moves)
    741378         1.878      0.000      2.057     moves/generator.py:206(_gen_rook_moves)
   106492973       3.142      0.000      3.142     {method 'bit_length' of 'int' objects}
----------------------------------------------------------------------------------------------------
"""

"""
Now:

info nodes 3581952 nps 35744 time 100210 hashfull 819

====================================================================================================
Total Function Calls: 267,956,918
----------------------------------------------------------------------------------------------------
    n-calls       tot-time   per-call   cum-time   function
----------------------------------------------------------------------------------------------------
    2228665        22.243     0.000      26.150    search/evaluation.py:137(evaluate)
2614507/679236     15.025     0.000      81.253    search/search.py:358(_quiescence)
    5595009        12.453     0.000      12.806    board/move_exec.py:49(make_move)
    7190149        9.327      0.000      9.327     moves/legality.py:17(is_square_attacked)
    5595004        6.612      0.000      6.713     board/move_exec.py:204(unmake_move)
    3581997        3.108      0.000      3.254     search/transposition.py:45(probe)
    817269         2.915      0.000      3.576     {method 'sort' of 'list' objects}
   103911296       2.863      0.000      2.863     {method 'bit_length' of 'int' objects}
  967445/462       2.644      0.000     100.189    search/search.py:246(_alpha_beta)
    817260         2.593      0.000      2.930     moves/generator.py:223(_gen_queen_moves)
    817260         2.572      0.000      3.077     moves/generator.py:61(_gen_pawn_moves)
    817260         2.101      0.000      16.645    moves/generator.py:35(generate_pseudo_legal_moves)
   35809438        1.915      0.000      1.915     {method 'bit_count' of 'int' objects}
    817260         1.731      0.000      1.894     moves/generator.py:206(_gen_rook_moves)
    6418738        1.631      0.000      9.999     moves/legality.py:57(is_in_check)
----------------------------------------------------------------------------------------------------
"""
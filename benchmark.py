from subprocess import Popen, PIPE
from time import time

from rich.console import Console

_console = Console()
def log(message):
    _console.log(message)

from subprocess import Popen, PIPE
from time import time

def warmup(process, seconds):
    print(f'Starting {seconds}s warm-up')
    start_time = time()

    move_time = seconds * 1000
    process.stdin.write('position startpos\n')
    process.stdin.write(f'go movetime {move_time}\n')
    process.stdin.flush()
    
    while True:
        elapsed = time() - start_time
        remaining = seconds - elapsed
        print(f'~{remaining:.1f}s left', end='\r', flush=True)
        line = process.stdout.readline()
        if line.startswith('bestmove'): break
    
    print('Warmup complete')

def benchmark(position='startpos', time_limit=5.0, engine_path='engine.bat'):

    try:
        process = Popen(
            engine_path,
            shell=True,
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE,
            text=True,
            bufsize=1
        )
    except FileNotFoundError:
        print(f"Error: Could not find '{engine_path}'")
        return

    try:
        process.stdin.write('uci\n')
        process.stdin.flush()

        while True: # engine -> gui
            line = process.stdout.readline()
            if not line: break
            if line.strip() == 'uciok': break

        warmup(process, 1) # 'warms-up' pypy JIT compiler to simulate how it'd be compiled in a real game

        if position == 'startpos': 
            process.stdin.write('position startpos\n') # gui -> engine
        else:
            process.stdin.write(f'position fen {position}\n') # gui -> engine
        
        move_time = int(time_limit * 1000)
        process.stdin.write(f'go movetime {move_time}\n') # gui -> engine
        process.stdin.flush()

        print(f'Testing Position: {position}')
        print(f'Time Limit: {time_limit}s\n')

        start_time = time()
        
        node_count = 0
        best_move = '0000'

        while True:
            line = process.stdout.readline()
            if not line: break
            line = line.strip()

            print(line) # engine -> gui

            if line.startswith('info'):
                parts = line.split()
                if 'nodes' in parts:
                    idx = parts.index('nodes')
                    if idx + 1 < len(parts):
                        node_count = int(parts[idx + 1])
            
            if line.startswith('bestmove'):
                best_move = line.split()[1]
                break
        
        end_time = time()
        duration = end_time - start_time
        
        nps = int(node_count / duration) if duration > 0 else 0

        print(f'\nBest Move: {best_move}')
        print(f'Time: {duration:.4f} seconds')
        print(f'Nodes: {node_count:,}')
        print(f'NPS: {nps:,} nodes/sec')

    except Exception as e:
        print(f'An error occurred: {e}')
    
    finally:
        if process.poll() is None:
            try:
                process.stdin.write('quit\n') # gui -> engine
                process.stdin.flush()
            except OSError:
                pass
        
        process.terminate()
        process.wait()

if __name__ == '__main__':
    fen = '5B2/1P2P2P/2P1r3/2b1p3/6p1/2K2P1k/p7/nN5B w - - 0 1'

    time_limit = 60
    benchmark(position=fen, time_limit=time_limit)

"""
Testing Position: 5B2/1P2P2P/2P1r3/2b1p3/6p1/2K2P1k/p7/nN5B w - - 0 1
Time Limit: 60s

info depth 1 currmove h7h8q score cp 1659 nodes 2657 nps 3671 time 723 hashfull 0 pv h7h8q
info depth 2 currmove h7h8q score cp 1659 nodes 4971 nps 4524 time 1098 hashfull 0 pv h7h8q h3g3
info depth 3 currmove h7h8q score cp 1659 nodes 7513 nps 5458 time 1376 hashfull 0 pv h7h8q h3g3 b7b8q
info depth 4 currmove h7h8q score cp 1659 nodes 21269 nps 8371 time 2540 hashfull 0 pv h7h8q h3g3 b7b8q c5e7
info depth 5 currmove h7h8q score cp 1584 nodes 65750 nps 12494 time 5262 hashfull 0 pv h7h8q h3g3 b7b8q a1b3 b8e5
info depth 6 currmove h7h8q score cp 1584 nodes 120232 nps 15044 time 7991 hashfull 3 pv h7h8q h3g3 b7b8q a1b3 b8e5 e6e5
info depth 7 currmove h7h8q score cp 1584 nodes 183760 nps 19172 time 9584 hashfull 5 pv h7h8q h3g3 b7b8q a1b3 b8e5 e6e5 h8e5
info depth 7 currmove h7h8q score cp 1584 nodes 183760 nps 19172 time 9584 hashfull 5 pv h7h8q h3g3 b7b8q a1b3 b8e5 e6e5 h8e5        
info depth 8 currmove h7h8q score cp 1584 nodes 451473 nps 27107 time 16655 hashfull 22 pv h7h8q h3g3 b7b8q a1b3 b8e5 e6e5 h8e5 g3h3 
info depth 9 currmove h7h8q score cp 1722 nodes 765433 nps 33195 time 23058 hashfull 30 pv h7h8q h3g3 b7b8q c5e7 f3g4 e7f8 h8f8 g3g4 f8f2
info depth 10 currmove h7h8q score cp 1723 nodes 1380113 nps 38893 time 35484 hashfull 64 pv h7h8q h3g3 b7b8q a1b3 b8e5 e6e5 h8e5 g3h3 e5h5 h3g3
info depth 11 currmove h7h8q score cp 1723 nodes 2282063 nps 45873 time 49747 hashfull 96 pv h7h8q h3g3 b7b8q a1b3 b8e5 e6e5 h8e5 g3h3 e5h5 h3g3 h5g4
info nodes 2738176 nps 45617 time 60024 hashfull 114
bestmove h7h8q

Best Move: h7h8q
Time: 60.0287 seconds
Nodes: 2,738,176
NPS: 45,614 nodes/sec
"""
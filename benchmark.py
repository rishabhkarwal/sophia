from subprocess import Popen, PIPE
from time import time

from rich.console import Console

_console = Console()
def log(message):
    _console.log(message)

from subprocess import Popen, PIPE
from time import time

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

info depth 1 currmove h7h8q score cp 1602 nodes 2799 nps 6429 time 435 hashfull 0 pv h7h8q
info depth 2 currmove h7h8q score cp 1602 nodes 4928 nps 7395 time 666 hashfull 0 pv h7h8q h3g3
info depth 3 currmove h7h8q score cp 1602 nodes 7725 nps 9098 time 849 hashfull 0 pv h7h8q h3g3 b7b8q
info depth 4 currmove h7h8q score cp 1468 nodes 32951 nps 16307 time 2020 hashfull 0 pv h7h8q h3g3 b7b8q c5d4
info depth 5 currmove h7h8q score cp 1370 nodes 79276 nps 23547 time 3366 hashfull 1 pv h7h8q h3g3 b7b8q a1b3 b8e5
info depth 6 currmove h7h8q score cp 1370 nodes 122005 nps 26006 time 4691 hashfull 3 pv h7h8q h3g3 b7b8q a1b3 b8e5 e6e5
info depth 7 currmove h7h8q score cp 1370 nodes 169962 nps 31406 time 5411 hashfull 4 pv h7h8q h3g3 b7b8q a1b3 b8e5 e6e5 h8e5
info depth 8 currmove h7h8q score cp 1370 nodes 453702 nps 45034 time 10074 hashfull 21 pv h7h8q h3g3 b7b8q a1b3 b8e5 e6e5 h8e5 g3f2
info depth 9 currmove h7h8q score cp 1432 nodes 689625 nps 55042 time 12528 hashfull 26 pv h7h8q h3g3 b7b8q a1b3 b8e5 e6e5 h8e5 g3f2 e5h2
info depth 10 currmove h7h8q score cp 1432 nodes 1324630 nps 67096 time 19742 hashfull 63 pv h7h8q h3g3 b7b8q a1b3 b8e5 e6e5 h8e5 g3f2 e5h2
info depth 11 currmove h7h8q score cp 1481 nodes 2260805 nps 79265 time 28521 hashfull 88 pv h7h8q h3g3 b7b8q a1b3 b8e5 e6e5 h8e5 g3h3 e5h5 h3g3 h5g4
info nodes 5279744 nps 87824 time 60116 hashfull 228
bestmove h7h8q

Best Move: h7h8q
Time: 60.1180 seconds
Nodes: 5,279,744
NPS: 87,823 nodes/sec

"""
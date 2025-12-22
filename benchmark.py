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
        process.stdin.write("uci\n")
        process.stdin.flush()

        while True: # engine -> gui
            line = process.stdout.readline()
            if not line: break
            if line.strip() == 'uciok': break

        if position == 'startpos': 
            process.stdin.write("position startpos\n") # gui -> engine
        else:
            process.stdin.write(f"position fen {position}\n") # gui -> engine
        
        move_time = int(time_limit * 1000)
        process.stdin.write(f"go movetime {move_time}\n") # gui -> engine
        process.stdin.flush()

        print(f'Testing Position: {position}')
        print(f'Time Limit: {time_limit}s\n')

        start_time = time()
        
        node_count = 0
        best_move = "0000"

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

        print(f"\nBest Move: {best_move}")
        print(f"Time: {duration:.4f} seconds")
        print(f"Nodes: {node_count:,}")
        print(f"NPS: {nps:,} nodes/sec")

    except Exception as e:
        print(f"An error occurred: {e}")
    
    finally:
        process.stdin.write("quit\n") # gui -> engine
        process.stdin.flush()
        process.terminate()

if __name__ == '__main__':
    fen = '8/3K4/1k6/8/8/8/7p/8 w - - 0 1'
    time_limit = 60
    benchmark(position=fen, time_limit=time_limit)

"""
Testing Position: 8/3K4/1k6/8/8/8/7p/8 w - - 0 1
Time Limit: 60s

[BEFORE] - python

    info depth 1 currmove d7e6 score cp -914 nodes 30 nps 17461 time 1 hashfull 0
    info depth 2 currmove d7e6 score cp -914 nodes 70 nps 26666 time 2 hashfull 0
    info depth 3 currmove d7d6 score cp -911 nodes 331 nps 40266 time 8 hashfull 0
    info depth 4 currmove d7d6 score cp -975 nodes 900 nps 56965 time 15 hashfull 0
    info depth 5 currmove d7d6 score cp -975 nodes 1319 nps 58134 time 22 hashfull 0
    info depth 6 currmove d7d6 score cp -987 nodes 2511 nps 64066 time 39 hashfull 0
    info depth 7 currmove d7d6 score cp -989 nodes 3893 nps 63656 time 61 hashfull 1
    info depth 8 currmove d7e6 score cp -994 nodes 12484 nps 61801 time 202 hashfull 2
    info depth 9 currmove d7e6 score cp -994 nodes 17099 nps 64808 time 263 hashfull 3
    info depth 10 currmove d7e6 score cp -998 nodes 48291 nps 71372 time 676 hashfull 8
    info depth 11 currmove d7e6 score cp -999 nodes 63445 nps 70179 time 904 hashfull 12
    info depth 12 currmove d7e6 score cp -999 nodes 83918 nps 69019 time 1215 hashfull 15
    info depth 13 currmove d7e6 score cp -999 nodes 113372 nps 70536 time 1607 hashfull 20
    info depth 14 currmove d7e6 score cp -999 nodes 177321 nps 71728 time 2472 hashfull 28
    info depth 15 currmove d7e6 score cp -1001 nodes 266342 nps 72978 time 3649 hashfull 44
    info depth 16 currmove d7e6 score cp -1015 nodes 422449 nps 74337 time 5682 hashfull 60
    info depth 17 currmove d7e6 score cp -1016 nodes 593141 nps 75672 time 7838 hashfull 77
    info depth 18 currmove d7e6 score cp -1049 nodes 978216 nps 75829 time 12900 hashfull 106
    info depth 19 currmove d7e6 score cp -1053 nodes 1375461 nps 76244 time 18040 hashfull 131
    info depth 20 currmove d7e6 score cp -1100 nodes 2226982 nps 75802 time 29378 hashfull 168
    info depth 21 currmove d7e6 score cp -1101 nodes 3172207 nps 76548 time 41440 hashfull 200
    info depth 22 currmove d7e6 score cp -1102 nodes 4116542 nps 76402 time 53879 hashfull 229
    bestmove d7e6

    Best Move: d7e6
    Time: 60.0035 seconds
    Nodes: 4,116,542
    NPS: 68,604 nodes/sec

==============================================================================================

[AFTER] - pypy

    info depth 1 currmove d7e6 score cp -914 nodes 30 nps 28378 time 1 hashfull 0
    info depth 2 currmove d7e6 score cp -914 nodes 70 nps 23163 time 3 hashfull 0
    info depth 3 currmove d7d6 score cp -911 nodes 331 nps 19830 time 16 hashfull 0
    info depth 4 currmove d7d6 score cp -975 nodes 900 nps 13602 time 66 hashfull 0
    info depth 5 currmove d7d6 score cp -975 nodes 1319 nps 12679 time 104 hashfull 0
    info depth 6 currmove d7d6 score cp -987 nodes 2511 nps 12644 time 198 hashfull 0
    info depth 7 currmove d7d6 score cp -989 nodes 3893 nps 13019 time 299 hashfull 1
    info depth 8 currmove d7e6 score cp -994 nodes 12484 nps 16739 time 745 hashfull 2
    info depth 9 currmove d7e6 score cp -994 nodes 17099 nps 17774 time 962 hashfull 3
    info depth 10 currmove d7e6 score cp -998 nodes 48291 nps 23558 time 2049 hashfull 8
    info depth 11 currmove d7e6 score cp -999 nodes 63445 nps 24939 time 2543 hashfull 12
    info depth 12 currmove d7e6 score cp -999 nodes 83918 nps 26843 time 3126 hashfull 15
    info depth 13 currmove d7e6 score cp -999 nodes 113372 nps 29378 time 3859 hashfull 20
    info depth 14 currmove d7e6 score cp -999 nodes 177321 nps 34753 time 5102 hashfull 28
    info depth 15 currmove d7e6 score cp -1001 nodes 266342 nps 40000 time 6658 hashfull 44
    info depth 16 currmove d7e6 score cp -1015 nodes 422449 nps 46974 time 8993 hashfull 60
    info depth 17 currmove d7e6 score cp -1016 nodes 593141 nps 52827 time 11227 hashfull 77
    info depth 18 currmove d7e6 score cp -1049 nodes 978216 nps 63337 time 15444 hashfull 106
    info depth 19 currmove d7e6 score cp -1053 nodes 1375461 nps 70684 time 19459 hashfull 131
    info depth 20 currmove d7e6 score cp -1100 nodes 2226982 nps 82005 time 27156 hashfull 168
    info depth 21 currmove d7e6 score cp -1101 nodes 3172207 nps 90104 time 35205 hashfull 200
    info depth 22 currmove d7e6 score cp -1102 nodes 4116542 nps 94901 time 43377 hashfull 229
    info depth 23 currmove d7e6 score cp -1151 nodes 5877417 nps 100165 time 58676 hashfull 271
    bestmove d7e6

    Best Move: d7e6
    Time: 58.6777 seconds
    Nodes: 5,877,417
    NPS: 100,164 nodes/sec
"""
import sys
import time
import traceback

from engine.board.fen_parser import load_from_fen
from engine.board.move_exec import make_move
from engine.movegen.generator import get_legal_moves
from engine.core.constants import WHITE, BLACK
from engine.search.search import SearchEngine

class UCI:
    def __init__(self):
        self.engine = SearchEngine(time_limit=1.0, debug=True)
        self.state = load_from_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")

    def run(self):
        while True:
            try:
                line = sys.stdin.readline()
                if not line: break
                line = line.strip()
                if not line: continue

                parts = line.split()
                command = parts[0]

                if command == "uci": self.handle_uci()
                elif command == "isready": print("readyok", flush=True)
                elif command == "ucinewgame": self.handle_new_game()
                elif command == "position": self.handle_position(parts[1:])
                elif command == "go": self.handle_go(parts[1:])
                elif command == "quit": break
                
            except Exception:
                continue

    def handle_uci(self):
        print("id name ChessEngine Ultimate", flush=True)
        print("id author User", flush=True)
        print("uciok", flush=True)

    def handle_new_game(self):
        self.engine = SearchEngine(time_limit=1.0, debug=True)

    def handle_position(self, args):
        moves_idx = -1
        if args[0] == "startpos":
            self.state = load_from_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
            if "moves" in args: moves_idx = args.index("moves")
        elif args[0] == "fen":
            if "moves" in args:
                moves_idx = args.index("moves")
                fen_str = " ".join(args[1:moves_idx])
            else:
                fen_str = " ".join(args[1:])
            self.state = load_from_fen(fen_str)

        if moves_idx != -1:
            moves = args[moves_idx + 1:]
            for move_str in moves:
                legal_moves = get_legal_moves(self.state)
                for legal_move in legal_moves:
                    s_move = str(legal_move).lower()
                    
                    if s_move == move_str.lower():
                        self.state = make_move(self.state, legal_move)
                        break

    def handle_go(self, args):
        wtime = None
        btime = None
        winc = 0
        binc = 0
        movetime = None

        try:
            for i in range(len(args)):
                if args[i] == "wtime": wtime = int(args[i+1])
                elif args[i] == "btime": btime = int(args[i+1])
                elif args[i] == "winc": winc = int(args[i+1])
                elif args[i] == "binc": binc = int(args[i+1])
                elif args[i] == "movetime": movetime = int(args[i+1])
        except IndexError: pass

        time_limit = 1.0 
        
        if movetime:
            time_limit = movetime / 1000.0
        elif wtime is not None and btime is not None:
            if self.state.player == WHITE:
                time_limit = (wtime / 30.0 + winc) / 1000.0
            else:
                time_limit = (btime / 30.0 + binc) / 1000.0
            time_limit = max(0.05, time_limit - 0.05)

        self.engine.time_limit = time_limit
        
        try:
            best_move = self.engine.get_best_move(self.state)
            
            if best_move:
                move_str = str(best_move)
                #if move_str == "O-O": move_str = "e1g1" if self.state.player == WHITE else "e8g8"
                #elif move_str == "O-O-O": move_str = "e1c1" if self.state.player == WHITE else "e8c8"
                print(f"bestmove {move_str}", flush=True)
            else:
                print("bestmove 0000", flush=True)
        except:
            pass
import sys
import time

from engine.board.fen_parser import load_from_fen
from engine.board.move_exec import make_move
from engine.moves.generator import get_legal_moves
from engine.core.constants import WHITE, BLACK, NAME, AUTHOR
from engine.search.search import SearchEngine
from engine.uci.utils import send_command

class UCI:
    def __init__(self, debug=False):
        self.debug = debug
        self.engine = SearchEngine(debug=self.debug)
        self.state = load_from_fen()

    def run(self):
        while True:
            try:
                line = sys.stdin.readline()
                if not line: break
                line = line.strip()
                if not line: continue

                parts = line.split()
                command = parts[0]

                if command == 'uci': self.handle_uci()
                elif command == 'isready': send_command('readyok')
                elif command == 'ucinewgame': self.handle_new_game()
                elif command == 'position': self.handle_position(parts[1:])
                elif command == 'go': self.handle_go(parts[1:])
                elif command == 'quit': break
                
            except Exception:
                continue

    def handle_uci(self):
        send_command(f'id name {NAME}')
        send_command(f'id author {AUTHOR}')
        send_command('uciok')

    def handle_new_game(self):
        self.engine = SearchEngine(debug=self.debug)

    def handle_position(self, args):
        moves_idx = -1
        if args[0] == 'startpos':
            self.state = load_from_fen('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1')
            if 'moves' in args: moves_idx = args.index('moves')
        elif args[0] == 'fen':
            if 'moves' in args:
                moves_idx = args.index('moves')
                fen_str = ' '.join(args[1:moves_idx])
            else:
                fen_str = ' '.join(args[1:])
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
        w_time = None
        b_time = None
        w_inc = 0
        b_inc = 0
        move_time = None

        try:
            for i in range(len(args)):
                if args[i] == 'wtime': w_time = int(args[i + 1])
                elif args[i] == 'btime': b_time = int(args[i + 1])
                elif args[i] == 'winc': w_inc = int(args[i + 1])
                elif args[i] == 'binc': b_inc = int(args[i + 1])
                elif args[i] == 'movetime': move_time = int(args[i + 1])
        except IndexError: pass

        time_limit = 1000 
        
        if move_time: time_limit = move_time

        elif w_time is not None and b_time is not None:
            # rule of 30
            if self.state.player == WHITE: time_limit = (w_time / 30.0 + w_inc)
            else: time_limit = (b_time / 30.0 + b_inc)
            
            # safety
            time_limit = max(50, time_limit - 50)

        self.engine.time_limit = time_limit
        
        try:
            best_move = self.engine.get_best_move(self.state)
            
            move_str = str(best_move) if best_move else '0000'
            send_command(f'bestmove {move_str}')

        except:
            pass
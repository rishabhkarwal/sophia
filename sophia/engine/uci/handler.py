import sys
import time

from engine.board.fen_parser import load_from_fen
from engine.board.move_exec import make_move
from engine.moves.generator import get_legal_moves
from engine.core.constants import WHITE, BLACK, NAME, AUTHOR
from engine.search.search import SearchEngine
from engine.uci.utils import send_command, send_info_string
from engine.core.move import move_to_uci
from engine.search.book import OpeningBook

class UCI:
    def __init__(self):
        self.engine = SearchEngine()
        self.state = load_from_fen()
        self.book = OpeningBook()

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
                import traceback
                send_info_string(f"error: {traceback.format_exc()}")
                continue

    def handle_uci(self):
        send_command(f'id name {NAME}')
        send_command(f'id author {AUTHOR}')
        send_command('uciok')

    def handle_new_game(self):
        # clear tables but keep JIT warm
        self.engine.tt.clear()
        self.engine.ordering.clear()
        self.engine.pawn_hash = type(self.engine.pawn_hash)(16) # reset pawn hash
        self.state.history = []

    def handle_position(self, args):
        moves_idx = -1
        if args[0] == 'startpos':
            fen_str = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
            if 'moves' in args: moves_idx = args.index('moves')
        elif args[0] == 'fen':
            if 'moves' in args:
                moves_idx = args.index('moves')
                fen_str = ' '.join(args[1:moves_idx])
            else:
                fen_str = ' '.join(args[1:])
        else: return

        try:
            self.state = load_from_fen(fen_str)
        except ValueError:
            send_info_string(f"error parsing fen: {fen_str}")
            return

        if moves_idx != -1:
            moves = args[moves_idx + 1:]
            for move_str in moves:
                legal_moves = get_legal_moves(self.state)
                for legal_move in legal_moves:
                    
                    s_move = move_to_uci(legal_move)
                    
                    if s_move == move_str.lower():
                        make_move(self.state, legal_move)
                        break

    def handle_go(self, args):
        book_move = self.book.get_move(self.state)
        if book_move:
            send_info_string(f"found book move: {book_move}")
            send_command(f'bestmove {book_move}')
            return

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

        time_limit = 2000
        
        # track opponent time for time pressure tactics
        opponent_time = b_time if self.state.is_white else w_time
        if opponent_time is None: opponent_time = 999999

        if move_time: 
            time_limit = move_time
        elif w_time is not None and b_time is not None:
            my_time = w_time if self.state.is_white else b_time
            my_inc = w_inc if self.state.is_white else b_inc
            
            # estimate remaining moves
            moves_played = self.state.fullmove_number
            remaining_moves_est = max(20, 60 - moves_played)
            
            # time allocation
            time_limit = (my_time / remaining_moves_est) + (my_inc * 0.7)
            
            # panic mode: if we have less than 10 seconds, play much faster
            if my_time < 10000:
                time_limit = my_time / 5
                
            # network / execution overhead
            overhead = 200
            time_limit = max(30, time_limit - overhead)

        self.engine.time_limit = int(time_limit)
        
        try:
            best_move = self.engine.get_best_move(self.state, opponent_time)
            
            if isinstance(best_move, str):
                move_str = best_move
            elif best_move is not None:
                move_str = move_to_uci(best_move)
            else:
                move_str = '0000'

            send_command(f'bestmove {move_str}')

        except Exception as e:
            send_info_string(f"error: {e}")
            import traceback
            send_info_string(traceback.format_exc())
            send_command(f'bestmove 0000')
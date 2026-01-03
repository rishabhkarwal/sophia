import sys
import traceback
import time

from engine.board.fen_parser import load_from_fen
from engine.board.move_exec import make_move, is_repetition
from engine.moves.generator import get_legal_moves
from engine.moves.legality import is_in_check
from engine.core.constants import NAME, AUTHOR
from engine.search.search import SearchEngine
from engine.uci.utils import send_command, send_info_string
from engine.core.move import move_to_uci
from engine.search.book import OpeningBook

# Import the new test suite
from engine.uci.tests import evaluate, perft, draw, win_percentage, move_accuracy

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

                self.parse_input(line.split())
                
            except Exception:
                send_info_string(f"error: {traceback.format_exc()}")
                continue

    def parse_input(self, parts):
        command = parts[0]

        # standard UCI commands
        if command == 'uci': return self.handle_uci()
        elif command == 'isready': return send_command('readyok')
        elif command == 'ucinewgame': return self.handle_new_game()
        elif command == 'position': return self.handle_position(parts[1:])
        elif command == 'go': return self.handle_go(parts[1:])
        elif command == 'quit': sys.exit()
        
        # custom debug commands
        elif command == 'd': return draw(self.state)
        elif command == 'eval': return evaluate(self.state)
        elif command == 'perft': return perft(self.state, int(parts[1]) if len(parts) > 1 else 1)
        elif command == 'win': return win_percentage(self.state)
        elif command == 'acc': return move_accuracy(self.state, parts[1] if len(parts) > 1 else '0000')
        elif command == 'play': return self.handle_play()

    def handle_play(self):
        """Self-play loop"""
        w_time, b_time = 10000, 10000 # 10 seconds each
        
        send_info_string(f"starting self-play")
        uci_draw = 'd'.split()
        self.parse_input(uci_draw)

        while True:
            if self.state.halfmove_clock >= 100: 
                send_info_string('draw: 50-move rule')
                break
                
            threefold, fivefold = is_repetition(self.state)
            if threefold: send_info_string('draw: threefold repetition'); break
            elif fivefold: send_info_string('draw: fivefold repetition'); break
                
            uci_go = f'go wtime {int(w_time)} btime {int(b_time)}'.split()
            
            is_white = self.state.is_white
            engine_time = w_time if is_white else b_time
            start_time = time.time()
            
            result = self.parse_input(uci_go)
            
            if not result or not result.startswith('bestmove'):
                send_info_string("error: engine did not return a move")
                break
                
            best_move_str = result.replace('bestmove ', '').strip()

            elapsed = (time.time() - start_time) * 1000
            engine_time -= elapsed

            if engine_time <= 0:
                winner = "black" if is_white else "white"
                send_info_string(f"time: {winner} wins")
                break

            if best_move_str == '0000':
                if is_in_check(self.state, is_white):
                    winner = "black" if is_white else "white"
                    send_info_string(f"checkmate: {winner} wins")
                else:
                    send_info_string("draw: stalemate")
                break

            legal_moves = get_legal_moves(self.state)
            found = False
            for move in legal_moves:
                if move_to_uci(move) == best_move_str:
                    make_move(self.state, move)
                    found = True
                    break
            
            if not found:
                send_info_string(f"error: engine played illegal move {best_move_str}")
                break

            self.parse_input(uci_draw)

    def handle_go(self, args):
        book_move = self.book.get_move(self.state)
        if book_move:
            send_info_string(f"found book move: {book_move}")
            response = f'bestmove {book_move}'
            send_command(response)
            return response

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
            response = f'bestmove {move_str}'
            send_command(response)
            return response

        except Exception as e:
            send_info_string(f"error: {e}")
            send_info_string(traceback.format_exc())
            response = 'bestmove 0000'
            send_command(response)
            return response

    def handle_uci(self):
        send_command(f'id name {NAME}')
        send_command(f'id author {AUTHOR}')
        send_command('uciok')

    def handle_new_game(self):
        self.engine.tt.clear()
        self.engine.ordering.clear()
        self.engine.pawn_hash = type(self.engine.pawn_hash)(16)
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
                    if move_to_uci(legal_move) == move_str.lower():
                        make_move(self.state, legal_move)
                        break
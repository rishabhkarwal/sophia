import sys
import traceback
import time
import copy
import threading

from engine.board.fen_parser import load_from_fen
from engine.board.move_exec import make_move, is_repetition
from engine.moves.generator import get_legal_moves
from engine.moves.legality import is_in_check
from engine.core.constants import NAME, AUTHOR, INFINITE_TIME
from engine.search.search import SearchEngine
from engine.uci.utils import send_command, send_info_string
from engine.core.move import move_to_uci
from engine.search.book import OpeningBook

from engine.uci.tests import (
    evaluate, perft, draw, win_percentage, move_accuracy,
    legal_moves, see, eval_breakdown, debug_toggle, debug_eval_toggle, order_moves,
    history_top, tt_stats,
)

class UCI:
    def __init__(self):
        self.engine = SearchEngine()
        self.state = load_from_fen()
        self.book = OpeningBook()

        self._ponder_thread = None
        self._ponder_best_move = None
        self._ponder_result_lock = threading.Lock()
        self._ponder_bestmove_sent = False

        # args saved from go ponder so ponderhit can reuse them
        self._ponder_go_args = None

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
        if command == 'uci': self.handle_uci()
        elif command == 'isready': send_command('readyok')
        elif command == 'ucinewgame': self.handle_new_game()
        elif command == 'position': self.handle_position(parts[1:])
        elif command == 'go': self.handle_go(parts[1:])
        elif command == 'stop': self.handle_stop()
        elif command == 'ponderhit': self.handle_ponderhit()
        elif command == 'quit': sys.exit()

        # custom debug commands
        elif command == 'd':      draw(self.state)
        elif command == 'eval':   evaluate(self.state)
        elif command == 'perft':  perft(self.state, int(parts[1]) if len(parts) > 1 else 1)
        elif command == 'win':    win_percentage(self.state)
        elif command == 'acc':    move_accuracy(self.state, parts[1] if len(parts) > 1 else '0000')
        elif command == 'legal':  legal_moves(self.state)
        elif command == 'see':    see(self.state, parts[1] if len(parts) > 1 else '0000')
        elif command == 'evalb':    eval_breakdown(self.state)
        elif command == 'dbg':      debug_toggle()
        elif command == 'dbgeval':  debug_eval_toggle()
        elif command == 'order':  order_moves(self.state)
        elif command == 'hist':   history_top(self.engine.ordering)
        elif command == 'ttstats': tt_stats(self.engine.tt)

    def _compute_time_limit(self, args):
        """Parse go args and return (time_limit_ms, opponent_time_ms, depth_limit, nodes_limit, is_movetime, is_ponder)."""
        w_time = None
        b_time = None
        w_inc = 0
        b_inc = 0
        move_time = None
        depth_limit = None
        nodes_limit = None
        is_ponder = False

        try:
            for i in range(len(args)):
                token = args[i]
                if token == 'wtime': w_time = int(args[i + 1])
                elif token == 'btime': b_time = int(args[i + 1])
                elif token == 'winc': w_inc = int(args[i + 1])
                elif token == 'binc': b_inc = int(args[i + 1])
                elif token == 'movetime': move_time = int(args[i + 1])
                elif token == 'depth': depth_limit = int(args[i + 1])
                elif token == 'nodes': nodes_limit = int(args[i + 1])
                elif token == 'ponder': is_ponder = True
        except IndexError: pass

        opponent_time = b_time if self.state.is_white else w_time
        if opponent_time is None: opponent_time = INFINITE_TIME

        time_limit = 2000

        if move_time:
            time_limit = move_time
        elif w_time is not None and b_time is not None:
            my_time = w_time if self.state.is_white else b_time
            my_inc = w_inc if self.state.is_white else b_inc

            moves_played = self.state.fullmove_number
            remaining_moves_est = max(20, 50 - moves_played)

            time_limit = (my_time / remaining_moves_est) + (my_inc * 0.5)

            if my_time < 10000:
                time_limit = my_time / 5

            overhead = 200
            time_limit = max(overhead, min(time_limit - overhead, my_time - overhead))
        elif depth_limit is not None or nodes_limit is not None:
            time_limit = INFINITE_TIME

        return int(time_limit), opponent_time, depth_limit, nodes_limit, (move_time is not None), is_ponder

    def _run_ponder_search(self, search_state, opponent_time):
        self.engine.time_limit = INFINITE_TIME

        try:
            best_move = self.engine.get_best_move(search_state, opponent_time, None, None, False)

            if isinstance(best_move, str): move_str = best_move
            elif best_move is not None: move_str = move_to_uci(best_move)
            else: move_str = '0000'

            ponder_suffix = ''
            if move_str != '0000' and self.engine.ponder_move:
                ponder_suffix = f' ponder {self.engine.ponder_move}'

            with self._ponder_result_lock:
                self._ponder_best_move = move_str
                if not self._ponder_bestmove_sent:
                    self._ponder_bestmove_sent = True
                    send_command(f'bestmove {move_str}{ponder_suffix}')

        except Exception as e:
            send_info_string(f"error in ponder: {e}")
            send_info_string(traceback.format_exc())
            with self._ponder_result_lock:
                self._ponder_best_move = '0000'
                if not self._ponder_bestmove_sent:
                    self._ponder_bestmove_sent = True
                    send_command('bestmove 0000')

    def handle_go(self, args):
        time_limit, opponent_time, depth_limit, nodes_limit, is_movetime, is_ponder = self._compute_time_limit(args)

        if not is_ponder:
            book_move = self.book.get_move(self.state)
            if book_move:
                ponder_suffix = ''
                try:
                    ponder_state = copy.deepcopy(self.state)
                    legal = get_legal_moves(ponder_state)
                    for lm in legal:
                        if move_to_uci(lm) == book_move:
                            make_move(ponder_state, lm)
                            break
                    ponder_book_move = self.book.get_move(ponder_state)
                    if ponder_book_move:
                        ponder_suffix = f' ponder {ponder_book_move}'
                except Exception:
                    pass
                send_command(f'bestmove {book_move}{ponder_suffix}')
                return

        self.engine.stop_flag.clear()

        if is_ponder:
            self._ponder_go_args = args
            self._ponder_best_move = None
            self._ponder_bestmove_sent = False
            search_state = copy.deepcopy(self.state)

            self._ponder_thread = threading.Thread(
                target=self._run_ponder_search,
                args=(search_state, opponent_time),
                daemon=True,
            )
            self._ponder_thread.start()
        else:
            self._ponder_thread = None
            search_state = copy.deepcopy(self.state)
            self.engine.time_limit = time_limit
            try:
                best_move = self.engine.get_best_move(search_state, opponent_time, depth_limit, nodes_limit, is_movetime)

                if isinstance(best_move, str): move_str = best_move
                elif best_move is not None: move_str = move_to_uci(best_move)
                else: move_str = '0000'

                ponder_suffix = ''
                if move_str != '0000' and self.engine.ponder_move:
                    ponder_suffix = f' ponder {self.engine.ponder_move}'

                send_command(f'bestmove {move_str}{ponder_suffix}')

            except Exception as e:
                send_info_string(f"error: {e}")
                send_info_string(traceback.format_exc())
                send_command('bestmove 0000')

    def handle_ponderhit(self):
        if self._ponder_thread is None or not self._ponder_thread.is_alive():
            return  # thread already finished, bestmove already sent

        args = self._ponder_go_args or []
        time_limit, opponent_time, depth_limit, nodes_limit, is_movetime, _ = self._compute_time_limit(args)

        # update limits directly, _check_time reads these on every node
        self.engine.time_limit = time_limit
        soft = time_limit / 1000.0
        if is_movetime:
            self.engine.hard_time_limit = soft
            self.engine.soft_time_limit = soft
        else:
            self.engine.hard_time_limit = min(soft * 1.5, time_limit / 1000.0 + 0.5)
            self.engine.soft_time_limit = soft

        self.engine.start_time = time.time()  # reset so limits apply from now not from ponder start

    def handle_stop(self):
        if self._ponder_thread is not None:
            self.engine.stop_flag.set()
            self._ponder_thread.join(timeout=2.0)
            self._ponder_thread = None

            with self._ponder_result_lock:
                already_sent = self._ponder_bestmove_sent
                if not already_sent:
                    self._ponder_bestmove_sent = True
                    move_str = self._ponder_best_move or '0000'

            if not already_sent:
                send_command(f'bestmove {move_str}')
        else:
            self.engine.stop_flag.set()

    def handle_uci(self):
        send_command(f'id name {NAME}')
        send_command(f'id author {AUTHOR}')
        send_command('option name Ponder type check default false')
        send_command('uciok')

    def handle_new_game(self):
        if self._ponder_thread is not None and self._ponder_thread.is_alive():
            self.engine.stop_flag.set()
            self._ponder_thread.join(timeout=2.0)
            self._ponder_thread = None
        self.engine.stop_flag.clear()
        self._ponder_bestmove_sent = True  # suppress any bestmove from a thread that outlived the game
        self.engine.tt.clear()
        self.engine.ordering.clear()
        self.engine.pawn_hash = type(self.engine.pawn_hash)(16)
        self.state = load_from_fen()

    def handle_position(self, args):
        if not args: return

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

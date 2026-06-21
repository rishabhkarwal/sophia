import sys
import traceback
import time
import threading

from engine.board.fen_parser import load_from_fen
from engine.board.move_exec import make_move, is_repetition
from engine.moves.generator import get_legal_moves
from engine.moves.legality import is_in_check
from engine.core.constants import (
    NAME, AUTHOR, INFINITE_TIME,
)
from engine.core.parameters import (
    DEFAULT_TIME_LIMIT, MOVES_TO_GO_MIN, MOVES_TO_GO_LOOKBACK,
    INCREMENT_FRACTION, LOW_TIME_THRESHOLD, LOW_TIME_DIVISOR,
    MOVE_OVERHEAD, PONDERHIT_HARD_FACTOR, PONDERHIT_HARD_OFFSET,
)
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
        self._ponder_lock = threading.Lock()
        # result stored by _run_ponder; emitted only by ponderhit/stop
        self._ponder_result = None
        self._ponder_args = None
        self._ponder_time_limit = None

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

        if command == 'uci': self.handle_uci()
        elif command == 'isready': send_command('readyok')
        elif command == 'ucinewgame': self.handle_new_game()
        elif command == 'position': self.handle_position(parts[1:])
        elif command == 'go': self.handle_go(parts[1:])
        elif command == 'stop': self.handle_stop()
        elif command == 'ponderhit': self.handle_ponderhit()
        elif command == 'quit': sys.exit()

        elif command == 'd':       draw(self.state)
        elif command == 'eval':    evaluate(self.state)
        elif command == 'perft':   perft(self.state, int(parts[1]) if len(parts) > 1 else 1)
        elif command == 'win':     win_percentage(self.state)
        elif command == 'acc':     move_accuracy(self.state, parts[1] if len(parts) > 1 else '0000')
        elif command == 'legal':   legal_moves(self.state)
        elif command == 'see':     see(self.state, parts[1] if len(parts) > 1 else '0000')
        elif command == 'evalb':   eval_breakdown(self.state)
        elif command == 'dbg':     debug_toggle()
        elif command == 'dbgeval': debug_eval_toggle()
        elif command == 'order':   order_moves(self.state)
        elif command == 'hist':    history_top(self.engine.ordering)
        elif command == 'ttstats': tt_stats(self.engine.tt)

    def _compute_time_limit(self, args):
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

        time_limit = DEFAULT_TIME_LIMIT

        if move_time:
            time_limit = move_time
        elif w_time is not None and b_time is not None:
            my_time = w_time if self.state.is_white else b_time
            my_inc = w_inc if self.state.is_white else b_inc

            moves_played = self.state.fullmove_number
            remaining_moves_est = max(MOVES_TO_GO_MIN, MOVES_TO_GO_LOOKBACK - moves_played)

            time_limit = (my_time / remaining_moves_est) + (my_inc * INCREMENT_FRACTION)

            if my_time < LOW_TIME_THRESHOLD:
                time_limit = my_time / LOW_TIME_DIVISOR

            overhead = MOVE_OVERHEAD
            time_limit = max(overhead, min(time_limit - overhead, my_time - overhead))
        elif depth_limit is not None or nodes_limit is not None:
            time_limit = INFINITE_TIME

        return int(time_limit), opponent_time, depth_limit, nodes_limit, (move_time is not None), is_ponder

    def _stop_ponder(self):
        """signal ponder thread to stop and wait for it; does NOT emit bestmove"""
        if self._ponder_thread is not None:
            if self._ponder_thread.is_alive():
                self.engine.stop_flag.set()
                self._ponder_thread.join(timeout=5.0)
            self._ponder_thread = None
        self._ponder_args = None
        self._ponder_time_limit = None

    def _book_ponder(self, state, book_move_uci, legal_moves_list):
        """look up book move for the position after uci is played"""
        try:
            ponder_state = state.clone()
            for lm in legal_moves_list:
                if move_to_uci(lm) == book_move_uci:
                    make_move(ponder_state, lm)
                    break
            result = self.book.get_move(ponder_state)
            if result:
                return result[0]
        except Exception:
            pass
        return None

    def _get_book_bestmove(self, state):
        book_result = self.book.get_move(state)
        if not book_result: return None

        book_move, book_pct, book_nodes, book_ms = book_result
        legal_moves_list = get_legal_moves(state)
        legal_ucis = {move_to_uci(lm) for lm in legal_moves_list}

        if book_move not in legal_ucis: return None

        book_nps = max(1, int(book_nodes / (book_ms / 1000)))
        ponder_move = self._book_ponder(state, book_move, legal_moves_list)
        ponder_suffix = f' ponder {ponder_move}' if ponder_move else ''

        return book_move, ponder_suffix, book_pct, book_nodes, book_ms, book_nps

    def _run_ponder(self, search_state, opponent_time):
        """background ponder search — stores result but does NOT emit bestmove"""
        try:
            best_move = self.engine.get_best_move(search_state, opponent_time, None, None, False)

            if isinstance(best_move, str): move_str = best_move
            elif best_move is not None: move_str = move_to_uci(best_move)
            else: move_str = '0000'

            ponder_suffix = ''
            if move_str != '0000' and self.engine.ponder_move:
                ponder_suffix = f' ponder {self.engine.ponder_move}'

            with self._ponder_lock:
                self._ponder_result = (move_str, ponder_suffix)

        except Exception as e:
            send_info_string(f"ponder error: {e}")
            with self._ponder_lock:
                self._ponder_result = ('0000', '')

    def handle_go(self, args):
        time_limit, opponent_time, depth_limit, nodes_limit, is_movetime, is_ponder = self._compute_time_limit(args)

        # stop any in-flight ponder; discard its result (it was for the wrong position)
        self._stop_ponder()
        self.engine.stop_flag.clear()
        with self._ponder_lock:
            self._ponder_result = None

        if is_ponder:
            book_bestmove = self._get_book_bestmove(self.state)
            if book_bestmove:
                book_move, ponder_suffix, book_pct, book_nodes, book_ms, book_nps = book_bestmove
                send_command(f'info score cp {book_pct} depth 1 nodes {book_nodes} time {book_ms} nps {book_nps} pv {book_move}')

                with self._ponder_lock:
                    self._ponder_result = (book_move, ponder_suffix)

                self._ponder_args = args
                self._ponder_time_limit = time_limit
                return

            # start infinite search in background; ponderhit will apply the real time limit
            self._ponder_args = args
            self._ponder_time_limit = time_limit
            search_state = self.state.clone()

            self.engine.time_limit = INFINITE_TIME
            self._ponder_thread = threading.Thread(
                target=self._run_ponder,
                args=(search_state, opponent_time),
                daemon=True,
            )

            self._ponder_thread.start()
            return

        # normal go — book first, then search
        book_bestmove = self._get_book_bestmove(self.state)

        if book_bestmove:
            book_move, ponder_suffix, book_pct, book_nodes, book_ms, book_nps = book_bestmove
            send_command(f'info score cp {book_pct} depth 1 nodes {book_nodes} time {book_ms} nps {book_nps} pv {book_move}')

            send_command(f'bestmove {book_move}{ponder_suffix}')
            return

        # search
        search_state = self.state.clone()
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
        """opponent played the predicted move — apply real time limit and wait for result"""
        args = self._ponder_args or []
        computed_time_limit, _, _, _, is_movetime, _ = self._compute_time_limit(args)
        time_limit = self._ponder_time_limit if self._ponder_time_limit is not None else computed_time_limit

        if self._ponder_thread is not None and self._ponder_thread.is_alive():
            # search still running — apply the real time limit
            self.engine.time_limit = time_limit
            self.engine.limit_start_time = time.time()
            soft = time_limit / 1000.0
            if is_movetime:
                self.engine.soft_time_limit = soft
                self.engine.hard_time_limit = soft
            else:
                self.engine.soft_time_limit = soft
                self.engine.hard_time_limit = min(soft * PONDERHIT_HARD_FACTOR, soft + PONDERHIT_HARD_OFFSET)

            # wait for the search to finish and emit its result
            self._ponder_thread.join(timeout=max(time_limit / 1000.0 + 2.0, 5.0))
            self._ponder_thread = None

        self._ponder_args = None
        self._ponder_time_limit = None

        # emit stored result (either from completed search or just-finished search above)
        with self._ponder_lock:
            result = self._ponder_result
            self._ponder_result = None

        if result:
            move_str, ponder_suffix = result
            send_command(f'bestmove {move_str}{ponder_suffix}')
        else:
            send_command('bestmove 0000')

    def handle_stop(self):
        """stop whatever is running"""
        if self._ponder_thread is not None and self._ponder_thread.is_alive():
            self.engine.stop_flag.set()
            self._ponder_thread.join(timeout=5.0)
            self._ponder_thread = None

            self._ponder_args = None
            self._ponder_time_limit = None

            with self._ponder_lock:
                result = self._ponder_result
                self._ponder_result = None

            if result:
                move_str, ponder_suffix = result
                send_command(f'bestmove {move_str}{ponder_suffix}')
            else:
                send_command('bestmove 0000')
        elif self._ponder_args is not None:
            self._ponder_args = None
            self._ponder_time_limit = None

            with self._ponder_lock:
                result = self._ponder_result
                self._ponder_result = None

            if result:
                move_str, ponder_suffix = result
                send_command(f'bestmove {move_str}{ponder_suffix}')
            else:
                send_command('bestmove 0000')
        else:
            self.engine.stop_flag.set()

    def handle_uci(self):
        send_command(f'id name {NAME}')
        send_command(f'id author {AUTHOR}')
        send_command('option name Ponder type check default false')
        send_command('uciok')

    def handle_new_game(self):
        self._stop_ponder()
        self.engine.stop_flag.clear()
        with self._ponder_lock:
            self._ponder_result = None
        self._ponder_args = None
        self._ponder_time_limit = None
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
                legal_moves_list = get_legal_moves(self.state)
                for legal_move in legal_moves_list:
                    if move_to_uci(legal_move) == move_str.lower():
                        make_move(self.state, legal_move)
                        break

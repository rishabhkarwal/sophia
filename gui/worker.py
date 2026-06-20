import chess
import chess.pgn
import datetime
import time
import io

from gui.engine import Wrapper
from gui.types import GameAssignment, GameUpdate, GameResult

# set by pool initializer — avoids pickling issues
_update_queue = None

def _init_worker(q):
    global _update_queue
    _update_queue = q

def play_game(assignment: GameAssignment) -> GameResult:
    a = assignment
    tc_str = f"{a.time_control}+{a.increment}"

    if a.white_is_engine_1:
        w_path, w_name = a.engine_1_path, a.engine_1_name
        b_path, b_name = a.engine_2_path, a.engine_2_name
    else:
        w_path, w_name = a.engine_2_path, a.engine_2_name
        b_path, b_name = a.engine_1_path, a.engine_1_name

    engine_w = None
    engine_b = None

    try:
        engine_w = Wrapper(w_path, quiet=True)
        engine_b = Wrapper(b_path, quiet=True)
        engine_w.start()
        engine_b.start()

        board = chess.Board(a.starting_fen) if a.starting_fen else chess.Board()

        engine_w._send_cmd('ucinewgame')
        engine_b._send_cmd('ucinewgame')

        w_time = float(a.time_control)
        b_time = float(a.time_control)

        result_text = ''
        termination = 'Unknown'

        ponder_state = {}

        while not result_text:
            if board.is_game_over():
                result_text = board.result()
                if board.is_checkmate(): termination = 'Checkmate'
                elif board.is_stalemate(): termination = 'Stalemate'
                elif board.is_insufficient_material(): termination = 'Insufficient Material'
                elif board.is_seventyfive_moves(): termination = '75 Move Rule'
                elif board.is_fivefold_repetition(): termination = 'Fivefold Repetition'
                else: termination = 'Draw'
                break

            is_white = board.turn == chess.WHITE
            engine = engine_w if is_white else engine_b
            opponent = engine_b if is_white else engine_w

            w_ms = int(w_time * 1000)
            b_ms = int(b_time * 1000)
            inc_ms = int(a.increment * 1000)

            turn_start = time.time()

            ponderhit = False
            ponder_predicted_move = ponder_state.pop(engine, None)
            if ponder_predicted_move is not None:
                current_move_uci = board.peek().uci() if board.move_stack else None
                if current_move_uci == ponder_predicted_move:
                    engine._send_cmd(f'ponderhit')
                    ponderhit = True
                else:
                    engine._send_cmd('stop')
                    _drain_bestmove(engine)
                    _sync_engine(engine)
                    engine._send_cmd(f'position fen {board.fen()}')
                    engine._send_cmd(f'go wtime {w_ms} btime {b_ms} winc {inc_ms} binc {inc_ms}')
            else:
                engine._send_cmd(f'position fen {board.fen()}')
                engine._send_cmd(f'go wtime {w_ms} btime {b_ms} winc {inc_ms} binc {inc_ms}')

            if ponderhit:
                turn_start = time.time()

            best_move_str = None
            ponder_move_str = None
            while True:
                try:
                    line = engine.process.stdout.readline()
                except OSError:
                    break
                if not line:
                    break
                line = line.strip()
                if line.startswith('bestmove'):
                    parts = line.split()
                    if len(parts) >= 2:
                        best_move_str = parts[1]
                    if len(parts) >= 4 and parts[2] == 'ponder':
                        ponder_move_str = parts[3]
                    break

            elapsed = time.time() - turn_start

            if is_white:
                w_time = max(0, w_time - elapsed + a.increment)
            else:
                b_time = max(0, b_time - elapsed + a.increment)

            time_left = w_time if is_white else b_time
            if time_left <= 0 and a.time_control > 0:
                result_text = '0-1' if is_white else '1-0'
                termination = 'Time Forfeit'
                break

            if best_move_str:
                try:
                    move = chess.Move.from_uci(best_move_str)
                    if move in board.legal_moves:
                        board.push(move)
                    else:
                        result_text = '0-1' if is_white else '1-0'
                        termination = f'Illegal Move ({best_move_str})'
                        break
                except ValueError:
                    result_text = '0-1' if is_white else '1-0'
                    termination = f'Invalid UCI ({best_move_str})'
                    break
            else:
                result_text = '0-1' if is_white else '1-0'
                termination = 'Engine Crash'
                break

            if ponder_move_str and engine.supports_ponder and not board.is_game_over():
                w_ms2 = int(w_time * 1000)
                b_ms2 = int(b_time * 1000)
                # position must include ponder move as last move, not the fen after it
                engine._send_cmd(f'position fen {board.fen()} moves {ponder_move_str}')
                engine._send_cmd(f'go ponder wtime {w_ms2} btime {b_ms2} winc {inc_ms} binc {inc_ms}')
                ponder_state[engine] = ponder_move_str
                if not engine.quiet:
                    from gui.console import log_info
                    log_info(f'[ponder] started: engine={engine.name} predicting={ponder_move_str}')

            _send_update(a.game_id, len(board.move_stack), board.fen(),
                         w_time, b_time, w_name, b_name, 'playing', None)

        # clean up any active ponder
        for pondering_engine in list(ponder_state):
            try:
                pondering_engine._send_cmd('stop')
                _drain_bestmove(pondering_engine)
                _sync_engine(pondering_engine)
            except Exception:
                pass

        _send_update(a.game_id, len(board.move_stack), board.fen(),
                     w_time, b_time, w_name, b_name, 'completed', result_text)

        pgn_string = _build_pgn(board, w_name, b_name, result_text,
                                termination, a.game_id, tc_str, a.starting_fen)

        return GameResult(
            game_id=a.game_id, white_name=w_name, black_name=b_name,
            result=result_text, termination=termination, pgn_string=pgn_string,
            moves=len(board.move_stack), time_control=tc_str, error=None
        )

    except Exception as e:
        _send_update(a.game_id, 0, '', 0, 0, w_name, b_name, 'completed', '*')
        return GameResult(
            game_id=a.game_id, white_name=w_name, black_name=b_name,
            result='*', termination='Engine Crash', pgn_string='',
            moves=0, time_control=tc_str, error=str(e)
        )

    finally:
        if engine_w: engine_w.stop()
        if engine_b: engine_b.stop()


def _drain_bestmove(engine, timeout=3.0):
    import select
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            ready = select.select([engine.process.stdout], [], [], max(0, deadline - time.time()))
            if not ready[0]: break
            line = engine.process.stdout.readline()
            if not line: break
            if line.strip().startswith('bestmove'): break
        except OSError:
            break


def _sync_engine(engine, timeout=1.0):
    import select
    engine._send_cmd('isready')
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            ready = select.select([engine.process.stdout], [], [], max(0, deadline - time.time()))
            if not ready[0]: break
            line = engine.process.stdout.readline()
            if not line: break
            if line.strip() == 'readyok': return True
        except OSError:
            break
    return False


def _send_update(game_id, move_num, fen, w_time, b_time, w_name, b_name, status, result):
    if _update_queue is None:
        return
    try:
        _update_queue.put_nowait(GameUpdate(
            game_id=game_id, move_number=move_num, fen=fen,
            w_time=w_time, b_time=b_time,
            white_name=w_name, black_name=b_name,
            status=status, result=result
        ))
    except Exception:
        pass


def _build_pgn(board, white, black, result, termination, round_num, tc_str, starting_fen):
    game = chess.pgn.Game()
    game.headers['Event'] = 'Engine Tournament'
    game.headers['Site'] = 'Local'
    game.headers['Date'] = datetime.datetime.now().strftime('%Y.%m.%d')
    game.headers['Round'] = str(round_num)
    game.headers['White'] = white
    game.headers['Black'] = black
    game.headers['Result'] = result
    game.headers['Termination'] = termination
    game.headers['TimeControl'] = tc_str

    if starting_fen and starting_fen != chess.STARTING_FEN:
        game.headers['FEN'] = starting_fen
        game.headers['SetUp'] = '1'

    game.add_line(board.move_stack)

    output = io.StringIO()
    print(game, file=output)
    return output.getvalue()

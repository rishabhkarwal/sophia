import threading
import time
import chess
import chess.engine

# path to the stockfish binary; none disables the eval bar entirely
STOCKFISH_PATH = "/opt/homebrew/bin/stockfish"


def _find_stockfish(path: str) -> str | None:
    """return path if the binary exists"""
    import shutil
    import subprocess
    candidate = path or shutil.which("stockfish")
    if not candidate:
        return None
    try:
        proc = subprocess.Popen(
            [candidate],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        proc.stdin.write(b"quit\n")
        proc.stdin.flush()
        proc.wait(timeout=2)
        return candidate
    except Exception:
        return None


class Evaluator:
    """continuously polls stockfish for the current position's eval"""

    def __init__(self, path: str = STOCKFISH_PATH, time_per_move: float = 0.08):
        resolved = _find_stockfish(path)
        if resolved is None:
            self.available = False
            self.current_cp = 0
            self.current_mate = None
            return

        self.available = True
        self._time_per_move = time_per_move
        self._board: chess.Board = chess.Board()
        self._pending_board: chess.Board | None = None
        self._lock = threading.Lock()
        self.current_cp: int = 0
        self.current_mate: int | None = None
        self.current_bestmove: chess.Move | None = None
        self.current_bestmove_fen: str = ""
        self._running = True

        try:
            self._engine = chess.engine.SimpleEngine.popen_uci(resolved)
        except Exception:
            self.available = False
            return

        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def update_position(self, board: chess.Board):
        if not self.available:
            return
        with self._lock:
            self._pending_board = board.copy()

    def _loop(self):
        last_fen = None
        while self._running:
            with self._lock:
                if self._pending_board is not None:
                    self._board = self._pending_board
                    self._pending_board = None

            fen = self._board.fen()
            if fen != last_fen:
                try:
                    info = self._engine.analyse(
                        self._board,
                        chess.engine.Limit(time=self._time_per_move),
                    )
                    pov = info["score"].white()
                    self.current_mate = pov.mate()
                    cp = pov.score(mate_score=10000)
                    self.current_cp = cp if cp is not None else self.current_cp
                    pv = info.get("pv")
                    self.current_bestmove = pv[0] if pv else None
                    self.current_bestmove_fen = fen
                    last_fen = fen
                except Exception:
                    pass
            else:
                time.sleep(0.02)

    def quit(self):
        if not self.available:
            return
        self._running = False
        try:
            self._engine.quit()
        except Exception:
            pass

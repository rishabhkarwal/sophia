import queue
import subprocess
import threading
import time

import chess

STOCKFISH_PATH = "/opt/homebrew/bin/stockfish"


def _find_stockfish(path):
    import shutil
    candidate = path or shutil.which("stockfish")
    if not candidate: return None
    try:
        proc = subprocess.Popen(
            [candidate],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True,
        )
        proc.stdin.write("quit\n")
        proc.stdin.flush()
        proc.wait(timeout=2)
        return candidate
    except Exception:
        return None


class Snapshot:
    """one atomic eval result so the gui never mixes fields from different positions; fen guards every field against the board being drawn"""
    def __init__(self, cp=0, mate=None, best=None, depth=0, fen=None):
        self.cp = cp
        self.mate = mate
        self.best = best
        self.depth = depth
        self.fen = fen


class Evaluator:
    """live stockfish analysis that never blocks the gui — reader thread owns stdout, worker thread runs stop -> position -> go infinite per position"""
    def __init__(self, path=STOCKFISH_PATH):
        self.snap = Snapshot()

        resolved = _find_stockfish(path)
        if resolved is None:
            self.available = False
            return

        try:
            self.process = subprocess.Popen(
                [resolved],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, bufsize=1,
            )
        except Exception:
            self.available = False
            return

        self.stopped = False
        self.lines = queue.Queue()
        self.reader = threading.Thread(target=self._read_loop, daemon=True)
        self.reader.start()

        self._send("uci")
        if not self._await("uciok"):
            self.available = False
            return
        self._send("isready")
        self._await("readyok")

        self.available = True
        self.generation = 0
        self.requests = queue.SimpleQueue()
        self.wake = threading.Event()
        self.worker = threading.Thread(target=self._worker, daemon=True)
        self.worker.start()

    def _read_loop(self):
        # sole owner of stdout — blocking readline avoids the select() vs
        # buffered-text-IO race that silently drops lines
        try:
            for line in self.process.stdout:
                if self.stopped: break
                self.lines.put(line.strip())
        except Exception:
            pass

    def _await(self, token, timeout=5.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                line = self.lines.get(timeout=max(0.0, deadline - time.time()))
            except queue.Empty:
                return False
            if line == token: return True
        return False

    def _send(self, cmd):
        self.process.stdin.write(f"{cmd}\n")
        self.process.stdin.flush()

    def _latest(self):
        latest = None
        try:
            while True: latest = self.requests.get_nowait()
        except queue.Empty:
            pass
        return latest

    def _drain_to_readyok(self):
        # a bestmove after stop is delayed/unreliable; readyok is the ordered
        # boundary — discarding to it stops an old search's lines leaking into
        # the next one (which showed stale arrows)
        self._send("isready")
        deadline = time.time() + 2.0
        while time.time() < deadline:
            try:
                line = self.lines.get(timeout=max(0.0, deadline - time.time()))
            except queue.Empty:
                return
            if line == "readyok": return

    def _worker(self):
        while not self.stopped:
            self.wake.wait()
            self.wake.clear()
            if self.stopped: return

            req = self._latest()
            if req is None: continue
            fen, gen = req

            self._send("stop")
            self._drain_to_readyok()
            self._send(f"position fen {fen}")
            self._send("go infinite")
            self._search(fen, gen)

    def _search(self, fen, gen):
        while not self.stopped:
            # a newer position arrived — abandon this search; the worker loop
            # will stop it and start the new one
            if gen != self.generation: self.wake.set(); return

            try:
                line = self.lines.get(timeout=0.1)
            except queue.Empty:
                continue

            if not line.startswith("info ") or " pv " not in line: continue

            depth, cp, mate, best = self._parse(line)
            if depth is None: continue
            if cp is None: cp = self.snap.cp
            snap = Snapshot(cp, mate, best, depth, fen)
            # re-check as late as possible so we never overwrite the snapshot of
            # a position the gui has already moved on to
            if gen != self.generation: return
            self.snap = snap

    def _parse(self, line):
        tokens = line.split()
        depth = cp = mate = best = None
        i = 0
        n = len(tokens)
        while i < n:
            tok = tokens[i]
            if tok == "depth" and i + 1 < n:
                try:
                    depth = int(tokens[i + 1])
                except ValueError:
                    pass
                i += 2
            elif tok == "score" and i + 2 < n:
                kind, val = tokens[i + 1], tokens[i + 2]
                try:
                    if kind == "cp": cp = int(val)
                    elif kind == "mate": mate = int(val); cp = 10000 if mate > 0 else -10000
                except ValueError:
                    pass
                i += 3
            elif tok == "pv" and i + 1 < n:
                try:
                    best = chess.Move.from_uci(tokens[i + 1])
                except ValueError:
                    pass
                i += 2
            else:
                i += 1
        return depth, cp, mate, best

    def update_position(self, board):
        if not self.available: return
        self.generation += 1
        self.snap = Snapshot(fen=board.fen())
        self.requests.put((board.fen(), self.generation))
        self.wake.set()

    def quit(self):
        if not self.available: return
        self.stopped = True
        self.wake.set()
        try:
            self._send("quit")
        except Exception:
            pass
        try:
            self.process.terminate()
        except Exception:
            pass

from gui.console import log_error, log_info, log_engine, log_gui, Colour
import os, sys, subprocess, time

class Wrapper:
    def __init__(self, path: str, version : str = '', console_colour=Colour.RESET, quiet=False):
        self.path = os.path.abspath(path)
        self.name = path.split('/')[0] # folder name of engine
        if version != '': self.name += '.' + version
        self.process = None
        self.score = 0
        self.wins = 0
        self.draws = 0
        self.losses = 0
        self.colour = console_colour
        self.quiet = quiet

    def start(self):
        if not os.path.exists(self.path):
            raise RuntimeError(f'Could not find engine file at: {self.path}')

        try:
            self.process = subprocess.Popen(
                self.path,
                shell=True,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )

            if self.process.poll() is not None:
                raise RuntimeError(f'Engine {self.name} failed during startup')

            self._send_cmd('uci')
            if not self._wait_for('uciok'):
                raise RuntimeError(f'Engine {self.name} failed UCI handshake')

        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"Error starting engine {self.name}: {e}")

    def stop(self):
        if self.process:
            try:
                self._send_cmd('quit')
                self.process.terminate()
            except:
                pass

    def _send_cmd(self, cmd):
        if self.process and self.process.poll() is None:
            try:
                if not self.quiet: log_gui(f"{cmd} -> {self.name}")
                self.process.stdin.write(f'{cmd}\n')
                self.process.stdin.flush()
            except OSError:
                if not self.quiet: log_error(f"Error sending command '{cmd}'")

    def _wait_for(self, target_text):
        if not self.process: return False
        while True:
            try:
                line = self.process.stdout.readline()
                if not line: return False
                line = line.strip()
                if not self.quiet: log_engine(self.name, line, self.colour)
                if target_text in line: return True
            except OSError:
                return False

    def get_best_move(self, fen: str, wtime: int, btime: int, winc: int, binc: int) -> str:
        if self.process.poll() is not None: return None

        self._send_cmd(f'position fen {fen}')
        self._send_cmd(f'go wtime {wtime} btime {btime} winc {winc} binc {binc}')
        
        while True:
            try:
                line = self.process.stdout.readline()
            except OSError:
                return None

            if not line: return None
            line = line.strip()
            
            if line.startswith('info'):
                if not self.quiet: log_engine(self.name, line, self.colour)

            if line.startswith('bestmove'):
                if not self.quiet: log_engine(self.name, line, self.colour + Colour.BOLD)
                if not self.quiet: print("")
                parts = line.split()
                if len(parts) >= 2:
                    return parts[1]
                return None
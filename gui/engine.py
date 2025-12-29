from gui.console import log_error
import os, sys, subprocess, time

class Wrapper:
    def __init__(self, path: str, version : str = ''):
        self.path = os.path.abspath(path)
        self.name = path.split('/')[0]
        if version != '': self.name += '.' + version
        self.process = None
        self.score = 0

    def start(self):
        if not os.path.exists(self.path):
            log_error(f'Could not find engine file at: {self.path}')
            sys.exit(1)

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
            
            time.sleep(0.1) 
            if self.process.poll() is not None:
                log_error(f'Error during startup')
                sys.exit(1)

            self._send_cmd('uci')
            if not self._wait_for('uciok'):
                log_error(f'Error during UCI handshake')
                sys.exit(1)

        except Exception as e:
            log_error(f"Error starting engine {self.name}: {e}")
            sys.exit(1)

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
                self.process.stdin.write(f'{cmd}\n')
                self.process.stdin.flush()
            except OSError:
                log_error(f"Error sending command '{cmd}'")
        else:
            pass

    def _wait_for(self, target_text):
        if not self.process: return False
        
        while True:
            try:
                line = self.process.stdout.readline()
            except OSError:
                return False

            if not line: return False
            
            if target_text in line: return True

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
            
            if line.startswith('bestmove'):
                parts = line.split()
                if len(parts) >= 2:
                    return parts[1]
                return None
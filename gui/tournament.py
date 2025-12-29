from gui.config import Config
from gui.engine import Wrapper
from gui.console import log, log_error, log_info
from gui.graphics import Display

import chess, time

class Tournament:
    def __init__(self, config: Config):
        self.cfg = config
    
        self.engine_1 = Wrapper(self.cfg.engine_1_path, 'v1')
        self.engine_2 = Wrapper(self.cfg.engine_2_path, 'v2')

    def run(self):
        self.engine_1.start()
        self.engine_2.start()
        log_info('Initialised engines')

        try:
            for i in range(1, self.cfg.total_games + 1):
                self._play_game(i)
        except KeyboardInterrupt:
            log_info('Tournament stopped')
        finally:
            self.engine_1.stop()
            self.engine_2.stop()
            self._print_final_results()

    def _play_game(self, game_number: int):
        board = chess.Board()
        
        if game_number & 1:
            white, black = self.engine_1, self.engine_2
        else:
            white, black = self.engine_2, self.engine_1

        w_time = self.cfg.time_control
        b_time = self.cfg.time_control
        
        white._send_cmd("ucinewgame")
        black._send_cmd("ucinewgame")
        
        game_over = False
        result_text = ""
        
        while not game_over:
            Display.clear_screen()
            Display.print_board(board)
            Display.print_stats(self.engine_1, self.engine_2, game_number, self.cfg.total_games, w_time, b_time)
            log_info(f'Moves: {Display._format_history(board)}')

            if board.is_game_over():
                game_over = True
                break

            is_white = (board.turn == chess.WHITE)
            current_engine = white if is_white else black
            
            w_ms = int(w_time * 1000)
            b_ms = int(b_time * 1000)
            inc_ms = int(self.cfg.increment * 1000)
            
            start_ts = time.time()
            best_move_str = current_engine.get_best_move(board.fen(), w_ms, b_ms, inc_ms, inc_ms)
            elapsed = time.time() - start_ts

            if is_white:
                w_time = max(0, w_time - elapsed + self.cfg.increment)
                if w_time <= 0 and self.cfg.time_control > 0:
                    result_text = "0-1 (Timeout)"
                    game_over = True
            else:
                b_time = max(0, b_time - elapsed + self.cfg.increment)
                if b_time <= 0 and self.cfg.time_control > 0:
                    result_text = "1-0 (Timeout)"
                    game_over = True
            
            if not game_over:
                if best_move_str:
                    try:
                        move = chess.Move.from_uci(best_move_str)
                        if move in board.legal_moves:
                            board.push(move)
                        else:
                            result_text = f"Illegal Move ({best_move_str})"
                            game_over = True
                    except ValueError:
                        result_text = f"Invalid Format ({best_move_str})"
                        game_over = True
                else:
                    result_text = "Engine Crashed/Resigned"
                    game_over = True
        

        if not result_text:
            result_text = board.result()
        
        log_info(result_text)

        time.sleep(3)
        
        self._update_score(result_text, white, black)

    def _update_score(self, result: str, white, black):
        w_points = 0.0
        b_points = 0.0
        
        if "1-0" in result: w_points = 1.0
        elif "0-1" in result: b_points = 1.0
        elif "1/2" in result: 
            w_points = 0.5
            b_points = 0.5
            
        if white == self.engine_1:
            self.engine_1.score += w_points
            self.engine_2.score += b_points
        else:
            self.engine_2.score += w_points
            self.engine_1.score += b_points

    def _print_final_results(self):
        Display.clear_screen()
        print("╔══════════════════════════════════════╗")
        print("║          TOURNAMENT RESULTS          ║")
        print("╠══════════════════════════════════════╣")
        print(f"║  {self.engine_1.name}: {self.engine_1.score:<24} ║")
        print(f"║  {self.engine_2.name}: {self.engine_2.score:<24} ║")
        print("╚══════════════════════════════════════╝")
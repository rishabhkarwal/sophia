from gui.config import Config
from gui.engine import Wrapper
from gui.console import log, log_error, log_info, Colour
from gui.graphics import GUI

import chess
import chess.pgn
import datetime
import time
import threading
import queue
import os

class Tournament:
    def __init__(self, config: Config):
        self.cfg = config
        self.gui = GUI()
        
        os.system('cls || clear')

        self.engine_1 = Wrapper(self.cfg.engine_1_path, console_colour=Colour.BLUE)
        self.engine_2 = Wrapper(self.cfg.engine_2_path, console_colour=Colour.MAGENTA)

    def run(self):
        self.engine_1.start()
        self.engine_2.start()
        log_info('Initialised engines')

        try:
            for i in range(1, self.cfg.total_games + 1):
                self._play_game(i)
                time.sleep(5)
        except KeyboardInterrupt:
            log_info('Tournament stopped')
        finally:
            self.engine_1.stop()
            self.engine_2.stop()
            self.gui.quit()
            self._print_final_results()

    def _play_game(self, game_number: int):
        board = chess.Board()
        
        if game_number & 1: white_engine, black_engine = self.engine_1, self.engine_2
        else: white_engine, black_engine = self.engine_2, self.engine_1

        w_time = self.cfg.time_control
        b_time = self.cfg.time_control
        
        white_engine._send_cmd("ucinewgame")
        black_engine._send_cmd("ucinewgame")
        
        game_over = False
        result_text = ""
        termination_reason = "Normal"
        move_queue = queue.Queue()

        while not game_over:
            if board.is_game_over():
                game_over = True
                termination_reason = "Rule Variation"
                break

            is_white = (board.turn == chess.WHITE)
            current_engine = white_engine if is_white else black_engine
            
            w_ms = int(w_time * 1000)
            b_ms = int(b_time * 1000)
            inc_ms = int(self.cfg.increment * 1000)

            search_thread = threading.Thread(
                target=self._search_task,
                args=(current_engine, board.fen(), w_ms, b_ms, inc_ms, move_queue),
                daemon=True
            )
            search_thread.start()
            
            turn_start_time = time.time()
            best_move_str = None

            while search_thread.is_alive():
                now = time.time()
                elapsed = now - turn_start_time

                w_disp = w_time - elapsed if is_white else w_time
                b_disp = b_time - elapsed if not is_white else b_time
                
                if (is_white and w_disp <= 0) or (not is_white and b_disp <= 0):
                    if self.cfg.time_control > 0:
                        result_text = "0-1" if is_white else "1-0"
                        termination_reason = "Time Forfeit"
                        game_over = True
                        break 

                self.gui.handle_events()

                self.gui.draw(
                    board, white_engine, black_engine, 
                    game_number, self.cfg.total_games, 
                    w_disp, b_disp, result_text
                )
                time.sleep(0.05) 

            if game_over: break

            if not move_queue.empty(): best_move_str = move_queue.get()

            real_elapsed = time.time() - turn_start_time

            time_left = (w_time if is_white else b_time) - real_elapsed
            
            if time_left <= 0 and self.cfg.time_control > 0:
                result_text = "0-1" if is_white else "1-0"
                termination_reason = "Time Forfeit"
                game_over = True
            else:
                # time is good, update clock and process move
                if is_white: w_time = max(0, time_left + self.cfg.increment)
                else: b_time = max(0, time_left + self.cfg.increment)

                if best_move_str:
                    try:
                        move = chess.Move.from_uci(best_move_str)
                        if move in board.legal_moves: board.push(move)
                        else:
                            result_text = "0-1" if is_white else "1-0"
                            termination_reason = f"Illegal Move ({best_move_str})"
                            game_over = True
                    except ValueError:
                        result_text = "0-1" if is_white else "1-0"
                        termination_reason = f"Invalid UCI ({best_move_str})"
                        game_over = True
                else:
                    result_text = "0-1" if is_white else "1-0"
                    termination_reason = "Engine Crash"
                    game_over = True
        
        if not result_text: result_text = board.result()
        
        if termination_reason == "Rule Variation": 
            if board.is_checkmate(): termination_reason = "Checkmate"
            elif board.is_stalemate(): termination_reason = "Stalemate"
            elif board.is_insufficient_material(): termination_reason = "Insufficient Material"
            elif board.is_seventyfive_moves(): termination_reason = "75 Moves Rule"
            elif board.is_fivefold_repetition(): termination_reason = "Fivefold Repetition"
            else: termination_reason = "Draw"

        log_info(f"Game Over: {result_text} ({termination_reason})")
        self._update_score(result_text, white_engine, black_engine)
        
        self._save_pgn(board, white_engine, black_engine, result_text, termination_reason, game_number)

        end_time = time.time()
        while time.time() - end_time < 1: 
            self.gui.handle_events()
            self.gui.draw(board, white_engine, black_engine, game_number, self.cfg.total_games, w_time, b_time, result_text)

    def _save_pgn(self, board, white, black, result, termination, round_num):
        try:
            game = chess.pgn.Game()
            
            game.headers["Event"] = "Engine Tournament"
            game.headers["Site"] = "Local"
            game.headers["Date"] = datetime.datetime.now().strftime("%Y.%m.%d")
            game.headers["Round"] = str(round_num)
            game.headers["White"] = white.name
            game.headers["Black"] = black.name
            game.headers["Result"] = result
            game.headers["Termination"] = termination
            game.headers["TimeControl"] = f"{self.cfg.time_control}+{self.cfg.increment}"

            game.add_line(board.move_stack)

            with open(self.cfg.pgn_path, "a", encoding="utf-8") as f:
                f.write(str(game) + "\n\n")
                
            log_info(f"Game saved to {self.cfg.pgn_path}")
        except Exception as e:
            log_error(f"Failed to save PGN: {e}")

    def _search_task(self, engine, fen, w, b, inc, q):
        try:
            move = engine.get_best_move(fen, w, b, inc, inc)
            q.put(move)
        except Exception:
            q.put(None)

    def _update_score(self, result: str, white, black):
        w_points = 0.0
        b_points = 0.0
        
        if "1-0" in result: 
            w_points = 1.0
            white.wins += 1
            black.losses += 1
        elif "0-1" in result: 
            b_points = 1.0
            black.wins += 1
            white.losses += 1
        elif "1/2" in result: 
            w_points = 0.5
            b_points = 0.5
            white.draws += 1
            black.draws += 1
            
        white.score += w_points
        black.score += b_points

    def _print_final_results(self):
        print("\n" + "="*40)
        print(f" {self.engine_1.name}: {self.engine_1.score}")
        print(f" {self.engine_2.name}: {self.engine_2.score}")
        print("="*40 + "\n")
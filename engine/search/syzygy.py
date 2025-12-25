import chess
import chess.syzygy
import os
import random
from engine.search.utils import state_to_board
from engine.core.constants import WHITE, BLACK
from engine.uci.utils import send_info_string

class SyzygyHandler:
    def __init__(self, file_path="syzygy"):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.path = os.path.join(current_dir, file_path)

        self.tablebase = None
        
        if os.path.exists(self.path):
            try:
                self.tablebase = chess.syzygy.open_tablebase(self.path)
                send_info_string(f"found syzygy tablebase in '{file_path}'")
            except Exception as e: send_info_string(f"syzygy error: {e}")
        else:
            send_info_string(f"syzygy tablebase NOT found in '{file_path}'")

    def get_best_move(self, state):
        if not self.tablebase: return None

        all_pieces = state.bitboards[WHITE] | state.bitboards[BLACK]
        if all_pieces.bit_count() > 5: return None 

        try: board = state_to_board(state)
        except Exception: return None

        try: current_wdl = self.tablebase.probe_wdl(board)
        except chess.syzygy.MissingTableError: return None

        if current_wdl is None: return None

        try: root_dtz = self.tablebase.probe_dtz(board)
        except: root_dtz = 0

        best_move = None
        best_dtz = float('inf')
        
        moves = list(board.legal_moves)
        random.shuffle(moves)

        for move in moves:
            # if winning, avoid repeating positions 
            if current_wdl > 0 and board.is_repetition(3): continue

            board.push(move)
            
            if board.is_checkmate():
                board.pop()
                return (move.uci(), 2, 0) 

            if board.is_game_over():
                result_wdl = 0 
                result_dtz = 0
            else:
                try:
                    result_wdl = self.tablebase.probe_wdl(board)
                    result_dtz = self.tablebase.probe_dtz(board)
                except:
                    board.pop()
                    continue
            
            board.pop()

            if result_wdl is None or result_dtz is None: continue

            # winning (WDL > 0)
            if current_wdl > 0:
                if result_wdl < 0:
                    is_zeroing = board.is_capture(move) or move.piece_type == chess.PAWN

                    move_dtz = abs(result_dtz)
                    
                    if is_zeroing: move_dtz = 0 

                    if move_dtz < best_dtz:
                        best_dtz = move_dtz
                        best_move = move

            # draw (WDL = 0)
            elif current_wdl == 0:
                if result_wdl == 0:
                    best_move = move
                    break 

            # losing (WDL < 0)
            elif current_wdl < 0:
                # if we must lose, make it take as long as possible: maximise DTZ
                if result_wdl > 0:
                    move_dtz = abs(result_dtz)

                    if best_dtz == float('inf'): best_dtz = -1
                    
                    if move_dtz > best_dtz:
                        best_dtz = move_dtz
                        best_move = move

        if best_move: return (best_move.uci(), current_wdl, root_dtz)
            
        return None

    def probe_wdl(self, state):
        if not self.tablebase: return None
        all_pieces = state.bitboards[WHITE] | state.bitboards[BLACK]
        if all_pieces.bit_count() > 5: return None
        try:
            board = state_to_board(state)
            return self.tablebase.probe_wdl(board)
        except: return None

    def probe_dtz(self, state):
        if not self.tablebase: return None
        all_pieces = state.bitboards[WHITE] | state.bitboards[BLACK]
        if all_pieces.bit_count() > 5: return None
        try:
            board = state_to_board(state)
            return self.tablebase.probe_dtz(board)
        except: return None

    def close(self):
        if self.tablebase: self.tablebase.close()
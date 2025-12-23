import chess
import chess.syzygy
import os
import random
from engine.search.utils import state_to_board
from engine.core.constants import ALL_PIECES
from engine.uci.utils import send_info_string

class SyzygyHandler:
    def __init__(self, file_path="syzygy"):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.path = os.path.join(current_dir, file_path)

        self.tablebase = None
        
        if os.path.exists(self.path):
            try:
                self.tablebase = chess.syzygy.open_tablebase(self.path)
                send_info_string(f"syzygy tablebase found @ {file_path}")
            except Exception as e: send_info_string(f"syzygy error: {e}")
        else:
            send_info_string(f"syzygy tablebase NOT found @ {file_path}")

    def get_best_move(self, state):
        if not self.tablebase: return None

        if state.bitboards['all'].bit_count() > 5: return None # currently has tablebase for 3-4-5


        try: board = state_to_board(state)
        except Exception: return None

        try: 
            current_wdl = self.tablebase.probe_wdl(board)
        except chess.syzygy.MissingTableError: 
            return None

        if current_wdl is None: return None

        try: root_dtz = self.tablebase.probe_dtz(board)
        except: root_dtz = 0

        best_move = None
        best_dtz = float('inf')
        max_dtz = -1

        moves = list(board.legal_moves)
        random.shuffle(moves)

        for move in moves:
            # if winning: don't draw
            if current_wdl > 0 and board.is_repetition(3): continue

            board.push(move)
            try:
                outcome_wdl = self.tablebase.probe_wdl(board)
                outcome_dtz = self.tablebase.probe_dtz(board)
            except:
                board.pop()
                continue
            board.pop()

            if outcome_wdl is None or outcome_dtz is None: continue

            # winning: find move that leads to fastest conversion (lowest DTZ)
            if current_wdl > 0:
                if outcome_wdl == -2 or outcome_wdl == -1: # opponent is losing
                    if abs(outcome_dtz) < best_dtz:
                        best_dtz = abs(outcome_dtz)
                        best_move = move
            
            # drawing: maintain the draw
            elif current_wdl == 0:
                if outcome_wdl == 0:
                    best_move = move
                    break

            # losing: delay the loss as long as possible (highest DTZ)
            elif current_wdl < 0:
                if outcome_wdl == 2 or outcome_wdl == 1:
                    if abs(outcome_dtz) > max_dtz:
                        max_dtz = abs(outcome_dtz)
                        best_move = move

        if best_move: return (best_move.uci(), current_wdl, root_dtz)
            
        return None

    def probe_wdl(self, state):
        if not self.tablebase: return None
        
        if state.bitboards['all'].bit_count() > 5: return None

        try:
            board = state_to_board(state)
            return self.tablebase.probe_wdl(board)
        except: return None

    def probe_dtz(self, state):
        """Returns DTZ score for the current state"""
        if not self.tablebase: return None
        
        if state.bitboards['all'].bit_count() > 5: return None

        try:
            board = state_to_board(state)
            return self.tablebase.probe_dtz(board)
        except: 
            return None

    def close(self):
        if self.tablebase:
            self.tablebase.close()
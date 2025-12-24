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
                send_info_string(f"found syzygy tablebase in {file_path}")
            except Exception as e: send_info_string(f"syzygy error: {e}")
        else:
            send_info_string(f"syzygy tablebase NOT found in {file_path}")

    def get_best_move(self, state):
        if not self.tablebase: return None

        # Tablebases are typically 3-4-5 pieces
        if state.bitboards['all'].bit_count() > 5: return None 

        try: board = state_to_board(state)
        except Exception: return None

        # 1. Probe Root WDL
        try: 
            current_wdl = self.tablebase.probe_wdl(board)
        except chess.syzygy.MissingTableError: 
            return None

        if current_wdl is None: return None

        # Get root DTZ for info string purposes
        try: root_dtz = self.tablebase.probe_dtz(board)
        except: root_dtz = 0

        best_move = None
        best_dtz = float('inf')
        
        # Move Ordering Strategy:
        # 1. Immediate Checkmate (The ultimate goal)
        # 2. Winning Zeroing Moves (Captures/Pawns) - Reset 50-move rule
        # 3. Winning Normal Moves - Pick lowest DTZ (fastest progress)
        
        moves = list(board.legal_moves)
        random.shuffle(moves) # Shuffle prevents repeating the same draw in drawn positions

        for move in moves:
            # Optimization: If winning, avoid repeating positions 
            if current_wdl > 0 and board.is_repetition(3): continue

            board.push(move)
            
            # --- CRITICAL FIX 1: Detect Mate ---
            if board.is_checkmate():
                board.pop()
                # Return strict win score. DTZ=0 implies immediate end.
                return (move.uci(), 2, 0) 

            # Handle Stalemate/Draws
            if board.is_game_over():
                # If we were winning (+2), a draw (0) is a fail.
                result_wdl = 0 
                result_dtz = 0
            else:
                try:
                    # Probe opponent's perspective
                    result_wdl = self.tablebase.probe_wdl(board)
                    result_dtz = self.tablebase.probe_dtz(board)
                except:
                    board.pop()
                    continue
            
            board.pop()

            if result_wdl is None or result_dtz is None: continue

            # --- Move Selection Logic ---

            # CASE 1: We are Winning (WDL > 0)
            if current_wdl > 0:
                # We only want moves where opponent is losing (-2 or -1)
                if result_wdl < 0:
                    
                    # --- CRITICAL FIX 2: Zeroing Moves ---
                    is_zeroing = board.is_capture(move) or move.piece_type == chess.PAWN
                    
                    move_dtz = abs(result_dtz)
                    
                    # If this is a zeroing move, treat its DTZ as 0.
                    # This forces the engine to pick it over any shuffling move.
                    if is_zeroing: 
                        move_dtz = 0 

                    # Standard Min-DTZ logic
                    if move_dtz < best_dtz:
                        best_dtz = move_dtz
                        best_move = move

            # CASE 2: We are Drawn (WDL = 0)
            elif current_wdl == 0:
                # Any move that keeps the draw is fine
                if result_wdl == 0:
                    best_move = move
                    # In a draw, any valid move is acceptable. 
                    # Shuffle (from random.shuffle above) handles variety.
                    break 

            # CASE 3: We are Losing (WDL < 0)
            elif current_wdl < 0:
                # If we must lose, make it take as long as possible.
                # Opponent wants to Win (>0). We maximize their DTZ.
                if result_wdl > 0:
                    move_dtz = abs(result_dtz)
                    
                    # Initialize max logic
                    if best_dtz == float('inf'): best_dtz = -1
                    
                    if move_dtz > best_dtz:
                        best_dtz = move_dtz
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
        if not self.tablebase: return None
        if state.bitboards['all'].bit_count() > 5: return None
        try:
            board = state_to_board(state)
            return self.tablebase.probe_dtz(board)
        except: return None

    def close(self):
        if self.tablebase:
            self.tablebase.close()
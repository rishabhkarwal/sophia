import os
import chess
import chess.polyglot

from engine.search.utils import state_to_board
from engine.uci.utils import send_info_string

class OpeningBook:
    def __init__(self, file_path="opening\\book.bin"):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.book_path = os.path.join(current_dir, file_path)
        self.is_book = os.path.exists(self.book_path)
        send_info_string(f"opening book{'' if self.is_book else ' NOT'} found in '{file_path}'") 

    def get_move(self, state):
        """Retrieves book move"""
        if not self.is_book: return None
            
        try:
            board = state_to_board(state)
            with chess.polyglot.open_reader(self.book_path) as reader:
                # weighted choice picks a move based on probability
                entry = reader.weighted_choice(board)
                return entry.move.uci()
        except Exception as e:
            # print(f"info string book error: {e}")
            return None
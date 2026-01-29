import os
import glob
import random
import chess
import chess.polyglot

from engine.search.utils import state_to_board
from engine.uci.utils import send_info_string

class OpeningBook:
    def __init__(self, directory='opening'):
        # get absolute path to the opening directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        book_path = os.path.join(current_dir, directory)
        
        # find all .bin files in that directory
        self.books = glob.glob(os.path.join(book_path, '*.bin'))
        
        if self.books:
            names = [f"'{os.path.basename(f).split('.')[0]}'" for f in self.books]
            send_info_string(f"found {len(self.books)} opening books in '{directory}': {', '.join(names)}")
        else:
            send_info_string(f"no opening books found in '{book_path}'")

    def get_move(self, state):
        """Retrieves a weighted random move using normalised weights from all books"""
        if not self.books:
            return None
            
        try:
            board = state_to_board(state)
            
            # e.g. {'e2e4': 250.5, 'd2d4': 200.0}
            move_weights = {}

            # iterate through every book file found
            for book in self.books:
                
                # dictionary for the current book only
                _book_move_weights = {}
                _book_total_weight = 0
                
                try:
                    with chess.polyglot.open_reader(book) as reader:
                        for entry in reader.find_all(board):
                            move_uci = entry.move.uci()
                            weight = entry.weight
                            
                            _book_move_weights[move_uci] = weight
                            _book_total_weight += weight
                except Exception:
                    continue

                if _book_total_weight == 0: continue

                # normalisation as books have different scales
                scale_factor = 10 / _book_total_weight

                for move_uci, raw_weight in _book_move_weights.items():
                    normalised_weight = raw_weight * scale_factor
                    
                    if move_uci in move_weights:
                        move_weights[move_uci] += normalised_weight
                    else:
                        move_weights[move_uci] = normalised_weight

            if not move_weights:
                return None

            moves = list(move_weights.keys())
            weights = list(move_weights.values())

            total_weight = sum(weights)
            sorted_options = sorted(move_weights.items(), key=lambda item: item[1], reverse=True)

            top_3 = sorted_options[:3]
            info_parts = []
            for move, w in top_3:
                pct = (w / total_weight) * 100
                info_parts.append(f"{move} ({int(pct)}%)")
            
            send_info_string(f"book options: {', '.join(info_parts)}")

            # select one move based on the combined normalised weights
            selected_move = random.choices(moves, weights=weights, k=1)[0]
            send_info_string(f"selected book move: {selected_move}")

            return selected_move

        except Exception as e:
            send_info_string(f"book error: {e}")
            return None
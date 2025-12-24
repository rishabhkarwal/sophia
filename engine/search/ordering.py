from engine.core.constants import (
    WHITE, WHITE_PIECES, BLACK_PIECES,
    INFINITY, KING,
    MASK_SOURCE, MAX_DEPTH
)
from engine.search.evaluation import MG_VALUES, EG_VALUES
from engine.core.move import is_capture, is_en_passant, is_promotion, get_start, get_target

class MoveOrdering:
    def __init__(self):
        # killer moves: [depth][slot]
        self.killer_moves = [[None] * 2 for _ in range(MAX_DEPTH + 2)]
        # history table: 64 x 64 array [from sq][to sq]
        self.history_table = [[0] * 64 for _ in range(64)]
        
        self.PIECE_VALUES = {piece: (MG_VALUES[piece] + EG_VALUES[piece]) / 2 for piece in MG_VALUES}
        self.PIECE_VALUES[KING] = INFINITY

    def store_killer(self, depth, move: int):
        if is_capture(move) or is_en_passant(move) or is_promotion(move): 
            return
        if self.killer_moves[depth][0] == move: 
            return
        self.killer_moves[depth][1] = self.killer_moves[depth][0]
        self.killer_moves[depth][0] = move

    def store_history(self, move: int, depth):
        if is_capture(move) or is_en_passant(move) or is_promotion(move): 
            return
        start = get_start(move)
        target = get_target(move)
        self.history_table[start][target] += depth * depth

    def _get_mvv_lva_score(self, state, move: int):
        start = get_start(move)
        target = get_target(move)
        target_mask = 1 << target
        start_mask = 1 << start
        bitboards = state.bitboards
        
        victim_val = 0
        aggressor_val = 0
        
        if state.is_white:
            for p in WHITE_PIECES:
                if bitboards[p] & start_mask:
                    aggressor_val = self.PIECE_VALUES[p.upper()]
                    break
            for p in BLACK_PIECES:
                if bitboards[p] & target_mask:
                    victim_val = self.PIECE_VALUES[p.upper()]
                    break
        else:
            for p in BLACK_PIECES:
                if bitboards[p] & start_mask:
                    aggressor_val = self.PIECE_VALUES[p.upper()]
                    break
            for p in WHITE_PIECES:
                if bitboards[p] & target_mask:
                    victim_val = self.PIECE_VALUES[p.upper()]
                    break
                
        if victim_val == 0: victim_val = 100
        return (10 * victim_val) - aggressor_val

    def get_move_score(self, move: int, tt_move, state, depth, killer_1, killer_2):
        if move == tt_move: return INFINITY * 100
        
        is_cap = is_capture(move) or is_en_passant(move) or is_promotion(move)
        
        if is_cap:
            return INFINITY * 10 + self._get_mvv_lva_score(state, move)
            
        if move == killer_1: return INFINITY * 9
        if move == killer_2: return INFINITY * 8
        
        start = get_start(move)
        target = get_target(move)
        return self.history_table[start][target]

    def clear(self):
        self.killer_moves = [[None] * 2 for _ in range(MAX_DEPTH + 2)]
        self.history_table = [[0] * 64 for _ in range(64)]
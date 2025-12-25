from engine.core.constants import (
    WHITE, INFINITY, NULL,
    PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
    MAX_DEPTH, MASK_SOURCE
)
from engine.core.move import CAPTURE_FLAG, EP_FLAG, PROMO_FLAG, SHIFT_TARGET

class MoveOrdering:
    def __init__(self):
        self.killer_moves = [[None] * 2 for _ in range(MAX_DEPTH + 2)]
        self.history_table = [[0] * 64 for _ in range(64)]
        
        self.TYPE_VALUES = {
            PAWN: 100, KNIGHT: 320, BISHOP: 330, ROOK: 500, QUEEN: 900, KING: 20000
        }
    
    def store_killer(self, depth, move: int):
        # Inline checks
        if (move & CAPTURE_FLAG) or (move & EP_FLAG) or (move & PROMO_FLAG): 
            return
        if self.killer_moves[depth][0] == move: 
            return
        self.killer_moves[depth][1] = self.killer_moves[depth][0]
        self.killer_moves[depth][0] = move
    
    def store_history(self, move: int, depth):
        # inline checks
        if (move & CAPTURE_FLAG) or (move & EP_FLAG) or (move & PROMO_FLAG): 
            return
        start = move & MASK_SOURCE
        target = (move >> SHIFT_TARGET) & MASK_SOURCE
        self.history_table[start][target] += depth * depth
    
    def _get_mvv_lva_score(self, state, move: int):
        start = move & MASK_SOURCE
        target = (move >> SHIFT_TARGET) & MASK_SOURCE
        
        attacker = state.board[start]
        victim = state.board[target]
        
        if victim == NULL: 
            if move & EP_FLAG: victim_val = self.TYPE_VALUES[PAWN]
            else: victim_val = 0
        else:
            # extract piece type by removing colour bit
            victim_type = victim & ~WHITE
            victim_val = self.TYPE_VALUES[victim_type]
            
        # extract piece type
        attacker_type = attacker & ~WHITE
        attacker_val = self.TYPE_VALUES[attacker_type]
        
        return (10 * victim_val) - attacker_val
    
    def get_move_score(self, move: int, tt_move, state, depth, killer_1, killer_2):
        if move == tt_move: return INFINITY * 100
        
        # inline check for captures/promotions
        is_cap = (move & CAPTURE_FLAG) or (move & EP_FLAG) or (move & PROMO_FLAG)
        
        if is_cap: return INFINITY * 10 + self._get_mvv_lva_score(state, move)
            
        if move == killer_1: return INFINITY * 9
        if move == killer_2: return INFINITY * 8
        
        start = move & MASK_SOURCE
        target = (move >> SHIFT_TARGET) & MASK_SOURCE
        return self.history_table[start][target]
    
    def clear(self):
        self.killer_moves = [[None] * 2 for _ in range(MAX_DEPTH + 2)]
        self.history_table = [[0] * 64 for _ in range(64)]
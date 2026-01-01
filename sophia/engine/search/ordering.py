from engine.core.constants import (
    WHITE, INFINITY, NULL,
    PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
    MAX_DEPTH, MASK_SOURCE, PIECE_VALUES
)
from engine.core.move import (
    CAPTURE, EN_PASSANT, PROMOTION, 
    SHIFT_TARGET, SHIFT_FLAG
)

class MoveOrdering:
    def __init__(self):
        self.killer_moves = [[None] * 2 for _ in range(MAX_DEPTH + 2)]
        self.history_table = [[0] * 64 for _ in range(64)]
    
    def store_killer(self, depth, move: int):
        flag = (move >> SHIFT_FLAG) & 0xF

        if (flag & CAPTURE) or (flag == EN_PASSANT) or (flag & PROMOTION):
            return

        if self.killer_moves[depth][0] == move: return
        self.killer_moves[depth][1] = self.killer_moves[depth][0]
        self.killer_moves[depth][0] = move
    
    def store_history(self, move: int, depth):
        flag = (move >> SHIFT_FLAG) & 0xF
        if (flag & CAPTURE) or (flag == EN_PASSANT) or (flag & PROMOTION):
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
            flag = (move >> SHIFT_FLAG) & 0xF
            if flag == EN_PASSANT:
                victim_val = PIECE_VALUES[PAWN] # pawn
            else:
                victim_val = 0
        else:
            victim_type = (victim & ~WHITE)
            victim_val = PIECE_VALUES[victim_type]
        
        attacker_type = (attacker & ~WHITE)
        attacker_val = PIECE_VALUES[attacker_type]
        
        return (10 * victim_val) - attacker_val
    
    def get_move_score(self, move: int, tt_move, state, depth, killer_1, killer_2):
        if move == tt_move: return INFINITY * 100
        
        flag = (move >> SHIFT_FLAG) & 0xF
        is_cap = (flag & CAPTURE) or (flag == EN_PASSANT) or (flag & PROMOTION)
        
        if is_cap: return INFINITY * 10 + self._get_mvv_lva_score(state, move)
            
        if move == killer_1: return INFINITY * 9
        if move == killer_2: return INFINITY * 8
        
        start = move & MASK_SOURCE
        target = (move >> SHIFT_TARGET) & MASK_SOURCE
        return self.history_table[start][target]
    
    def clear(self):
        self.killer_moves = [[None] * 2 for _ in range(MAX_DEPTH + 2)]
        self.history_table = [[0] * 64 for _ in range(64)]
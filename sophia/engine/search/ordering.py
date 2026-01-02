from engine.core.constants import (
    WHITE, INFINITY, NULL,
    PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
    MAX_DEPTH, MASK_SOURCE, PIECE_VALUES
)
from engine.core.move import (
    CAPTURE, EN_PASSANT, PROMOTION, 
    SHIFT_TARGET, SHIFT_FLAG
)

# repetition penalty for moving same piece repeatedly
REPETITION_PENALTY = -25  # (except king)

class MoveOrdering:
    def __init__(self):
        self.killer_moves = [[None] * 2 for _ in range(MAX_DEPTH + 2)]
        self.history_table = [[0] * 64 for _ in range(64)]
        self.countermoves = [[None] * 64 for _ in range(64)]  # [from_sq][to_sq] -> countermove
    
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
    
    def store_countermove(self, previous_move, current_move: int):
        """Store countermove: after opponent plays previous move, we play current move"""
        if previous_move is None:
            return
        
        flag = (current_move >> SHIFT_FLAG) & 0xF
        if (flag & CAPTURE) or (flag == EN_PASSANT) or (flag & PROMOTION):
            return
        
        prev_from = previous_move & MASK_SOURCE
        prev_to = (previous_move >> SHIFT_TARGET) & MASK_SOURCE
        self.countermoves[prev_from][prev_to] = current_move
    
    def get_countermove(self, previous_move):
        """Get the countermove for the previous opponent move"""
        if previous_move is None:
            return None
        prev_from = previous_move & MASK_SOURCE
        prev_to = (previous_move >> SHIFT_TARGET) & MASK_SOURCE
        return self.countermoves[prev_from][prev_to]
    
    def _get_mvv_lva_score(self, state, move: int):
        start = move & MASK_SOURCE
        target = (move >> SHIFT_TARGET) & MASK_SOURCE
        
        attacker = state.board[start]
        victim = state.board[target]
        
        if victim == NULL: 
            flag = (move >> SHIFT_FLAG) & 0xF
            if flag == EN_PASSANT:
                victim_val = PIECE_VALUES[PAWN]
            else:
                victim_val = 0
        else:
            victim_type = (victim & ~WHITE)
            victim_val = PIECE_VALUES[victim_type]
        
        attacker_type = (attacker & ~WHITE)
        attacker_val = PIECE_VALUES[attacker_type]
        
        return (10 * victim_val) - attacker_val
    
    def get_move_score(self, move: int, tt_move, counter_move, state, depth, killer_1, killer_2):
        """Calculate move score for ordering"""
        if move == tt_move: return INFINITY * 100
        
        flag = (move >> SHIFT_FLAG) & 0xF
        is_cap = (flag & CAPTURE) or (flag == EN_PASSANT) or (flag & PROMOTION)
        
        if is_cap: return INFINITY * 10 + self._get_mvv_lva_score(state, move)
        
        if move == counter_move: return INFINITY * 9.5
        if move == killer_1: return INFINITY * 9
        if move == killer_2: return INFINITY * 8
        
        start = move & MASK_SOURCE
        target = (move >> SHIFT_TARGET) & MASK_SOURCE
        
        base_score = self.history_table[start][target]
        
        # repetition penalty - discourage moving the same piece repeatedly
        # (except kings, which should be moving around)
        if state.last_moved_piece_sq >= 0 and state.last_moved_piece_sq == start:
            piece = state.board[start]
            if piece != NULL:
                piece_type = piece & ~WHITE
                if piece_type != KING:
                    base_score += REPETITION_PENALTY
        
        return base_score
    
    def clear(self):
        self.killer_moves = [[None] * 2 for _ in range(MAX_DEPTH + 2)]
        self.history_table = [[0] * 64 for _ in range(64)]
        self.countermoves = [[None] * 64 for _ in range(64)]

# incremental move selection (pick next best without full sort)
def pick_next_move(moves, start_index, state, ordering, tt_move, counter, depth, k1, k2):
    if start_index >= len(moves):
        return -1
    
    best_idx = start_index
    best_score = ordering.get_move_score(moves[start_index], tt_move, counter, state, depth, k1, k2)
    
    # find the best move among remaining moves
    for i in range(start_index + 1, len(moves)):
        score = ordering.get_move_score(moves[i], tt_move, counter, state, depth, k1, k2)
        if score > best_score:
            best_score = score
            best_idx = i
    
    # Swap best move to current position
    if best_idx != start_index:
        moves[start_index], moves[best_idx] = moves[best_idx], moves[start_index]
    
    return start_index
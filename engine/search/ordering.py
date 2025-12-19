from engine.core.constants import WHITE, WHITE_PIECES, BLACK_PIECES

class MoveOrdering:
    def __init__(self):
        # Killer Moves: [Depth][Slot]
        self.killer_moves = [[None] * 2 for _ in range(102)]
        # History table: 64x64 array [from_sq][to_sq]
        self.history_table = [[0] * 64 for _ in range(64)]
        
        self.PIECE_VALUES = {
            'P': 100, 'N': 320, 'B': 330, 'R': 500, 'Q': 900, 'K': 20000,
            'p': 100, 'n': 320, 'b': 330, 'r': 500, 'q': 900, 'k': 20000
        }

    def store_killer(self, depth, move):
        if move.is_capture: return 
        if self.killer_moves[depth][0] == move: return
        self.killer_moves[depth][1] = self.killer_moves[depth][0]
        self.killer_moves[depth][0] = move

    def store_history(self, move, depth):
        if move.is_capture: return
        self.history_table[move.start][move.target] += depth * depth

    def get_mvv_lva_score(self, state, move):
        if not move.is_capture: return 0
        
        target_mask = 1 << move.target
        start_mask = 1 << move.start
        
        victim_val = 0
        aggressor_val = 0
        
        if state.player == WHITE:
            # Aggressor is White
            for p in WHITE_PIECES:
                if state.bitboards.get(p, 0) & start_mask:
                    aggressor_val = self.PIECE_VALUES[p]
                    break
            # Victim is Black
            for p in BLACK_PIECES:
                if state.bitboards.get(p, 0) & target_mask:
                    victim_val = self.PIECE_VALUES[p]
                    break
        else:
            # Aggressor is Black
            for p in BLACK_PIECES:
                if state.bitboards.get(p, 0) & start_mask:
                    aggressor_val = self.PIECE_VALUES[p]
                    break
            # Victim is White
            for p in WHITE_PIECES:
                if state.bitboards.get(p, 0) & target_mask:
                    victim_val = self.PIECE_VALUES[p]
                    break
                
        if victim_val == 0: victim_val = 100 
            
        return (10 * victim_val) - aggressor_val

    def get_move_score(self, move, tt_move, state, depth, killer_1, killer_2):
        if move == tt_move: return 10_000_000
        if move.is_capture: return 1_000_000 + self.get_mvv_lva_score(state, move)
        if move == killer_1: return 900_000
        if move == killer_2: return 800_000
        return self.history_table[move.start][move.target]
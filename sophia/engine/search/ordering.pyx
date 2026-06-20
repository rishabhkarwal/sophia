# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True

from engine.core.constants import (
    WHITE, INFINITY, NULL as _NULL,
    PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
    MAX_DEPTH, MASK_SOURCE, PIECE_VALUES,
    HISTORY_MAX, HISTORY_GRAVITY,
)
from engine.core.move import (
    CAPTURE, EN_PASSANT, PROMOTION, FLAG_MASK,
    SHIFT_TARGET, SHIFT_FLAG
)
from engine.search.see cimport see_ge
from engine.board.state cimport State

cdef int _INFINITY        = INFINITY
cdef int _NULL_SQ         = _NULL
cdef int _SHIFT_TARGET    = SHIFT_TARGET
cdef int _SHIFT_FLAG      = SHIFT_FLAG
cdef int _CAPTURE         = CAPTURE
cdef int _EN_PASSANT      = EN_PASSANT
cdef int _PROMOTION       = PROMOTION
cdef int _FLAG_MASK       = FLAG_MASK
cdef int _MASK_SOURCE     = MASK_SOURCE
cdef int _HISTORY_MAX     = HISTORY_MAX
cdef int _PAWN            = PAWN
cdef int _KNIGHT          = KNIGHT
cdef int _BISHOP          = BISHOP
cdef int _ROOK            = ROOK
cdef int _QUEEN           = QUEEN
cdef int _KING            = KING
cdef int _WHITE           = WHITE

cdef int _SCORE_TT_MOVE      = 2_000_000_000 # highest
cdef int _SCORE_GOOD_CAP     = 1_000_000_000 # good capture (SEE >= 0)
cdef int _SCORE_COUNTER_MOVE =   900_000_000
cdef int _SCORE_KILLER_1     =   800_000_000
cdef int _SCORE_KILLER_2     =   700_000_000
cdef int _SCORE_BAD_CAP      =  -100_000_000 # bad capture (SEE < 0), MVV-LVA adjusted

# repetition penalty for moving same piece repeatedly
cdef int _REPETITION_PENALTY = -25 # (except king)

cdef int[16] _PIECE_VALUES
_PIECE_VALUES[_PAWN]   = PIECE_VALUES[PAWN]
_PIECE_VALUES[_KNIGHT] = PIECE_VALUES[KNIGHT]
_PIECE_VALUES[_BISHOP] = PIECE_VALUES[BISHOP]
_PIECE_VALUES[_ROOK]   = PIECE_VALUES[ROOK]
_PIECE_VALUES[_QUEEN]  = PIECE_VALUES[QUEEN]
_PIECE_VALUES[_KING]   = PIECE_VALUES[KING]


cdef class MoveOrdering:
    def __init__(self):
        cdef int i, j
        for i in range(64):
            for j in range(64):
                self.history_table[i][j] = 0
                self.countermoves[i][j] = 0
        for i in range(102):
            self.killer_moves[i][0] = 0
            self.killer_moves[i][1] = 0

    cpdef void store_killer(self, int depth, unsigned int move) noexcept:
        cdef int flag
        flag = (move >> _SHIFT_FLAG) & _FLAG_MASK

        if (flag & _CAPTURE) or (flag == _EN_PASSANT) or (flag & _PROMOTION): return

        if self.killer_moves[depth][0] == move: return

        self.killer_moves[depth][1] = self.killer_moves[depth][0]
        self.killer_moves[depth][0] = move

    cdef void store_history(self, unsigned int move, int depth) noexcept:
        cdef int flag, start, target, bonus
        flag = (move >> _SHIFT_FLAG) & _FLAG_MASK

        if (flag & _CAPTURE) or (flag == _EN_PASSANT) or (flag & _PROMOTION): return

        start  = move & _MASK_SOURCE
        target = (move >> _SHIFT_TARGET) & _MASK_SOURCE

        bonus  = depth * depth
        self.history_table[start][target] += bonus - self.history_table[start][target] * bonus // _HISTORY_MAX

    cdef void apply_history_malus(self, unsigned int move, int depth) noexcept:
        cdef int flag, start, target, bonus
        flag = (move >> _SHIFT_FLAG) & _FLAG_MASK

        if (flag & _CAPTURE) or (flag == _EN_PASSANT) or (flag & _PROMOTION): return

        start  = move & _MASK_SOURCE
        target = (move >> _SHIFT_TARGET) & _MASK_SOURCE

        bonus  = depth * depth
        self.history_table[start][target] -= bonus - self.history_table[start][target] * bonus // _HISTORY_MAX

    cdef void store_countermove(self, object previous_move, unsigned int current_move) noexcept:
        cdef int flag, prev_from, prev_to, previous_move_int

        if previous_move is None: return

        flag = (current_move >> _SHIFT_FLAG) & _FLAG_MASK

        if (flag & _CAPTURE) or (flag == _EN_PASSANT) or (flag & _PROMOTION): return

        previous_move_int = <int>previous_move
        prev_from = previous_move_int & _MASK_SOURCE
        prev_to   = (previous_move_int >> _SHIFT_TARGET) & _MASK_SOURCE

        self.countermoves[prev_from][prev_to] = current_move

    cpdef unsigned int get_countermove(self, object previous_move) noexcept:
        cdef int prev_from, prev_to, previous_move_int

        if previous_move is None: return 0
        previous_move_int = <int>previous_move

        prev_from = previous_move_int & _MASK_SOURCE
        prev_to   = (previous_move_int >> _SHIFT_TARGET) & _MASK_SOURCE

        return self.countermoves[prev_from][prev_to]

    cpdef int get_move_score(self, unsigned int move, unsigned int tt_move,
                             unsigned int counter_move, State state,
                             int depth, unsigned int killer_1, unsigned int killer_2) noexcept:
        cdef int flag, start, target, base_score
        cdef int piece, piece_type
        cdef int attacker, victim, victim_val, attacker_val, mvv_lva

        if move == tt_move: return _SCORE_TT_MOVE

        flag = (move >> _SHIFT_FLAG) & _FLAG_MASK
        cdef bint is_cap = (flag & _CAPTURE) or (flag == _EN_PASSANT) or (flag & _PROMOTION)

        if is_cap:
            # MVV-LVA
            start   = move & _MASK_SOURCE
            target  = (move >> _SHIFT_TARGET) & _MASK_SOURCE
            attacker = state.board[start]
            victim   = state.board[target]

            if victim == _NULL_SQ:
                if flag == _EN_PASSANT:
                    victim_val = _PIECE_VALUES[_PAWN]
                else:
                    victim_val = 0
            else:
                victim_val = _PIECE_VALUES[victim & ~_WHITE]

            attacker_val = _PIECE_VALUES[attacker & ~_WHITE]
            mvv_lva = 10 * victim_val - attacker_val

            if see_ge(state, move, 0):
                return _SCORE_GOOD_CAP + mvv_lva
            else:
                return _SCORE_BAD_CAP + mvv_lva

        if move == counter_move and counter_move != 0:
            return _SCORE_COUNTER_MOVE
        if move == killer_1 and killer_1 != 0:
            return _SCORE_KILLER_1
        if move == killer_2 and killer_2 != 0:
            return _SCORE_KILLER_2

        start  = move & _MASK_SOURCE
        target = (move >> _SHIFT_TARGET) & _MASK_SOURCE
        base_score = self.history_table[start][target]

        if state.last_moved_piece_sq >= 0 and state.last_moved_piece_sq == start:
            piece = state.board[start]
            if piece != _NULL_SQ:
                piece_type = piece & ~_WHITE
                if piece_type != _KING:
                    base_score += _REPETITION_PENALTY

        return base_score

    def clear(self):
        cdef int i, j
        for i in range(102):
            self.killer_moves[i][0] = 0
            self.killer_moves[i][1] = 0
        for i in range(64):
            for j in range(64):
                self.history_table[i][j] = 0
                self.countermoves[i][j] = 0


cpdef int pick_next_move(list moves, int start_index, State state, MoveOrdering ordering,
                         unsigned int tt_move, unsigned int counter,
                         int depth, unsigned int k1, unsigned int k2) noexcept:
    cdef int best_idx, i, n, best_score, score
    cdef unsigned int mv
    n = len(moves)
    if start_index >= n:
        return -1

    best_idx   = start_index
    best_score = ordering.get_move_score(<unsigned int>moves[start_index], tt_move, counter, state, depth, k1, k2)

    for i in range(start_index + 1, n):
        score = ordering.get_move_score(<unsigned int>moves[i], tt_move, counter, state, depth, k1, k2)
        if score > best_score:
            best_score = score
            best_idx   = i

    if best_idx != start_index:
        moves[start_index], moves[best_idx] = moves[best_idx], moves[start_index]

    return start_index

# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True

from engine.core.constants import (
    WHITE, INFINITY, NULL as _NULL,
    PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
    MAX_DEPTH,
    HISTORY_MAX, HISTORY_GRAVITY,
)
from engine.core.parameters import (
    PIECE_VALUES,
    SCORE_TT_MOVE, SCORE_GOOD_CAP, SCORE_COUNTER_MOVE,
    SCORE_KILLER_1, SCORE_KILLER_2, SCORE_BAD_CAP,
    MOVE_REPETITION_PENALTY, MVV_LVA_MULTIPLIER,
)
from engine.core.move import (
    CAPTURE, EN_PASSANT, PROMOTION,
)
from engine.core.move cimport move_source, move_target, move_flag, is_capture, is_promotion, is_en_passant
from engine.search.see cimport see_ge
from engine.board.state cimport State
from engine.moves.generator cimport MoveList

cdef int _INFINITY        = INFINITY
cdef int _NULL_SQ         = _NULL
cdef int _CAPTURE         = CAPTURE
cdef int _EN_PASSANT      = EN_PASSANT
cdef int _PROMOTION       = PROMOTION
cdef int _HISTORY_MAX     = HISTORY_MAX
cdef int _PAWN            = PAWN
cdef int _KNIGHT          = KNIGHT
cdef int _BISHOP          = BISHOP
cdef int _ROOK            = ROOK
cdef int _QUEEN           = QUEEN
cdef int _KING            = KING
cdef int _WHITE           = WHITE

cdef int _SCORE_TT_MOVE      = SCORE_TT_MOVE
cdef int _SCORE_GOOD_CAP     = SCORE_GOOD_CAP
cdef int _SCORE_COUNTER_MOVE = SCORE_COUNTER_MOVE
cdef int _SCORE_KILLER_1     = SCORE_KILLER_1
cdef int _SCORE_KILLER_2     = SCORE_KILLER_2
cdef int _SCORE_BAD_CAP      = SCORE_BAD_CAP
cdef int _REPETITION_PENALTY = MOVE_REPETITION_PENALTY
cdef int _MVV_LVA_MULT       = MVV_LVA_MULTIPLIER

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
        if is_capture(move) or is_en_passant(move) or is_promotion(move): return

        if self.killer_moves[depth][0] == move: return

        self.killer_moves[depth][1] = self.killer_moves[depth][0]
        self.killer_moves[depth][0] = move

    cdef void store_history(self, unsigned int move, int depth) noexcept:
        cdef int start, target, bonus

        if is_capture(move) or is_en_passant(move) or is_promotion(move): return

        start  = move_source(move)
        target = move_target(move)

        bonus  = depth * depth
        self.history_table[start][target] += bonus - self.history_table[start][target] * bonus // _HISTORY_MAX

    cdef void apply_history_malus(self, unsigned int move, int depth) noexcept:
        cdef int start, target, bonus

        if is_capture(move) or is_en_passant(move) or is_promotion(move): return

        start  = move_source(move)
        target = move_target(move)

        bonus  = depth * depth
        self.history_table[start][target] -= bonus - self.history_table[start][target] * bonus // _HISTORY_MAX

    cdef void store_countermove(self, object previous_move, unsigned int current_move) noexcept:
        cdef int prev_from, prev_to, previous_move_int

        if previous_move is None: return

        if is_capture(current_move) or is_en_passant(current_move) or is_promotion(current_move): return

        previous_move_int = <int>previous_move
        prev_from = move_source(<unsigned int>previous_move_int)
        prev_to   = move_target(<unsigned int>previous_move_int)

        self.countermoves[prev_from][prev_to] = current_move

    cpdef unsigned int get_countermove(self, object previous_move) noexcept:
        cdef int prev_from, prev_to, previous_move_int

        if previous_move is None: return 0
        previous_move_int = <int>previous_move

        prev_from = move_source(<unsigned int>previous_move_int)
        prev_to   = move_target(<unsigned int>previous_move_int)

        return self.countermoves[prev_from][prev_to]

    cpdef int get_move_score(self, unsigned int move, unsigned int tt_move,
                             unsigned int counter_move, State state,
                             int depth, unsigned int killer_1, unsigned int killer_2) noexcept:
        cdef int start, target, base_score
        cdef int piece, piece_type
        cdef int attacker, victim, victim_val, attacker_val, mvv_lva

        if move == tt_move: return _SCORE_TT_MOVE

        cdef bint is_cap = is_capture(move) or is_en_passant(move) or is_promotion(move)

        if is_cap:
            # MVV-LVA
            start   = move_source(move)
            target  = move_target(move)
            attacker = state.board[start]
            victim   = state.board[target]

            if victim == _NULL_SQ:
                if is_en_passant(move):
                    victim_val = _PIECE_VALUES[_PAWN]
                else:
                    victim_val = 0
            else:
                victim_val = _PIECE_VALUES[victim & ~_WHITE]

            attacker_val = _PIECE_VALUES[attacker & ~_WHITE]
            mvv_lva = _MVV_LVA_MULT * victim_val - attacker_val

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

        start  = move_source(move)
        target = move_target(move)
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


cdef void score_move_list(MoveList* moves, int* scores, signed char* see_cache,
                          State state, MoveOrdering ordering,
                          unsigned int tt_move, unsigned int counter,
                          int depth, unsigned int k1, unsigned int k2) noexcept:
    cdef int i, n, start, target, base_score
    cdef int piece, piece_type
    cdef int attacker, victim, victim_val, attacker_val, mvv_lva
    cdef bint is_cap, see_ok
    cdef unsigned int move

    n = moves.count
    for i in range(n):
        move = moves.moves[i]
        see_cache[i] = -1

        is_cap = is_capture(move) or is_en_passant(move) or is_promotion(move)

        if is_cap:
            start  = move_source(move)
            target = move_target(move)
            attacker = state.board[start]
            victim   = state.board[target]

            if victim == _NULL_SQ:
                if is_en_passant(move):
                    victim_val = _PIECE_VALUES[_PAWN]
                else:
                    victim_val = 0
            else:
                victim_val = _PIECE_VALUES[victim & ~_WHITE]

            attacker_val = _PIECE_VALUES[attacker & ~_WHITE]
            mvv_lva = _MVV_LVA_MULT * victim_val - attacker_val

            see_ok = see_ge(state, move, 0)
            see_cache[i] = 1 if see_ok else 0

            if move == tt_move:
                scores[i] = _SCORE_TT_MOVE
            elif see_ok:
                scores[i] = _SCORE_GOOD_CAP + mvv_lva
            else:
                scores[i] = _SCORE_BAD_CAP + mvv_lva
            continue

        if move == tt_move:
            scores[i] = _SCORE_TT_MOVE
            continue
        if move == counter and counter != 0:
            scores[i] = _SCORE_COUNTER_MOVE
            continue
        if move == k1 and k1 != 0:
            scores[i] = _SCORE_KILLER_1
            continue
        if move == k2 and k2 != 0:
            scores[i] = _SCORE_KILLER_2
            continue

        start  = move_source(move)
        target = move_target(move)
        base_score = ordering.history_table[start][target]

        if state.last_moved_piece_sq >= 0 and state.last_moved_piece_sq == start:
            piece = state.board[start]
            if piece != _NULL_SQ:
                piece_type = piece & ~_WHITE
                if piece_type != _KING:
                    base_score += _REPETITION_PENALTY

        scores[i] = base_score


cdef int pick_next_move_list(MoveList* moves, int* scores, signed char* see_cache,
                             int start_index) noexcept:
    cdef int best_idx, i, n, best_score, tmp_score
    cdef unsigned int tmp
    cdef signed char tmp_see

    n = moves.count
    if start_index >= n:
        return -1

    best_idx   = start_index
    best_score = scores[start_index]

    for i in range(start_index + 1, n):
        if scores[i] > best_score:
            best_score = scores[i]
            best_idx   = i

    if best_idx != start_index:
        tmp = moves.moves[start_index]
        moves.moves[start_index] = moves.moves[best_idx]
        moves.moves[best_idx] = tmp

        tmp_score = scores[start_index]
        scores[start_index] = scores[best_idx]
        scores[best_idx] = tmp_score

        tmp_see = see_cache[start_index]
        see_cache[start_index] = see_cache[best_idx]
        see_cache[best_idx] = tmp_see

    return start_index

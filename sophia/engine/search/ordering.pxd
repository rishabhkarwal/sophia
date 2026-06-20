# declaration header for ordering.pyx

from engine.board.state cimport State
from engine.moves.generator cimport MoveList

cdef class MoveOrdering:
    cdef public int   history_table[64][64]
    cdef public unsigned int killer_moves[102][2]   # MAX_DEPTH + 2 = 102
    cdef public unsigned int countermoves[64][64]   # 0 = no move

    cpdef void store_killer(self, int depth, unsigned int move) noexcept
    cdef void store_history(self, unsigned int move, int depth) noexcept
    cdef void apply_history_malus(self, unsigned int move, int depth) noexcept
    cdef void store_countermove(self, object previous_move, unsigned int current_move) noexcept
    cpdef unsigned int get_countermove(self, object previous_move) noexcept
    cpdef int get_move_score(self, unsigned int move, unsigned int tt_move,
                             unsigned int counter_move, State state,
                             int depth, unsigned int killer_1, unsigned int killer_2) noexcept

cpdef int pick_next_move(list moves, int start_index, State state, MoveOrdering ordering,
                         unsigned int tt_move, unsigned int counter,
                         int depth, unsigned int k1, unsigned int k2) noexcept
cdef void score_move_list(MoveList* moves, int* scores, signed char* see_cache,
                          State state, MoveOrdering ordering,
                          unsigned int tt_move, unsigned int counter,
                          int depth, unsigned int k1, unsigned int k2) noexcept
cdef int pick_next_move_list(MoveList* moves, int* scores, signed char* see_cache,
                             int start_index) noexcept

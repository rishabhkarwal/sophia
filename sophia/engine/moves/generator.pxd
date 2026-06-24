from engine.board.state cimport State

cdef struct MoveList:
    unsigned int moves[256]
    int count

cdef void generate_pseudo_legal_move_list(State state, MoveList* moves, bint captures_only) noexcept
cdef void generate_check_evasion_move_list(State state, MoveList* moves) noexcept
cdef bint is_pseudo_legal_move(State state, unsigned int move) noexcept
cpdef list generate_pseudo_legal_moves(State state, bint captures_only=*)
cdef void generate_legal_move_list(State state, MoveList* moves, bint captures_only) noexcept
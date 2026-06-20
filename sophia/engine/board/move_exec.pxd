from engine.board.state cimport State

cpdef void make_move(State state, unsigned int move)
cpdef void unmake_move(State state, unsigned int move)
cpdef void make_null_move(State state)
cpdef void unmake_null_move(State state)
cpdef bint has_insufficient_material(State state)

from engine.board.state cimport State

cdef bint see_ge(State state, unsigned int move, int threshold) noexcept

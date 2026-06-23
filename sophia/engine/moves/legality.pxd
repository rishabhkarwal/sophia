# declaration header for legality.pyx

from engine.board.state cimport State

cdef bint is_square_attacked(State state, int sq, bint by_white) noexcept
cdef unsigned long long attackers_to_square(State state, int sq, bint colour) noexcept
cpdef bint is_in_check(State state, bint colour) noexcept
cpdef bint is_legal(State state, unsigned int move)

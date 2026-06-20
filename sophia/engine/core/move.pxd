# declaration header for move.pyx
# cimport this to get zero-overhead

cdef unsigned int _pack(int start, int target, int flag) noexcept nogil
cpdef str move_to_uci(unsigned int move)

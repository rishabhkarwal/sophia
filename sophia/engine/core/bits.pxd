# declaration header for bits.pyx — allows other .pyx files
# as pure c calls (zero python dispatch)

cdef int lsb(unsigned long long bb) noexcept nogil
cdef unsigned long long pop_lsb(unsigned long long bb) noexcept nogil
cdef int popcount(unsigned long long bb) noexcept nogil

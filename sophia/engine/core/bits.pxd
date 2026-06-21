cdef extern from *:
    """
    static inline int _sophia_ctz64(unsigned long long x) {
        return __builtin_ctzll(x);
    }
    static inline int _sophia_popcount64(unsigned long long x) {
        return __builtin_popcountll(x);
    }
    """
    int _sophia_ctz64(unsigned long long x) noexcept nogil
    int _sophia_popcount64(unsigned long long x) noexcept nogil


cdef inline int lsb(unsigned long long bb) noexcept nogil:
    return _sophia_ctz64(bb)


cdef inline unsigned long long pop_lsb(unsigned long long bb) noexcept nogil:
    return bb & (bb - 1)


cdef inline int popcount(unsigned long long bb) noexcept nogil:
    return _sophia_popcount64(bb)

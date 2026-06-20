# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True

# inline c bit helpers. These replace inline python calls throughout
# __builtin_ctzll is available on
# all gcc/clang targets and compiles to a single BSF/TZCNT instruction.

cdef extern from *:
    """
    static inline int _ctz64(unsigned long long x) {
        return __builtin_ctzll(x);
    }
    static inline int _popcount64(unsigned long long x) {
        return __builtin_popcountll(x);
    }
    """
    int _ctz64(unsigned long long x) noexcept nogil
    int _popcount64(unsigned long long x) noexcept nogil


cdef inline int lsb(unsigned long long bb) noexcept nogil:
    """index of least-significant bit"""
    return _ctz64(bb)


cdef inline unsigned long long pop_lsb(unsigned long long bb) noexcept nogil:
    """clear the least-significant set bit and return the result"""
    return bb & (bb - 1)


cdef inline int popcount(unsigned long long bb) noexcept nogil:
    """population count (number of set bits)"""
    return _popcount64(bb)

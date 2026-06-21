# declaration header for move.pyx
# cimport this to get zero-overhead

cdef enum:
    _MOVE_MASK_SOURCE = 0b0000000000111111
    _MOVE_FLAG_MASK   = 0b1111
    _MOVE_PROMOTION   = 0b1000
    _MOVE_CAPTURE     = 0b0100
    _MOVE_SPECIAL_1   = 0b0010
    _MOVE_SPECIAL_0   = 0b0001
    _MOVE_CASTLE_KS   = _MOVE_SPECIAL_1
    _MOVE_CASTLE_QS   = _MOVE_SPECIAL_1 | _MOVE_SPECIAL_0
    _MOVE_EN_PASSANT  = _MOVE_CAPTURE | _MOVE_SPECIAL_0
    _MOVE_SHIFT_TARGET = 6
    _MOVE_SHIFT_FLAG   = 12
    _MOVE_CAPTURE_FLAG = _MOVE_CAPTURE << _MOVE_SHIFT_FLAG
    _MOVE_PROMO_FLAG   = _MOVE_PROMOTION << _MOVE_SHIFT_FLAG


cdef inline unsigned int _pack(int start, int target, int flag) noexcept nogil:
    return <unsigned int>(start | (target << _MOVE_SHIFT_TARGET) | (flag << _MOVE_SHIFT_FLAG))


cdef inline int move_source(unsigned int move) noexcept nogil:
    return <int>(move & _MOVE_MASK_SOURCE)


cdef inline int move_target(unsigned int move) noexcept nogil:
    return <int>((move >> _MOVE_SHIFT_TARGET) & _MOVE_MASK_SOURCE)


cdef inline int move_flag(unsigned int move) noexcept nogil:
    return <int>((move >> _MOVE_SHIFT_FLAG) & _MOVE_FLAG_MASK)


cdef inline int move_flag_shifted(unsigned int move) noexcept nogil:
    return <int>(move >> _MOVE_SHIFT_FLAG)


cdef inline int move_promotion_index(unsigned int move) noexcept nogil:
    return move_flag(move) & (_MOVE_SPECIAL_1 | _MOVE_SPECIAL_0)


cdef inline bint is_capture(unsigned int move) noexcept nogil:
    return (move & _MOVE_CAPTURE_FLAG) != 0


cdef inline bint is_promotion(unsigned int move) noexcept nogil:
    return (move & _MOVE_PROMO_FLAG) != 0


cdef inline bint is_en_passant(unsigned int move) noexcept nogil:
    return move_flag(move) == _MOVE_EN_PASSANT


cdef inline bint is_castling(unsigned int move) noexcept nogil:
    cdef int flag = move_flag(move)
    return flag == _MOVE_CASTLE_KS or flag == _MOVE_CASTLE_QS


cpdef str move_to_uci(unsigned int move)

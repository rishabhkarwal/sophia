cdef unsigned long long KNIGHT_ATTACKS[64]
cdef unsigned long long KING_ATTACKS[64]
cdef unsigned long long WHITE_PAWN_ATTACKS[64]
cdef unsigned long long BLACK_PAWN_ATTACKS[64]
cdef unsigned long long BISHOP_MASKS[64]
cdef unsigned long long ROOK_MASKS[64]
cdef unsigned long long SQUARE_TO_BB[64]

cdef unsigned long long bishop_attacks(int sq, unsigned long long all_pieces) noexcept
cdef unsigned long long rook_attacks(int sq, unsigned long long all_pieces) noexcept

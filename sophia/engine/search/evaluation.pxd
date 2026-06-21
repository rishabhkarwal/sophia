from engine.board.state cimport State

cdef int MG_TABLE_C[16][64]
cdef int EG_TABLE_C[16][64]
cdef int PHASE_WEIGHTS_C[16]

cdef packed struct PawnEntry:
    unsigned long long key
    int                score

cdef class PawnHashTable:
    cdef PawnEntry*    table
    cdef public long long size
    cdef public unsigned long long mask
    cdef public long long dbg_hits
    cdef public long long dbg_misses

    cdef bint probe(self, unsigned long long key, int* out_score) noexcept
    cdef void store(self, unsigned long long key, int score) noexcept

cpdef int evaluate(State state, object pawn_hash_table=*)

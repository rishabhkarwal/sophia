from engine.board.state cimport State

cdef int MG_TABLE_C[16][64]
cdef int EG_TABLE_C[16][64]
cdef int PHASE_WEIGHTS_C[16]

cpdef int evaluate(State state, object pawn_hash_table=*)

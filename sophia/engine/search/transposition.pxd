# declaration header for transposition.pyx

cdef packed struct TTEntry:
    unsigned long long key
    unsigned int       move    # 0 = no move (None sentinel)
    int                score
    short              depth
    unsigned char      flag

cdef class TranspositionTable:
    cdef TTEntry*      table
    cdef public long long size
    cdef public unsigned long long mask
    cdef public int entries_count

    cdef bint probe(self, unsigned long long key,
                    short* out_depth, int* out_score,
                    unsigned char* out_flag, unsigned int* out_move) noexcept
    cdef void store(self, unsigned long long key, short depth, int score,
                    unsigned char flag, unsigned int move) noexcept

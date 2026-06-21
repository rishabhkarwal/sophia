# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True

from libc.stdlib cimport malloc, free, calloc
from libc.string cimport memset

FLAG_EXACT      = 0
FLAG_LOWERBOUND = 1
FLAG_UPPERBOUND = 2

# sentinel for "no move stored"
cdef unsigned int _NO_MOVE = 0


cdef class TranspositionTable:
    def __init__(self, size_mb: int = 64):
        cdef long long total_bytes, n, power
        # each entry is 20 bytes (8 + 4 + 4 + 2 + 1 + 1 pad = 20, packed = 19 but we use packed)
        total_bytes = <long long>size_mb * 1024 * 1024
        n = total_bytes // sizeof(TTEntry)
        if n < 1:
            n = 1

        power = 1
        while (power << 1) <= n:
            power <<= 1

        self.size = power
        self.mask = <unsigned long long>(power - 1)
        self.entries_count = 0
        # calloc zero-initialises — key=0 means empty (valid Zobrist keys are non-zero)
        self.table = <TTEntry*>calloc(power, sizeof(TTEntry))
        if not self.table:
            raise MemoryError(f"TranspositionTable: failed to allocate {size_mb} MB")

    def __dealloc__(self):
        if self.table:
            free(self.table)
            self.table = NULL


    cdef void store(self, unsigned long long key, short depth, int score,
                    unsigned char flag, unsigned int move) noexcept:
        cdef long long index
        cdef TTEntry* slot

        index = <long long>(key & self.mask)
        slot  = &self.table[index]

        if slot.key == 0:
            self.entries_count += 1

        # replace if: empty slot, collision, or same position at equal/better depth
        if slot.key == 0 or slot.key != key or depth >= slot.depth:
            slot.key   = key
            slot.move  = move
            slot.score = score
            slot.depth = depth
            slot.flag  = flag

    # fills output pointers, returns True on hit
    cdef bint probe(self, unsigned long long key,
                    short* out_depth, int* out_score,
                    unsigned char* out_flag, unsigned int* out_move) noexcept:
        cdef long long index
        cdef TTEntry* slot

        index = <long long>(key & self.mask)
        slot  = &self.table[index]

        if slot.key == key and slot.key != 0:
            out_depth[0] = slot.depth
            out_score[0] = slot.score
            out_flag[0]  = slot.flag
            out_move[0]  = slot.move
            return True
        return False


    def store_entry(self, key: int, depth: int, score: int, flag: int, best_move):
        cdef unsigned int move
        move = <unsigned int>best_move if best_move is not None else _NO_MOVE
        self.store(<unsigned long long>key, <short>depth, <int>score,
                   <unsigned char>flag, move)

    def probe_entry(self, key: int):
        cdef short depth
        cdef int score
        cdef unsigned char flag
        cdef unsigned int move
        if self.probe(<unsigned long long>key, &depth, &score, &flag, &move):
            return (key, <int>depth, score, <int>flag, move if move != _NO_MOVE else None)
        return None

    def sample_stats(self, int max_samples=100_000):
        cdef long long sample_target, step, i, total
        cdef long long exact, bound, empty
        cdef TTEntry* slot

        sample_target = max_samples
        if sample_target < 1:
            sample_target = 1
        if sample_target > self.size:
            sample_target = self.size

        step = self.size // sample_target
        if step < 1:
            step = 1

        total = 0
        exact = 0
        bound = 0
        empty = 0

        for i in range(0, self.size, step):
            slot = &self.table[i]
            total += 1
            if slot.key == 0:
                empty += 1
            elif slot.flag == FLAG_EXACT:
                exact += 1
            else:
                bound += 1

        return total, exact, bound, empty

    def clear(self):
        memset(self.table, 0, self.size * sizeof(TTEntry))
        self.entries_count = 0

    def get_hashfull(self) -> int:
        return int(self.entries_count / self.size * 1000)

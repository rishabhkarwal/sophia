# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True

from libc.stdint cimport uint32_t, uint64_t

from engine.board.state cimport State
from engine.board.move_exec cimport make_move, unmake_move
from engine.moves.generator cimport MoveList, generate_legal_move_list


cdef struct PerftTTEntry:
    uint64_t key
    uint64_t nodes
    uint32_t depth
    uint32_t epoch


DEF TABLE_SIZE = 1 << 22
cdef uint64_t TABLE_MASK = TABLE_SIZE - 1
cdef PerftTTEntry transposition_table[TABLE_SIZE]
cdef uint32_t tt_epoch = 0


cdef void _start_perft_run():
    global tt_epoch
    tt_epoch += 1
    if tt_epoch == 0:
        tt_epoch = 1


cdef uint64_t _count_legal_moves(State state):
    cdef MoveList moves

    generate_legal_move_list(state, &moves, False)
    return moves.count


cdef uint64_t _perft(State state, int depth):
    cdef MoveList moves
    cdef unsigned int move
    cdef uint64_t nodes = 0
    cdef uint64_t key, index
    cdef PerftTTEntry* entry
    cdef int i

    if depth <= 0: return 1
    if depth == 1: return _count_legal_moves(state)

    key = <uint64_t>state.hash
    index = key & TABLE_MASK
    entry = &transposition_table[index]

    if entry.epoch == tt_epoch and entry.key == key and entry.depth == <uint32_t>depth:
        return entry.nodes

    generate_legal_move_list(state, &moves, False)

    for i in range(moves.count):
        move = moves.moves[i]
        make_move(state, move)
        nodes += _perft(state, depth - 1)
        unmake_move(state, move)

    if entry.epoch != tt_epoch or entry.depth <= <uint32_t>depth:
        entry.key = key
        entry.nodes = nodes
        entry.depth = <uint32_t>depth
        entry.epoch = tt_epoch

    return nodes


cpdef uint64_t run_perft(State state, int depth):
    if depth < 0:
        raise ValueError("depth cannot be negative")

    _start_perft_run()
    return _perft(state, depth)


cpdef list run_perft_divide(State state, int depth):
    cdef MoveList moves
    cdef unsigned int move
    cdef uint64_t nodes
    cdef list rows = []
    cdef int i

    if depth <= 0:
        return rows

    _start_perft_run()
    generate_legal_move_list(state, &moves, False)

    for i in range(moves.count):
        move = moves.moves[i]
        make_move(state, move)
        nodes = 1 if depth == 1 else _perft(state, depth - 1)
        rows.append((move, nodes))
        unmake_move(state, move)

    return rows

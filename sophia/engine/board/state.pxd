# declaration header for state.pyx.
# other .pyx files do: cimport engine.board.state as _state (or `from ... cimport State`)
# to get c-level access to all typed fields without python dispatch

cdef enum:
    STATE_STACK_CAPACITY = 16384


cdef packed struct UndoInfo:
    int captured_piece
    int old_castling
    int old_ep
    int old_halfmove
    unsigned long long old_hash
    int old_mg
    int old_eg
    int old_phase
    unsigned long long old_w_passed
    unsigned long long old_b_passed
    int old_last_moved


cdef class State:
    cdef public unsigned long long bitboards[16]
    cdef public int board[64]
    cdef public int piece_counts[16]

    cdef public bint is_white
    cdef public int  castling_rights
    cdef public int  en_passant_square
    cdef public int  halfmove_clock
    cdef public int  fullmove_number

    cdef public unsigned long long hash
    cdef public int  mg_score
    cdef public int  eg_score
    cdef public int  phase

    cdef public unsigned long long white_passed_pawns
    cdef public unsigned long long black_passed_pawns

    cdef public int  last_moved_piece_sq

    cdef UndoInfo* undo_stack
    cdef unsigned long long* history
    cdef public Py_ssize_t stack_len
    cdef public Py_ssize_t history_len
    cdef public Py_ssize_t stack_capacity

    cpdef State clone(self)

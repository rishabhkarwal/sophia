# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True

from libc.string cimport memcpy, memset

from engine.core.constants import NULL as _NULL

cdef class State:
    def __cinit__(self):
        """zero-initialise all C arrays before __init__ can run"""
        memset(self.bitboards,    0,           sizeof(self.bitboards))
        # evil memory trick basically
        memset(self.board,        -1 & 0xFF,   sizeof(self.board)) # fill 0xFF = -1 as signed byte
        memset(self.piece_counts, 0,           sizeof(self.piece_counts))

    def __init__(self,
                 bitboards=None,
                 board=None,
                 piece_counts=None,
                 bint is_white=True,
                 int castling_rights=0,
                 int en_passant_square=-1,
                 int halfmove_clock=0,
                 int fullmove_number=1,
                 history=None):
        cdef int i

        if bitboards is not None:
            for i in range(16):
                self.bitboards[i] = <unsigned long long>bitboards[i]

        if board is not None:
            for i in range(64):
                self.board[i] = <int>board[i]

        if piece_counts is not None:
            for i in range(16):
                self.piece_counts[i] = <int>piece_counts[i]

        self.is_white            = is_white
        self.castling_rights     = castling_rights
        self.en_passant_square   = en_passant_square
        self.halfmove_clock      = halfmove_clock
        self.fullmove_number     = fullmove_number

        self.hash                = 0
        self.mg_score            = 0
        self.eg_score            = 0
        self.phase               = 0
        self.white_passed_pawns  = 0
        self.black_passed_pawns  = 0
        self.last_moved_piece_sq = _NULL

        self.history       = list(history) if history is not None else []
        self.context_stack = []

    cpdef State clone(self):
        """fast explicit clone"""
        cdef State s = State.__new__(State)

        memcpy(s.bitboards,    self.bitboards,    sizeof(self.bitboards))
        memcpy(s.board,        self.board,        sizeof(self.board))
        memcpy(s.piece_counts, self.piece_counts, sizeof(self.piece_counts))

        s.is_white            = self.is_white
        s.castling_rights     = self.castling_rights
        s.en_passant_square   = self.en_passant_square
        s.halfmove_clock      = self.halfmove_clock
        s.fullmove_number     = self.fullmove_number
        s.hash                = self.hash
        s.mg_score            = self.mg_score
        s.eg_score            = self.eg_score
        s.phase               = self.phase
        s.white_passed_pawns  = self.white_passed_pawns
        s.black_passed_pawns  = self.black_passed_pawns
        s.last_moved_piece_sq = self.last_moved_piece_sq

        s.history       = list(self.history)
        s.context_stack = list(self.context_stack)

        return s

    def get_piece_at(self, int square):
        cdef int p = self.board[square]
        return p if p != _NULL else None

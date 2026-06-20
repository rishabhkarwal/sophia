# declaration header for search.pyx

from engine.board.state cimport State
from engine.search.transposition cimport TranspositionTable
from engine.search.ordering cimport MoveOrdering

cdef class SearchEngine:
    cdef public int   nodes_searched
    cdef public int   depth_reached
    cdef public int   seldepth
    cdef public int   tbhits
    cdef public double start_time
    cdef public double hard_time_limit
    cdef public double soft_time_limit
    cdef public int   check_interval
    cdef public int   aspiration_current
    cdef public int   aspiration_stability_count
    cdef public int   aspiration_min
    cdef public int   aspiration_max
    cdef public int   time_limit
    cdef public int   root_colour

    cdef public TranspositionTable tt
    cdef public object pawn_hash
    cdef public object syzygy
    cdef public MoveOrdering ordering
    cdef public object stop_flag
    cdef public object ponder_move
    cdef public object nodes_limit
    cdef public object opponent_time_ms

    # debug counters
    cdef public int dbg_nmp_attempts
    cdef public int dbg_nmp_cutoffs
    cdef public int dbg_rfp_attempts
    cdef public int dbg_rfp_cutoffs
    cdef public int dbg_snmp_attempts
    cdef public int dbg_snmp_cutoffs
    cdef public int dbg_razor_attempts
    cdef public int dbg_razor_cutoffs
    cdef public int dbg_futility_skips
    cdef public int dbg_lmp_skips
    cdef public int dbg_lmr_reductions
    cdef public int dbg_lmr_researches
    cdef public int dbg_pvs_researches
    cdef public int dbg_check_extensions
    cdef public int dbg_iid_triggers
    cdef public int dbg_iid_tt_hits
    cdef public int dbg_tt_exact_used
    cdef public int dbg_tt_bound_cutoff
    cdef public int dbg_tt_bound_noncutoff
    cdef public int dbg_tt_shallow
    cdef public int dbg_qnodes
    cdef public int dbg_qstandpat
    cdef public int dbg_qdelta_prunes
    cdef public object dbg_beta_cutoff_idx
    cdef public int dbg_cutoff_by_tt
    cdef public int dbg_cutoff_by_killer
    cdef public int dbg_cutoff_by_cap
    cdef public int dbg_cutoff_by_quiet
    cdef public int dbg_asp_fail_low
    cdef public int dbg_asp_fail_high
    cdef public int dbg_asp_fail_both
    cdef public int dbg_repetition_draws
    cdef public int dbg_fifty_move_draws
    cdef public int dbg_insuf_mat_draws
    cdef public int dbg_syzygy_probes
    cdef public int dbg_syzygy_hits

    cdef int _alpha_beta(self, State state, int depth, int alpha, int beta, int ply,
                         object previous_move, bint allow_null, bint is_pv) except? -32768
    cdef int _quiescence(self, State state, int alpha, int beta, int ply) except? -32768

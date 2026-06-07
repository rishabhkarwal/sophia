import time
from engine.board.move_exec import make_move, unmake_move
from engine.moves.generator import get_legal_moves, generate_pseudo_legal_moves
from engine.moves.legality import is_in_check
from engine.search.evaluation import evaluate as static_eval, MAX_PHASE, PawnHashTable
from engine.core.move import move_to_uci
from engine.search.utils import state_to_board
from engine.uci.utils import send_command
from engine.search.see import see_full, see_fast
from engine.search.ordering import MoveOrdering, pick_next_move
import engine.core.constants as _const
from engine.core.constants import (
    WHITE, BLACK, NULL,
    WP, WN, WB, WR, WQ, WK,
    BP, BN, BB, BR, BQ, BK,
    PIECE_STR, PIECE_VALUES, PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
    MASK_SOURCE,
)
from engine.core.move import SHIFT_TARGET, SHIFT_FLAG, SQUARE_NAMES
from math import exp

def _get_score(state):
    return static_eval(state)

def evaluate(state):
    """Prints the static evaluation of the current state"""
    score = _get_score(state)
    
    mg_phase = min(state.phase, MAX_PHASE)
    eg_phase = MAX_PHASE - mg_phase
    
    send_command(f"Evaluation: {score / 100 :.1f}")
    send_command(f"Phase: {state.phase}/{MAX_PHASE}")
    send_command(f"MG Score: {state.mg_score :,} (Weight: {mg_phase / MAX_PHASE * 100 :.1f}%)")
    send_command(f"EG Score: {state.eg_score :,} (Weight: {eg_phase / MAX_PHASE * 100 :.1f}%)")


def perft(state, depth):
    """Runs Perft"""
    def _perft_recursive(state, depth):
        if depth == 0: return 1
        
        nodes = 0
        moves = generate_pseudo_legal_moves(state)
        
        for move in moves:
            make_move(state, move)
            if not is_in_check(state, not state.is_white):
                nodes += _perft_recursive(state, depth - 1)
            unmake_move(state, move)
            
        return nodes
    
    t_start = time.time()
    total_nodes = 0
    
    moves = get_legal_moves(state)
    
    for move in moves:
        make_move(state, move)
        nodes = _perft_recursive(state, depth - 1)
        unmake_move(state, move)
        
        total_nodes += nodes
        send_command(f"{move_to_uci(move)}: {nodes :,}")
        
    t_end = time.time()
    dt = t_end - t_start
    nps = int(total_nodes / dt) if dt > 0 else 0
    
    send_command(f"\nNodes: {total_nodes :,}")
    send_command(f"Time: {dt :.3f} s")
    send_command(f"NPS: {nps :,}\n")


def draw(state):
    send_command("\n")
    
    for rank in range(7, -1, -1):
        line = f" {rank + 1}   "
        for file in range(8):
            square = rank * 8 + file
            piece = state.board[square]
            
            symbol = PIECE_STR[piece]
            if piece == NULL:
                if (rank + file) & 1:
                    symbol = '.' # dark empty square (assumes dark terminal)
                else:
                    symbol = ' '
            line += f" {symbol} "
            
        send_command(line)
    
    caption = '\n' + '      ' + '  '.join(rank for rank in 'abcdefgh')
    send_command(caption)
    
    side = "White" if state.is_white else "Black"
    send_command(f"\nTurn: {side}")
    send_command(f"Hash: {state.hash:016x}\n")

def _clamp_percentage(percentage):
    return max(0.0, min(100.0, percentage))

def _get_win_percentage(state):
    centipawns = _get_score(state)
    win = 50 + 50 * (2 / (1 + exp(-0.00368208 * centipawns)) - 1)
    return _clamp_percentage(win)

def _get_move_accuracy(win_percent_before, win_percent_after):
    accuracy = 103.1668 * exp(-0.04354 * (win_percent_before - win_percent_after)) - 3.1669
    return _clamp_percentage(accuracy)

def win_percentage(state):
    send_command(f'{_get_win_percentage(state) :.2f}%')
    send_command("\n")

def move_accuracy(state, move_str):
    win_percent_before = _get_win_percentage(state)

    legal_moves = get_legal_moves(state)
    is_valid = False
    for legal_move in legal_moves:      
        s_move = move_to_uci(legal_move)
        
        if s_move == move_str.lower():
            make_move(state, legal_move)
            opp_win_percent = _get_win_percentage(state)
            win_percent_after = 100.0 - opp_win_percent
            unmake_move(state, legal_move)
            is_valid = True
            break
    if not is_valid: send_command(f'error: invalid move {move_str}\n')
    else: send_command(f'{_get_move_accuracy(win_percent_before, win_percent_after) :.2f}%\n')

def legal_moves(state):
    """Prints all legal moves in the current position"""
    moves = get_legal_moves(state)
    move_strings = [move_to_uci(m) for m in moves]
    move_strings.sort()
    
    send_command(f"count: {len(moves)}")
    send_command(f"moves: {' '.join(move_strings)}\n")

def see(state, move_str):
    moves = get_legal_moves(state)
    found = next((m for m in moves if move_to_uci(m) == move_str.lower()), None)
    if not found: send_command(f"error: move '{move_str.lower()}' is not legal\n"); return
    send_command(f"see {move_str.lower()}: {see_full(state, found)}\n")

def eval_breakdown(state):
    old = _const.DEBUG_EVAL
    _const.DEBUG_EVAL = True
    static_eval(state, PawnHashTable(4))
    _const.DEBUG_EVAL = old
    send_command("")

def debug_toggle():
    _const.DEBUG = not _const.DEBUG
    send_command(f"DEBUG = {_const.DEBUG}\n")

def debug_eval_toggle():
    _const.DEBUG_EVAL = not _const.DEBUG_EVAL
    send_command(f"DEBUG_EVAL = {_const.DEBUG_EVAL}\n")

def order_moves(state):
    ordering = MoveOrdering()
    scored = sorted(
        [(ordering.get_move_score(m, None, None, state, 1, None, None), move_to_uci(m)) for m in get_legal_moves(state)],
        reverse=True
    )
    send_command(f"Move ordering ({len(scored)} moves):")
    for score, uci in scored: send_command(f"  {uci}  score={score}")
    send_command("")

def history_top(ordering, n=10):
    entries = sorted(
        [(ordering.history_table[f][t], f"{SQUARE_NAMES[f]}{SQUARE_NAMES[t]}")
         for f in range(64) for t in range(64) if ordering.history_table[f][t] > 0],
        reverse=True
    )
    send_command(f"Top {n} history entries:")
    for val, sq in entries[:n]: send_command(f"  {sq}  {val}")
    send_command("")

def tt_stats(tt):
    step = max(1, tt.size // min(tt.size, 100_000))
    entries = [tt.table[i] for i in range(0, tt.size, step)]
    exact = sum(1 for e in entries if e and e.flag == 0)
    bound = sum(1 for e in entries if e and e.flag != 0)
    empty = sum(1 for e in entries if e is None)
    total = exact + bound + empty
    send_command(f"TT stats (sampled {total} of {tt.size}):")
    send_command(f"  hashfull: {tt.get_hashfull()}/1000")
    send_command(f"  exact:    {exact} ({100*exact//total if total else 0}%)")
    send_command(f"  bound:    {bound} ({100*bound//total if total else 0}%)")
    send_command(f"  empty:    {empty} ({100*empty//total if total else 0}%)")
    send_command("")
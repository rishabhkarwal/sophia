import time
from engine.board.move_exec import make_move, unmake_move
from engine.moves.generator import get_legal_moves, generate_pseudo_legal_moves
from engine.moves.legality import is_in_check
from engine.search.evaluation import evaluate as static_eval, MAX_PHASE
from engine.core.move import move_to_uci
from engine.search.utils import state_to_board
from engine.uci.utils import send_command
from engine.search.see import see_full
from engine.core.constants import (
    WHITE, BLACK, NULL,
    WP, WN, WB, WR, WQ, WK,
    BP, BN, BB, BR, BQ, BK,
    PIECE_STR
)
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
    """Runs SEE on a specific move"""
    target_move_str = move_str.lower()
    moves = get_legal_moves(state)
    
    found_move = None
    for move in moves:
        if move_to_uci(move) == target_move_str:
            found_move = move
            break
    
    if found_move is None:
        send_command(f"error: move '{target_move_str}' is not legal or valid")
        return

    score = see_full(state, found_move)
    send_command(f"see {target_move_str}: {score}\n")
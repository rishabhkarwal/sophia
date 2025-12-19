from engine.board.state import State
from engine.core.move import Move, CAPTURE, PROMOTION, EP_CAPTURE, CASTLE
from engine.core.constants import (
    WHITE, BLACK, NO_SQUARE,
    CASTLE_WK, CASTLE_WQ, CASTLE_BK, CASTLE_BQ,
    WHITE_PIECES, BLACK_PIECES, ALL_PIECES,
    A1, H1, A8, H8, E1, C1, G1, E8, C8, G8,
    F1, D1, F8, D8
)
from engine.core.bitboard_utils import BitBoard
from engine.core.zobrist import compute_hash

def get_position_id(bitboards, player, castling, ep) -> str:
    """Generate a unique string identifier for the current position (for draw detection)"""
    pieces_str = ""
    for piece in ALL_PIECES:
        pieces_str += f"{piece}:{bitboards[piece]}|"
    
    return f"{pieces_str}T:{player}C:{castling}EP:{ep}"

def is_threefold_repetition(state: State) -> bool:
    """Check if the current position has occurred 3 times"""
    if not state.history:
        return False

    last_entry = state.history[-1]
    if '#' not in last_entry:
        return False
        
    current_id = last_entry.split('#')[1]
    
    count = 0
    for entry in reversed(state.history):
        if '#' in entry:
            if entry.split('#')[1] == current_id:
                count += 1

        if count >= 3: return True
    return False

def make_move(state: State, move: Move) -> State:
    """Apply a move and return a new game state"""
    new_bitboards = state.bitboards.copy()
    
    if state.player == WHITE:
        active = WHITE_PIECES
        opponent = BLACK_PIECES
    else:
        active = BLACK_PIECES
        opponent = WHITE_PIECES
    
    start_mask = 1 << move.start
    target_mask = 1 << move.target
    
    moving_piece = None
    for piece in active:
        if new_bitboards.get(piece, 0) & start_mask:
            moving_piece = piece
            break
    
    # handle captures
    if move.flag & CAPTURE:
        if move.flag & EP_CAPTURE:
            ep_offset = -8 if state.player == WHITE else 8
            capture_sq = move.target + ep_offset
            enemy_pawn = 'p' if state.player == WHITE else 'P'
            new_bitboards[enemy_pawn] = BitBoard.clear_bit(new_bitboards[enemy_pawn], capture_sq)
        else:
            for piece in opponent:
                if new_bitboards.get(piece, 0) & target_mask:
                    new_bitboards[piece] = BitBoard.clear_bit(new_bitboards[piece], move.target)
                    break
    
    new_bitboards[moving_piece] = BitBoard.clear_bit(new_bitboards[moving_piece], move.start)
    
    if move.flag & PROMOTION:
        promo_char = move.promo_type if move.promo_type else 'q'
        target_piece = promo_char.upper() if state.player == WHITE else promo_char.lower()
    else:
        target_piece = moving_piece
    
    new_bitboards[target_piece] = BitBoard.set_bit(new_bitboards.get(target_piece, 0), move.target)
    
    # handle castling
    if move.flag & CASTLE:
        rook_key = 'R' if state.player == WHITE else 'r'
        if move.target == G1:
            new_bitboards[rook_key] = BitBoard.clear_bit(new_bitboards[rook_key], H1)
            new_bitboards[rook_key] = BitBoard.set_bit(new_bitboards[rook_key], F1)
        elif move.target == C1:
            new_bitboards[rook_key] = BitBoard.clear_bit(new_bitboards[rook_key], A1)
            new_bitboards[rook_key] = BitBoard.set_bit(new_bitboards[rook_key], D1)
        elif move.target == G8:
            new_bitboards[rook_key] = BitBoard.clear_bit(new_bitboards[rook_key], H8)
            new_bitboards[rook_key] = BitBoard.set_bit(new_bitboards[rook_key], F8)
        elif move.target == C8:
            new_bitboards[rook_key] = BitBoard.clear_bit(new_bitboards[rook_key], A8)
            new_bitboards[rook_key] = BitBoard.set_bit(new_bitboards[rook_key], D8)
    
    new_bitboards['white'] = 0
    for piece in WHITE_PIECES: new_bitboards['white'] |= new_bitboards.get(piece, 0)
    
    new_bitboards['black'] = 0
    for piece in BLACK_PIECES: new_bitboards['black'] |= new_bitboards.get(piece, 0)
    
    new_bitboards['all'] = new_bitboards['white'] | new_bitboards['black']
    
    new_castling = state.castling
    
    if moving_piece == 'K': new_castling &= ~(CASTLE_WK | CASTLE_WQ)
    elif moving_piece == 'k': new_castling &= ~(CASTLE_BK | CASTLE_BQ)
    
    rook_rights = {A1: CASTLE_WQ, H1: CASTLE_WK, A8: CASTLE_BQ, H8: CASTLE_BK}
    if move.start in rook_rights: new_castling &= ~rook_rights[move.start]
    if move.target in rook_rights: new_castling &= ~rook_rights[move.target]
    
    new_ep = NO_SQUARE
    is_pawn = moving_piece.lower() == 'p'
    
    if is_pawn and abs(move.start - move.target) == 16:
        new_ep = (move.start + move.target) // 2
    
    if is_pawn or (move.flag & CAPTURE): new_halfmove = 0
    else: new_halfmove = state.halfmove_clock + 1
    
    new_fullmove = state.fullmove_number + (1 if state.player == BLACK else 0)

    position_id = get_position_id(new_bitboards, not(state.player), new_castling, new_ep)
    history_entry = f"{move}#{position_id}"
    
    # Create new state (Post init will calculate Zobrist hash automatically)
    return State(new_bitboards, not(state.player), new_castling, new_ep, new_halfmove, new_fullmove, state.history + [history_entry])
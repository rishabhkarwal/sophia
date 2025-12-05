from typing import Optional, List
from .state import State
from .move import Move, CAPTURE, PROMOTION, EP_CAPTURE, CASTLE
from .constants import (
    WHITE, BLACK, NO_SQUARE,
    CASTLE_WK, CASTLE_WQ, CASTLE_BK, CASTLE_BQ,
    WHITE_PIECES, BLACK_PIECES,
    A1, H1, A8, H8, E1, C1, G1, E8, C8, G8,
    F1, D1, F8, D8
)
from .utils import BitBoard

from .move_gen import generate_moves, get_attackers

def make_move(state: State, move: Move) -> State:
    """Apply a move and return a new game state (without validating legality)"""
    # create new bitboard dictionary (shallow copy for speed)
    new_bitboards = state.bitboards.copy()
    
    if state.player == WHITE:
        active = WHITE_PIECES
        opponent = BLACK_PIECES
    else:
        active = BLACK_PIECES
        opponent = WHITE_PIECES
    
    # square bitmasks
    start_mask = 1 << move.start
    target_mask = 1 << move.target
    
    # identify the moving piece
    moving_piece = None
    for piece in active:
        if new_bitboards.get(piece, 0) & start_mask:
            moving_piece = piece
            break
    
    # handle captures
    if move.flag & CAPTURE:
        if move.flag & EP_CAPTURE:
            # en passant
            ep_offset = -8 if state.player == WHITE else 8
            capture_sq = move.target + ep_offset
            enemy_pawn = 'p' if state.player == WHITE else 'P'
            new_bitboards[enemy_pawn] = BitBoard.clear_bit(new_bitboards[enemy_pawn], capture_sq)
        else:
            # normal capture: remove enemy piece from target square
            for piece in opponent:
                if new_bitboards.get(piece, 0) & target_mask:
                    new_bitboards[piece] = BitBoard.clear_bit(new_bitboards[piece], move.target)
                    break
    
    # remove piece from start square
    new_bitboards[moving_piece] = BitBoard.clear_bit(new_bitboards[moving_piece], move.start)
    
    # add piece to target square
    if move.flag & PROMOTION:
        # promote to specified piece (default to queen)
        promo_char = move.promo_type if move.promo_type else 'q'
        target_piece = promo_char.upper() if state.player == WHITE else promo_char.lower()
    else:
        target_piece = moving_piece
    
    new_bitboards[target_piece] = BitBoard.set_bit(new_bitboards.get(target_piece, 0), move.target)
    
    # handle castling (move the rook)
    if move.flag & CASTLE:
        rook_key = 'R' if state.player == WHITE else 'r'
        # determine rook movement based on king's target square
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
    
    # update occupancy bitboards
    new_bitboards['white'] = 0
    for piece in WHITE_PIECES: new_bitboards['white'] |= new_bitboards.get(piece, 0)
    
    new_bitboards['black'] = 0
    for piece in BLACK_PIECES: new_bitboards['black'] |= new_bitboards.get(piece, 0)
    
    new_bitboards['all'] = new_bitboards['white'] | new_bitboards['black']
    
    # update castling rights
    new_castling = state.castling
    
    # king moves remove all castling rights for that side
    if moving_piece == 'K': new_castling &= ~(CASTLE_WK | CASTLE_WQ)
    elif moving_piece == 'k': new_castling &= ~(CASTLE_BK | CASTLE_BQ)
    
    # rook moves remove castling rights for that rook
    rook_rights = {A1: CASTLE_WQ, H1: CASTLE_WK, A8: CASTLE_BQ, H8: CASTLE_BK}
    
    if move.start in rook_rights: new_castling &= ~rook_rights[move.start]
    
    # capturing a rook removes that rook's castling right
    if move.target in rook_rights: new_castling &= ~rook_rights[move.target]
    
    # set en-passant target square
    new_ep = NO_SQUARE
    is_pawn = moving_piece.lower() == 'p'
    
    # double pawn push creates en-passant opportunity
    if is_pawn and abs(move.start - move.target) == 16:
        new_ep = (move.start + move.target) // 2
    
    # update move counters
    if is_pawn or (move.flag & CAPTURE): new_halfmove = 0
    else: new_halfmove = state.halfmove_clock + 1
    
    # fullmove number increments after black's turn
    new_fullmove = state.fullmove_number + (1 if state.player == BLACK else 0)
    
    return State(new_bitboards, not(state.player), new_castling, new_ep, new_halfmove, new_fullmove, state.history + [str(move)])

def is_in_check(state: State, colour: int) -> int:
    """Check if the king of the specified colour is under attack"""
    
    # find the king
    king_key = 'K' if colour == WHITE else 'k'
    king_bb = state.bitboards.get(king_key, 0)
    
    # no king found (should never happen in valid positions)
    # if not king_bb: return 0
    
    # get the square the king is on
    king_sq = next(BitBoard.bit_scan(king_bb))
    
    # check if opponent is attacking the king square
    attacker_colour = BLACK if colour == WHITE else WHITE
    
    return get_attackers(state, king_sq, attacker_colour)

def is_legal(state: State, move: Move) -> bool:
    """Check if a move is legal by verifying it doesn't leave own king in check"""
    # make the move
    new_state = make_move(state, move)
    # check if our king is in check in the resulting position
    return not is_in_check(new_state, state.player)

def get_legal_moves(state: State) -> list:
    """Generate all legal moves for the current position"""
    pseudo_legal = generate_moves(state)
    legal = []
    
    for move in pseudo_legal:
        if is_legal(state, move):
            legal.append(move)
    
    return legal

def is_checkmate(state: State) -> bool:
    """Check if the current position is checkmate"""
    # must be in check
    if not is_in_check(state, state.player): return False
    # must have no legal moves
    legal_moves = generate_legal_moves(state)
    return len(legal_moves) == 0

def is_stalemate(state: State) -> bool:
    """Check if the current position is stalemate"""
    # must NOT be in check
    if is_in_check(state, state.player): return False
    # must have no legal moves
    legal_moves = generate_legal_moves(state)
    return len(legal_moves) == 0
from dataclasses import dataclass
from typing import Optional

QUIET = 0 # 0000: normal move
CAPTURE = 1 # 0001: captures enemy piece
PROMOTION = 2 # 0010: pawn promotion
EP_CAPTURE = 4 # 0100: en-passant capture
CASTLE = 8 # 1000: castling move

@dataclass(frozen=True, slots=True)
class Move:
    start: int
    target: int
    flag: int = QUIET
    promo_type: Optional[str] = None

    @property
    def is_capture(self) -> bool:
        """True if move captures a piece (normal capture or en passant)"""
        return bool(self.flag & (CAPTURE | EP_CAPTURE))
    
    @property
    def is_promotion(self) -> bool:
        """True if move is a pawn promotion"""
        return bool(self.flag & PROMOTION)
    
    @property
    def is_en_passant(self) -> bool:
        """True if move is en passant capture"""
        return bool(self.flag & EP_CAPTURE)
    
    @property
    def is_castle(self) -> bool:
        """True if move is castling"""
        return bool(self.flag & CASTLE)
    
    @property
    def is_quiet(self) -> bool:
        """True if move has no special flags"""
        return self.flag == QUIET

    def __str__(self):
        """Convert move object to string e.g. 'e2e4'"""

        # Removed for UCI format
        """
        # Handle Castling Notation
        if self.flag & CASTLE:
            # If target file > start file (e.g., e1 -> g1), it's Kingside
            if (self.target % 8) > (self.start % 8):
                return "O-O"
            else:
                return "O-O-O"
        """

        files = "abcdefgh"
        
        # Decode Start Square
        f_file, f_rank = self.start % 8, self.start // 8
        start_sq = f"{files[f_file]}{f_rank + 1}"
        
        # Decode Target Square
        t_file, t_rank = self.target % 8, self.target // 8
        target_sq = f"{files[t_file]}{t_rank + 1}"
        
        move_str = start_sq + target_sq
        
        # Append promotion character if applicable
        if self.flag & PROMOTION:
            # Default to 'q' if promo_type is None (safety check)
            p_char = self.promo_type if self.promo_type else 'q'
            move_str += p_char.lower()
            
        return move_str
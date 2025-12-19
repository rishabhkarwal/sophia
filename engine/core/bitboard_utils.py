'''
56 57 58 59 60 61 62 63
48 49 50 51 52 53 54 55
40 41 42 43 44 45 46 47
32 33 34 35 36 37 38 39
24 25 26 27 28 29 30 31
16 17 18 19 20 21 22 23
 8  9 10 11 12 13 14 15
 0  1  2  3  4  5  6  7
'''

class BitBoard:
    @staticmethod
    def pprint(bitboard, piece = '1'):
        [print(''.join([f'{piece}  ' if (bitboard & (1 << rank * 8 + file)) else '·  ' for file in range(8)])) for rank in range(7, -1, -1)], print()
    
    @staticmethod
    def bit_scan(bitboard):
        while bitboard:
            lsb = bitboard & -bitboard  # isolate the least significant bit
            yield lsb.bit_length() - 1  # return the index of the bit
            bitboard &= bitboard - 1  # clear the least significant bit

    @staticmethod
    def set_bit(bitboard, square):
        """Sets bit at 'square' to 1"""
        return bitboard | (1 << square)

    @staticmethod
    def clear_bit(bitboard, square):
        """Sets bit at 'square' to 0"""
        return bitboard & ~(1 << square)

    @staticmethod
    def check_bit(bitboard, square):
        """Returns 1 if bit at 'square' is set"""
        return (bitboard >> square) & 1

    @staticmethod
    def algebraic_to_bit(square):
        return (int(square[1]) - 1) * 8 + ord(square[0].lower()) - ord('a')
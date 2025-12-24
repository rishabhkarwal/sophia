def bit_scan(bitboard):
    """Returns a list of square indices where bits are set to 1"""
    squares = []
    while bitboard:
        lsb = bitboard & -bitboard  # isolate lsb
        squares.append(lsb.bit_length() - 1)  # get index
        bitboard &= bitboard - 1  # reset lsb
    return squares

def pprint(bitboard, piece='1'):
    """Pretty-print a bitboard"""
    for rank in range(7, -1, -1):
        row = []
        for file in range(8):
            if bitboard & (1 << (rank * 8 + file)):
                row.append(f'{piece}  ')
            else:
                row.append('.  ')
        print(''.join(row))
    print()

def set_bit(bitboard, square):
    """Sets bit at 'square' to 1"""
    return bitboard | (1 << square)

def clear_bit(bitboard, square):
    """Sets bit at 'square' to 0"""
    return bitboard & ~(1 << square)

def check_bit(bitboard, square):
    """Returns True if bit at 'square' is set"""
    return (bitboard >> square) & 1

def sq_to_bb(square):
    """Converts a square index to its bitboard representation"""
    return 1 << square

def algebraic_to_bit(square):
    """Convert algebraic notation to bit index"""
    file, rank = square[0], square[1]
    return (int(rank) - 1) * 8 + ord(file.lower()) - ord('a')

def bit_to_algebraic(square):
    """Convert bit index to algebraic notation"""
    file, rank = square % 8, square // 8
    return f"{'abcdefgh'[file]}{rank + 1}"
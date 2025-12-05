import os

UNICODE_PIECES = {
    'P': '♟', 'N': '♞', 'B': '♝', 'R': '♜', 'Q': '♛', 'K': '♚',
    'p': '♙', 'n': '♘', 'b': '♗', 'r': '♖', 'q': '♕', 'k': '♔',
    '': '·'
}

class GUI:
    def __init__(self):
        pass

    def clear_screen(self):
        """Clears the terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_board(self, state):
        h, v = '───', '│'
        
        print(f"  ╭{h}" + (f"┬{h}" * 7) + f"╮") # top border

        for rank in range(7, -1, -1):
            row_str = f"{rank + 1} {v}"
            for file in range(8):
                sq = rank * 8 + file
                char = UNICODE_PIECES.get(state.get_piece_at(sq), ' ')
                row_str += f" {char} {v}"
            print(row_str)

            if rank > 0: print(f"  ├{h}" + (f"┼{h}" * 7) + f"┤") # middle rows

        print(f"  ╰{h}" + (f"┴{h}" * 7) + f"╯") # bottom border
        print("    a   b   c   d   e   f   g   h\n")

    def format_move_history(self, moves):
        lines = []
        width = max(3, len(str((len(moves) + 1) // 2)))
        for i in range(0, len(moves), 2):
            move_number = i // 2 + 1
            white = moves[i]
            black = moves[i + 1] if i + 1 < len(moves) else ""
            lines.append(f"{move_number:>{width}}. {white:<6} {black}".rstrip())

        return "\n".join(lines)
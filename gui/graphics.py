import chess, os
from gui.console import log_info

PIECES = {
    'P': '♟', 'N': '♞', 'B': '♝', 'R': '♜', 'Q': '♛', 'K': '♚',
    'p': '♙', 'n': '♘', 'b': '♗', 'r': '♖', 'q': '♕', 'k': '♔',
    'light': '·', 'dark' : ' '
}

class Display:
    @staticmethod
    def clear_screen():
        os.system('cls' if os.name == 'nt' else 'clear')

    @staticmethod
    def _get_material_balance(board: chess.Board) -> int:
        values = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9}
        score = 0
        for pt, val in values.items():
            score += len(board.pieces(pt, chess.WHITE)) * val
            score -= len(board.pieces(pt, chess.BLACK)) * val
        return score

    @staticmethod
    def print_board(board: chess.Board):
        log_info(f"Turn: {'White' if board.turn == chess.WHITE else 'Black'}")
        material = Display._get_material_balance(board)
        mat_str = f"+{material}" if material > 0 else str(material)
        log_info(f'Material: {mat_str}')

        h, v = '───', '│'
        print(f"  ╭{h}" + (f"┬{h}" * 7) + f"╮") 

        for rank in range(7, -1, -1):
            row = f"{rank + 1} {v}"
            for file in range(8):
                square = chess.square(file, rank)
                piece = board.piece_at(square)
                if piece: symbol = piece.symbol()
                else: symbol = 'light' if (rank + file) & 1 else 'dark'
                row += f" {PIECES[symbol]} {v}"
            print(row)
            if rank > 0: print(f"  ├{h}" + (f"┼{h}" * 7) + f"┤") 

        print(f"  ╰{h}" + (f"┴{h}" * 7) + f"╯") 
        print("    a   b   c   d   e   f   g   h\n")

    @staticmethod
    def print_stats(engine_1, engine_2, game_number, total_games, w_time, b_time):
        

        log_info(f'Game {game_number}/{total_games}')
        log_info(f'{engine_1.name} - {engine_2.name} : {engine_1.score} - {engine_2.score}')
        

        if game_number & 1:
            log_info(f'{w_time :.2f} {b_time :.2f}')
        else:
            log_info(f'{b_time :.2f} {w_time :.2f}')

        

    @staticmethod
    def _format_history(board: chess.Board) -> str:
        moves = board.move_stack
        moves_str = " ".join([m.uci() for m in moves[-6:]])
        return f"...{moves_str}"
import time
from tqdm import tqdm

from .fen_parser import load_from_fen
from .move_exec import make_move, is_in_check, get_legal_moves
from .constants import WHITE, BLACK

from .gui import GUI
from .bot import RandomBot

class Game:
    DELAY = 0.1
    def __init__(self, fen='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'):
        self.state = load_from_fen(fen)
        self.gui = GUI()

        self.white_player, self.black_player = RandomBot(WHITE), RandomBot(BLACK)

        self.fen = fen

    def run(self, silent=False):
        winner = None
        reason = None
        while 1:
            if not silent: self.gui.clear_screen()

            legal_moves = get_legal_moves(self.state)
            is_check = is_in_check(self.state, self.state.player)
            is_white = self.state.player == WHITE

            if not silent:
                turn_color = "White" if is_white else "Black"
                check_msg = "| Check" if is_check else ""
                print(f"{turn_color} {check_msg}\n")

            if not silent: self.gui.print_board(self.state)
        
            if not silent: print(f"\n{self.gui.format_move_history(self.state.history)}\n")

            if not legal_moves: # no legal moves
                if is_check: # player to move in check
                    winner = BLACK if is_white else WHITE
                    if not silent: print(f"{"Black" if winner == BLACK else "White"} | Checkmate")
                    reason = "Checkmate"
                else:
                    if not silent: print("Draw | Stalemate")
                    reason = "Stalemate"
                break
                
            if self.state.halfmove_clock >= 100:
                if not silent: print("Draw | 50-move rule")
                reason = "50-move rule"
                break

            if not silent: time.sleep(self.DELAY) # so the game is watchable

            move = (self.white_player if is_white else self.black_player).get_best_move(self.state)

            self.state = make_move(self.state, move)

        return winner, reason

    def test(self, n):

        def reset():
            self.state = load_from_fen(self.fen)

        def format_results(results):
            lines = []
            lines.append(f"White: {results[WHITE]}")
            lines.append(f"Black: {results[BLACK]}")
            lines.append(f"Draw: {results[None]}")
            return "\n".join(lines)

        results = {state : 0 for state in [WHITE, BLACK, None]}

        with tqdm(total=n, desc=f"Testing", unit="game") as pbar:
            for _ in range(n):
                result, _ = self.run(silent=True)
                results[result] += 1

                pbar.set_postfix({"": f'> {format_results(results).replace("\n", ", ")}'})
                pbar.update(1)

                reset()

        print()

        return format_results(results)
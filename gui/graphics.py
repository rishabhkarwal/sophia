import pygame
import chess
import os

from gui.console import log_error

class Palette:
    LIGHT_SQ = (140, 143, 186)
    DARK_SQ = (26, 30, 35)
    BG = (26, 30, 35)
    PANEL_BG = (35, 40, 45)
    
    TEXT_MAIN = (220, 220, 220)
    TEXT_DIM = (140, 140, 140)
    SCROLLBAR = (60, 60, 60)
    BORDER = (140, 143, 186)
    
    HIGHLIGHT = (245, 141, 85, 150) 
    CLOCK_ACTIVE = (245, 141, 85)
    CLOCK_INACTIVE = (120, 120, 120)
    
    MAT_ADVANTAGE = (245, 141, 85)
    
    STAT_WIN = (100, 200, 100)
    STAT_DRAW = (160, 160, 160)
    STAT_LOSS = (200, 80, 80)

class Layout:
    BOARD_CONTAINER_SIZE = 640
    PANEL_WIDTH = 340
    WINDOW_W = BOARD_CONTAINER_SIZE + PANEL_WIDTH
    WINDOW_H = BOARD_CONTAINER_SIZE
    
    TARGET_PADDING = 30
    AVAILABLE_SPACE = BOARD_CONTAINER_SIZE - (TARGET_PADDING * 2)
    SQUARE_SIZE = AVAILABLE_SPACE // 8

    ACTUAL_BOARD_PIXELS = SQUARE_SIZE * 8
    OFFSET_X = (BOARD_CONTAINER_SIZE - ACTUAL_BOARD_PIXELS) // 2
    OFFSET_Y = (BOARD_CONTAINER_SIZE - ACTUAL_BOARD_PIXELS) // 2
    
    ASSETS_DIR = 'gui/assets'

UNICODE_PIECES = {
    chess.BLACK: {'P': '♙', 'N': '♘', 'B': '♗', 'R': '♖', 'Q': '♕', 'K': '♔'},
    chess.WHITE: {'P': '♟', 'N': '♞', 'B': '♝', 'R': '♜', 'Q': '♛', 'K': '♚'}
}

fps = 60

class GUI:
    def __init__(self):
        os.environ['SDL_VIDEO_CENTERED'] = '1'
        pygame.init()
        pygame.display.set_caption("Chess Engine Tournament")
        self.screen = pygame.display.set_mode((Layout.WINDOW_W, Layout.WINDOW_H), pygame.NOFRAME)
        self.clock = pygame.time.Clock()
        
        self.font_header = pygame.font.SysFont("Segoe UI", 24, bold=True)
        self.font_sub = pygame.font.SysFont("Segoe UI", 16)
        self.font_small = pygame.font.SysFont("Consolas", 14, bold=True)
        
        self.font_moves = pygame.font.SysFont("Segoe UI Symbol", 17)
        if not self.font_moves:
             self.font_moves = pygame.font.SysFont("Arial Unicode MS", 17)

        self.scroll_y = 0
        self.scroll_speed = 25
        self.max_scroll = 0
        self.last_move_count = 0 

        self.piece_images = {}
        self._load_assets()

    def _load_assets(self):
        pieces = ['p', 'n', 'b', 'r', 'q', 'k']
        colours = ['w', 'b']
        
        if not os.path.isdir(Layout.ASSETS_DIR):
             log_error(f"Warning: Assets dir '{Layout.ASSETS_DIR}' not found.")
             return

        for colour in colours:
            for piece in pieces:
                key = f"{colour}{piece}"
                filepath = os.path.join(Layout.ASSETS_DIR, f"{key}.png")
                if not os.path.exists(filepath):
                    filepath = os.path.join(Layout.ASSETS_DIR, f"{key}.svg")

                if os.path.exists(filepath):
                    try:
                        img = pygame.image.load(filepath).convert_alpha()
                        img = pygame.transform.smoothscale(img, (Layout.SQUARE_SIZE, Layout.SQUARE_SIZE))
                        self.piece_images[key] = img
                    except pygame.error:
                        pass

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit()
                raise KeyboardInterrupt
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.quit()
                    raise KeyboardInterrupt
            elif event.type == pygame.MOUSEWHEEL:
                self.scroll_y -= event.y * self.scroll_speed

    def draw(self, board: chess.Board, white_engine, black_engine, game_num, total, w_time, b_time, result_text=""):
        self.screen.fill(Palette.BG)
        
        border_rect = (
            Layout.OFFSET_X - 2, 
            Layout.OFFSET_Y - 2, 
            Layout.ACTUAL_BOARD_PIXELS + 4, 
            Layout.ACTUAL_BOARD_PIXELS + 4
        )
        pygame.draw.rect(self.screen, Palette.BORDER, border_rect, width=2)

        self._draw_squares(board)
        self._draw_pieces(board)
        
        w_mat_list, b_mat_list, w_score, b_score = self._calculate_material(board)
        
        is_white_turn = (board.turn == chess.WHITE) and not result_text
        self._draw_panel(
            white_engine, black_engine, 
            game_num, total, 
            w_time, b_time, 
            is_white_turn, result_text,
            board,
            w_mat_list, b_mat_list, w_score, b_score
        )

        pygame.display.flip()
        self.clock.tick(fps)

    def _calculate_material(self, board):
        full_set = {chess.PAWN: 8, chess.KNIGHT: 2, chess.BISHOP: 2, chess.ROOK: 2, chess.QUEEN: 1}
        w_current = {k: len(board.pieces(k, chess.WHITE)) for k in full_set}
        b_current = {k: len(board.pieces(k, chess.BLACK)) for k in full_set}
        
        w_captures = []
        for pt, count in full_set.items():
            missing = count - b_current[pt]
            if missing > 0:
                char = UNICODE_PIECES[chess.BLACK][chess.piece_symbol(pt).upper()]
                w_captures.extend([char] * missing)
                
        b_captures = []
        for pt, count in full_set.items():
            missing = count - w_current[pt]
            if missing > 0:
                char = UNICODE_PIECES[chess.WHITE][chess.piece_symbol(pt).upper()]
                b_captures.extend([char] * missing)

        sort_order = ['♟', '♞', '♝', '♜', '♛', '♙', '♘', '♗', '♖', '♕']
        w_captures.sort(key=lambda x: sort_order.index(x) if x in sort_order else 0)
        b_captures.sort(key=lambda x: sort_order.index(x) if x in sort_order else 0)

        w_val = sum(len(board.pieces(pt, chess.WHITE)) * val for pt, val in {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9}.items())
        b_val = sum(len(board.pieces(pt, chess.BLACK)) * val for pt, val in {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9}.items())
        
        return w_captures, b_captures, w_val, b_val

    def _draw_squares(self, board):
        last_move = board.peek() if board.move_stack else None
        
        for r in range(8):
            for c in range(8):
                color = Palette.LIGHT_SQ if (r + c) % 2 == 0 else Palette.DARK_SQ

                x = Layout.OFFSET_X + (c * Layout.SQUARE_SIZE)
                y = Layout.OFFSET_Y + (r * Layout.SQUARE_SIZE)
                
                pygame.draw.rect(self.screen, color, (x, y, Layout.SQUARE_SIZE, Layout.SQUARE_SIZE))
                
                if last_move and (chess.square(c, 7-r) == last_move.from_square or chess.square(c, 7-r) == last_move.to_square):
                    s = pygame.Surface((Layout.SQUARE_SIZE, Layout.SQUARE_SIZE), pygame.SRCALPHA)
                    s.fill(Palette.HIGHLIGHT)
                    self.screen.blit(s, (x, y))

    def _draw_pieces(self, board):
        for r in range(8):
            for c in range(8):
                square = chess.square(c, 7-r)
                piece = board.piece_at(square)
                if piece:
                    key = f"{'w' if piece.color == chess.WHITE else 'b'}{piece.symbol().lower()}"
                    img = self.piece_images.get(key)
                    if img:
                        x = Layout.OFFSET_X + (c * Layout.SQUARE_SIZE)
                        y = Layout.OFFSET_Y + (r * Layout.SQUARE_SIZE)
                        self.screen.blit(img, (x, y))

    def _draw_panel(self, w_eng, b_eng, game, total, w_time, b_time, white_active, result, board, w_cap, b_cap, w_sc, b_sc):
        x = Layout.BOARD_CONTAINER_SIZE + 15
        width = Layout.PANEL_WIDTH - 30
        y = 20
   
        header = self.font_header.render(f"Game {game} / {total}", True, Palette.TEXT_MAIN)
        self.screen.blit(header, (x, y)); y += 50

        self._draw_player_card(w_eng, w_time, x, y, "White", white_active, w_cap, w_sc - b_sc)
        y += 90

        b_active = not white_active and not result
        self._draw_player_card(b_eng, b_time, x, y, "Black", b_active, b_cap, b_sc - w_sc)
        y += 90
        
        pygame.draw.line(self.screen, Palette.SCROLLBAR, (x, y), (x + width, y), 1)
        y += 15

        list_h = Layout.WINDOW_H - y - 60 
        viewport = pygame.Rect(x, y, width, list_h)
        pygame.draw.rect(self.screen, Palette.PANEL_BG, viewport, border_radius=5)
        self._draw_move_list(board, viewport)
        
        if result:
            self._draw_result(result)

    def _draw_player_card(self, engine, time_left, x, y, role, is_active, captures, adv):
        col = Palette.TEXT_MAIN if is_active else Palette.TEXT_DIM
        name_s = self.font_sub.render(f"{role}: {engine.name} [{engine.score}]", True, col)
        self.screen.blit(name_s, (x, y))

        w = getattr(engine, 'wins', 0)
        d = getattr(engine, 'draws', 0)
        l = getattr(engine, 'losses', 0)

        name_w = name_s.get_width()
        self._render_wdl(x + name_w + 10, y + 2, w, d, l)

        t_col = Palette.CLOCK_ACTIVE if is_active else Palette.CLOCK_INACTIVE
        time_s = self._format_time(max(0, time_left))
        time_r = self.font_header.render(time_s, True, t_col)
        self.screen.blit(time_r, (x, y + 25))
        
        cap_str = "".join(captures)
        if len(cap_str) > 12: cap_str = cap_str[:11] + "..." 
        cap_surf = self.font_moves.render(cap_str, True, Palette.TEXT_DIM)
        self.screen.blit(cap_surf, (x, y + 55))

        if adv > 0:
            adv_txt = self.font_sub.render(f"+{int(adv)}", True, Palette.MAT_ADVANTAGE)
            self.screen.blit(adv_txt, (x + cap_surf.get_width() + 10, y + 55))

    def _render_wdl(self, x, y, w, d, l):
        def blit_text(text, color, cur_x):
            surf = self.font_small.render(text, True, color)
            self.screen.blit(surf, (cur_x, y))
            return cur_x + surf.get_width()

        cur_x = x
        cur_x = blit_text(str(w), Palette.STAT_WIN, cur_x)
        cur_x = blit_text("/", Palette.TEXT_DIM, cur_x)
        cur_x = blit_text(str(d), Palette.STAT_DRAW, cur_x)
        cur_x = blit_text("/", Palette.TEXT_DIM, cur_x)
        cur_x = blit_text(str(l), Palette.STAT_LOSS, cur_x)

    def _format_time(self, seconds):
        if seconds > 60:
            m = int(seconds // 60)
            s = int(seconds % 60)
            return f"{m:02}:{s:02}"
        else:
            s = int(seconds)
            ms = int((seconds - s) * 100)
            return f"{s:02}:{ms:02}"

    def _draw_move_list(self, board, viewport: pygame.Rect):
        move_stack = board.move_stack
        line_height = 24
        total_lines = (len(move_stack) + 1) // 2
        content_height = total_lines * line_height + 10 
        
        self.max_scroll = max(0, content_height - viewport.height)
        
        if len(move_stack) > self.last_move_count:
            self.last_move_count = len(move_stack)
            self.scroll_y = self.max_scroll

        self.scroll_y = max(0, min(self.scroll_y, self.max_scroll))

        surf = pygame.Surface((viewport.width - 10, content_height))
        surf.fill(Palette.PANEL_BG)

        temp_board = chess.Board()
        start_num = 1
        for i in range(0, len(move_stack), 2):
            y_pos = (start_num - 1) * line_height + 5
            num_str = f"{start_num}."
            
            wm = move_stack[i]
            wp = temp_board.piece_at(wm.from_square)
            wsym = UNICODE_PIECES[chess.WHITE][wp.symbol().upper()]
            wt = f"{wsym} {temp_board.san(wm)}"
            temp_board.push(wm)
            
            bt = ""
            if i + 1 < len(move_stack):
                bm = move_stack[i + 1]
                bp = temp_board.piece_at(bm.from_square)
                bsym = UNICODE_PIECES[chess.BLACK][bp.symbol().upper()]
                bt = f"{bsym} {temp_board.san(bm)}"
                temp_board.push(bm)

            surf.blit(self.font_moves.render(num_str, True, Palette.TEXT_DIM), (5, y_pos))
            surf.blit(self.font_moves.render(wt, True, Palette.TEXT_MAIN), (40, y_pos))
            surf.blit(self.font_moves.render(bt, True, Palette.TEXT_MAIN), (145, y_pos))
            start_num += 1

        visible_area = pygame.Rect(0, self.scroll_y, viewport.width - 10, viewport.height)
        self.screen.blit(surf, viewport.topleft, area=visible_area)

        if content_height > viewport.height:
            sb_x = viewport.right - 8
            thumb_h = max(20, viewport.height * (viewport.height / content_height))
            ratio = self.scroll_y / self.max_scroll
            thumb_y = viewport.top + (viewport.height - thumb_h) * ratio
            pygame.draw.rect(self.screen, Palette.SCROLLBAR, (sb_x, thumb_y, 6, thumb_h), border_radius=3)

    def _draw_result(self, text):
        bg = pygame.Surface((Layout.BOARD_CONTAINER_SIZE, 80))
        bg.set_alpha(230)
        bg.fill((0, 0, 0))
        y_pos = Layout.BOARD_CONTAINER_SIZE // 2 - 40
        self.screen.blit(bg, (0, y_pos))
        txt = self.font_header.render(text, True, (255, 100, 100))
        tr = txt.get_rect(center=(Layout.BOARD_CONTAINER_SIZE//2, Layout.BOARD_CONTAINER_SIZE//2))
        self.screen.blit(txt, tr)

    def quit(self):
        pygame.quit()
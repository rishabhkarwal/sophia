import pygame
import chess
import os

from gui.console import log_error


class Palette:
    # new retro colour scheme
    LIGHT_SQ    = (213, 196, 161)
    DARK_SQ     = (41, 41, 41)
    BG          = (41, 41, 41)
    PANEL_BG    = (50, 50, 50)
    CARD_BG     = (60, 60, 60)
    CARD_BORDER = (80, 80, 80)

    TEXT_MAIN   = (213, 196, 161)
    TEXT_DIM    = (140, 130, 110)
    TEXT_ROLE   = (110, 105, 90)
    SCROLLBAR   = (80, 80, 80)

    BORDER      = (213, 196, 161)

    HIGHLIGHT       = (243, 181, 98, 140)
    CLOCK_ACTIVE    = (243, 181, 98)
    CLOCK_INACTIVE  = (100, 95, 80)

    MAT_ADVANTAGE   = (243, 181, 98)

    STAT_WIN    = (81, 143, 107)
    STAT_DRAW   = (140, 130, 110)
    STAT_LOSS   = (205, 37, 29)

    RESULT_BG     = (50, 50, 50)
    RESULT_BORDER = (140, 190, 178)


class Layout:
    PANEL_WIDTH = 340
    SQUARE_SIZE = 72
    ACTUAL_BOARD_PIXELS = SQUARE_SIZE * 8   # 576
    OFFSET_Y = 32

    # standard (no eval bar): symmetric padding on all sides
    OFFSET_X = 32
    BOARD_CONTAINER_W = OFFSET_X + ACTUAL_BOARD_PIXELS + 32   # 640
    BOARD_CONTAINER_H = OFFSET_Y + ACTUAL_BOARD_PIXELS + 32   # 640
    WINDOW_W = BOARD_CONTAINER_W + PANEL_WIDTH                 # 980
    WINDOW_H = BOARD_CONTAINER_H                               # 640

    # eval-bar variant
    EVAL_OFFSET_X = 64
    EVAL_BOARD_CONTAINER_W = EVAL_OFFSET_X + ACTUAL_BOARD_PIXELS + 32   # 672
    EVAL_WINDOW_W = EVAL_BOARD_CONTAINER_W + PANEL_WIDTH                 # 1012

    ASSETS_DIR = 'gui/assets'
    CARD_RADIUS = 10
    PANEL_RADIUS = 8


UNICODE_PIECES = {
    chess.BLACK: {'P': '♙', 'N': '♘', 'B': '♗', 'R': '♖', 'Q': '♕', 'K': '♔'},
    chess.WHITE: {'P': '♟', 'N': '♞', 'B': '♝', 'R': '♜', 'Q': '♛', 'K': '♚'}
}

fps = 120


class GUI:
    def __init__(self, eval_bar: bool = False):
        # pick layout variant based on whether the eval bar is active
        self.eval_bar = eval_bar
        self._offset_x = Layout.EVAL_OFFSET_X if eval_bar else Layout.OFFSET_X
        self._window_w = Layout.EVAL_WINDOW_W if eval_bar else Layout.WINDOW_W
        self._board_container_w = Layout.EVAL_BOARD_CONTAINER_W if eval_bar else Layout.BOARD_CONTAINER_W

        os.environ['SDL_VIDEO_CENTERED'] = '1'
        pygame.init()
        pygame.display.set_caption("Engine Tournament")
        self._win = pygame.display.set_mode((self._window_w, Layout.WINDOW_H), pygame.RESIZABLE)
        self.screen = pygame.Surface((self._window_w, Layout.WINDOW_H))
        self.clock = pygame.time.Clock()

        self.font_header = pygame.font.SysFont("Helvetica Neue", 22, bold=True)
        self.font_sub = pygame.font.SysFont("Helvetica Neue", 15)
        self.font_role = pygame.font.SysFont("Helvetica Neue", 11)
        self.font_clock = pygame.font.SysFont("Menlo", 22, bold=True)
        self.font_small = pygame.font.SysFont("Menlo", 13, bold=True)

        self.font_moves = pygame.font.SysFont("Apple Symbols", 16)
        if not self.font_moves:
            self.font_moves = pygame.font.SysFont("Arial Unicode MS", 16)

        self.scroll_y = 0
        self.scroll_speed = 25
        self.max_scroll = 0
        self.last_move_count = 0

        # move list surface cache — only rebuilt when new moves arrive
        self._move_list_cache: pygame.Surface | None = None
        self._move_list_cache_move_count = -1

        self.piece_images = {}
        self._load_assets()

        self._last_panel_args = None
        self._last_eval_cp = 0
        self._last_eval_mate: int | None = None
        self._displayed_eval_cp = 0.0  # smoothly animated toward last eval

        # pre-build shared highlight surface
        self._highlight_surf = pygame.Surface((Layout.SQUARE_SIZE, Layout.SQUARE_SIZE), pygame.SRCALPHA)
        self._highlight_surf.fill(Palette.HIGHLIGHT)

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
                        self.piece_images[key] = img  # stored at native resolution
                    except pygame.error:
                        pass

    def _present(self):
        ww, wh = self._win.get_size()
        scale = min(ww / self._window_w, wh / Layout.WINDOW_H)
        scaled_w = int(self._window_w * scale)
        scaled_h = int(Layout.WINDOW_H * scale)
        scaled = pygame.transform.smoothscale(self.screen, (scaled_w, scaled_h))
        self._win.fill(Palette.BG)
        self._win.blit(scaled, ((ww - scaled_w) // 2, (wh - scaled_h) // 2))
        pygame.display.flip()

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
            elif event.type == pygame.VIDEORESIZE:
                scale = max(event.w / self._window_w, event.h / Layout.WINDOW_H)
                scale = max(scale, self._board_container_w / self._window_w)
                w = int(self._window_w * scale)
                h = int(Layout.WINDOW_H * scale)
                self._win = pygame.display.set_mode((w, h), pygame.RESIZABLE)

    def _draw_eval_bar(self, cp: float):
        """chess.com-style eval bar"""
        BAR_W = 26
        RADIUS = 2
        BAR_X = (self._offset_x - BAR_W) // 2
        BAR_Y = Layout.OFFSET_Y
        BAR_H = Layout.ACTUAL_BOARD_PIXELS

        # lerp at same visual speed regardless of fps
        self._displayed_eval_cp += (cp - self._displayed_eval_cp) * 0.05
        disp = self._displayed_eval_cp

        clamped = max(-800.0, min(800.0, disp))
        white_frac = 0.5 + clamped / 1600.0
        black_h = int(BAR_H * (1.0 - white_frac))
        white_h = BAR_H - black_h

        # draw into offscreen surface so rounded clip works cleanly
        bar = pygame.Surface((BAR_W, BAR_H), pygame.SRCALPHA)

        # full bar in black first
        pygame.draw.rect(bar, (0, 0, 0), (0, 0, BAR_W, BAR_H), border_radius=RADIUS)

        # white section from bottom — blit a full white rect clipped to bottom rows
        if white_h > 0:
            white_surf = pygame.Surface((BAR_W, BAR_H), pygame.SRCALPHA)
            pygame.draw.rect(white_surf, (255, 255, 255),
                             (0, 0, BAR_W, BAR_H), border_radius=RADIUS)
            bar.blit(white_surf, (0, black_h),
                     area=pygame.Rect(0, black_h, BAR_W, white_h))

        self.screen.blit(bar, (BAR_X, BAR_Y))

        # eval label: bottom of bar for white winning, top for black
        mate = self._last_eval_mate
        cp_int = int(self._last_eval_cp)

        if mate is not None:
            label = f"M{abs(mate)}"
        else:
            label = f"{abs(cp_int) / 100:.1f}"

        white_winning = cp_int >= 0
        text_colour = (0, 0, 0) if white_winning else (255, 255, 255)
        lbl_surf = self.font_role.render(label, True, text_colour)
        lbl_x = BAR_X + BAR_W // 2 - lbl_surf.get_width() // 2
        MARGIN = 5

        if white_winning:
            # anchor to bottom of bar
            lbl_y = BAR_Y + BAR_H - lbl_surf.get_height() - MARGIN
        else:
            # anchor to top of bar
            lbl_y = BAR_Y + MARGIN

        self.screen.blit(lbl_surf, (lbl_x, lbl_y))

    def draw(self, board, white_engine, black_engine, game_num, total, w_time, b_time, result_text="", eval_cp=None, eval_mate=None):
        if eval_cp is not None:
            self._last_eval_cp = eval_cp
        self._last_eval_mate = eval_mate
        self.screen.fill(Palette.BG)

        if self.eval_bar:
            self._draw_eval_bar(self._last_eval_cp)

        # board frame with rounded corners
        frame_rect = pygame.Rect(
            self._offset_x - 3,
            Layout.OFFSET_Y - 3,
            Layout.ACTUAL_BOARD_PIXELS + 6,
            Layout.ACTUAL_BOARD_PIXELS + 6
        )
        pygame.draw.rect(self.screen, Palette.BORDER, frame_rect, width=2, border_radius=4)

        self._draw_squares(board)
        self._draw_pieces(board)

        w_mat_list, b_mat_list, w_score, b_score = self._calculate_material(board)

        is_white_turn = (board.turn == chess.WHITE) and not result_text
        panel_args = (white_engine, black_engine, game_num, total, w_time, b_time,
                      is_white_turn, result_text, board, w_mat_list, b_mat_list, w_score, b_score)
        self._last_panel_args = panel_args
        self._draw_panel(*panel_args)

        self._present()
        self.clock.tick(fps)

    def animate_move(self, board, move):
        """animate a piece sliding from its source to destination square"""
        piece = board.piece_at(move.from_square)
        if piece is None:
            return

        key = f"{'w' if piece.color == chess.WHITE else 'b'}{piece.symbol().lower()}"
        img = self._get_piece_img(key)
        if img is None:
            return

        fc, fr = chess.square_file(move.from_square), chess.square_rank(move.from_square)
        tc, tr = chess.square_file(move.to_square), chess.square_rank(move.to_square)

        sx = self._offset_x + fc * Layout.SQUARE_SIZE
        sy = Layout.OFFSET_Y + (7 - fr) * Layout.SQUARE_SIZE
        ex = self._offset_x + tc * Layout.SQUARE_SIZE
        ey = Layout.OFFSET_Y + (7 - tr) * Layout.SQUARE_SIZE

        duration = 0.12  # seconds
        steps = max(8, int(duration * fps))

        for step in range(steps + 1):
            t = step / steps
            # ease-out cubic
            t = 1 - (1 - t) ** 3
            cx = sx + (ex - sx) * t
            cy = sy + (ey - sy) * t

            self.screen.fill(Palette.BG)

            frame_rect = pygame.Rect(
                self._offset_x - 3, Layout.OFFSET_Y - 3,
                Layout.ACTUAL_BOARD_PIXELS + 6, Layout.ACTUAL_BOARD_PIXELS + 6
            )
            pygame.draw.rect(self.screen, Palette.BORDER, frame_rect, width=2, border_radius=4)

            self._draw_squares_for_move(board, move)

            # draw all pieces except the moving one
            for r in range(8):
                for c in range(8):
                    sq = chess.square(c, 7 - r)
                    if sq == move.from_square:
                        continue
                    p = board.piece_at(sq)
                    if p:
                        pk = f"{'w' if p.color == chess.WHITE else 'b'}{p.symbol().lower()}"
                        pi = self._get_piece_img(pk)
                        if pi:
                            self.screen.blit(pi, (self._offset_x + c * Layout.SQUARE_SIZE,
                                                   Layout.OFFSET_Y + r * Layout.SQUARE_SIZE))

            # draw moving piece at interpolated position
            self.screen.blit(img, (int(cx), int(cy)))

            if self.eval_bar:
                self._draw_eval_bar(self._last_eval_cp)

            if self._last_panel_args:
                self._draw_panel(*self._last_panel_args)

            self.handle_events()
            self._present()
            self.clock.tick(fps)

    def _draw_squares_for_move(self, board, pending_move):
        """draw board squares with highlight on the pending move's squares"""
        for r in range(8):
            for c in range(8):
                color = Palette.LIGHT_SQ if (r + c) % 2 == 0 else Palette.DARK_SQ
                x = self._offset_x + c * Layout.SQUARE_SIZE
                y = Layout.OFFSET_Y + r * Layout.SQUARE_SIZE
                pygame.draw.rect(self.screen, color, (x, y, Layout.SQUARE_SIZE, Layout.SQUARE_SIZE))

                sq = chess.square(c, 7 - r)
                if sq == pending_move.from_square or sq == pending_move.to_square:
                    margin = 3
                    h_rect = pygame.Rect(x + margin, y + margin,
                                         Layout.SQUARE_SIZE - margin * 2, Layout.SQUARE_SIZE - margin * 2)
                    h_surf = pygame.Surface((h_rect.width, h_rect.height), pygame.SRCALPHA)
                    h_surf.fill(Palette.HIGHLIGHT)
                    self.screen.blit(h_surf, h_rect.topleft)

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
                x = self._offset_x + c * Layout.SQUARE_SIZE
                y = Layout.OFFSET_Y + r * Layout.SQUARE_SIZE
                pygame.draw.rect(self.screen, color, (x, y, Layout.SQUARE_SIZE, Layout.SQUARE_SIZE))

                if last_move:
                    sq = chess.square(c, 7 - r)
                    if sq == last_move.from_square or sq == last_move.to_square:
                        margin = 3
                        h_rect = pygame.Rect(x + margin, y + margin,
                                             Layout.SQUARE_SIZE - margin * 2, Layout.SQUARE_SIZE - margin * 2)
                        h_surf = pygame.Surface((h_rect.width, h_rect.height), pygame.SRCALPHA)
                        h_surf.fill(Palette.HIGHLIGHT)
                        self.screen.blit(h_surf, h_rect.topleft)

    def _get_piece_img(self, key):
        img = self.piece_images.get(key)
        if img is None:
            return None
        return pygame.transform.smoothscale(img, (Layout.SQUARE_SIZE, Layout.SQUARE_SIZE))

    def _draw_pieces(self, board):
        for r in range(8):
            for c in range(8):
                square = chess.square(c, 7 - r)
                piece = board.piece_at(square)
                if piece:
                    key = f"{'w' if piece.color == chess.WHITE else 'b'}{piece.symbol().lower()}"
                    img = self._get_piece_img(key)
                    if img:
                        x = self._offset_x + c * Layout.SQUARE_SIZE
                        y = Layout.OFFSET_Y + r * Layout.SQUARE_SIZE
                        self.screen.blit(img, (x, y))

    def _draw_panel(self, w_eng, b_eng, game, total, w_time, b_time, white_active, result, board, w_cap, b_cap, w_sc, b_sc):
        panel_x = self._board_container_w
        panel_rect = pygame.Rect(panel_x, 0, Layout.PANEL_WIDTH, Layout.WINDOW_H)
        pygame.draw.rect(self.screen, Palette.PANEL_BG, panel_rect)

        x = panel_x + 16
        width = Layout.PANEL_WIDTH - 32
        y = 18

        header = self.font_header.render(f"Game {game}  /  {total}", True, Palette.TEXT_MAIN)
        self.screen.blit(header, (x, y))
        y += 40

        self._draw_player_card(w_eng, w_time, x, y, "WHITE", white_active, w_cap, w_sc - b_sc, width)
        y += 98

        b_active = not white_active and not result
        self._draw_player_card(b_eng, b_time, x, y, "BLACK", b_active, b_cap, b_sc - w_sc, width)
        y += 98

        # divider
        pygame.draw.line(self.screen, Palette.CARD_BORDER, (x, y + 8), (x + width, y + 8), 1)
        y += 22

        list_h = Layout.WINDOW_H - y - 10
        viewport = pygame.Rect(x, y, width, list_h)
        pygame.draw.rect(self.screen, Palette.CARD_BG, viewport, border_radius=Layout.PANEL_RADIUS)
        self._draw_move_list(board, viewport)

        if result:
            self._draw_result(result)

    def _draw_player_card(self, engine, time_left, x, y, role, is_active, captures, adv, width):
        card_rect = pygame.Rect(x, y, width, 88)
        border_color = Palette.CLOCK_ACTIVE if is_active else Palette.CARD_BORDER
        pygame.draw.rect(self.screen, Palette.CARD_BG, card_rect, border_radius=Layout.CARD_RADIUS)
        pygame.draw.rect(self.screen, border_color, card_rect, width=1, border_radius=Layout.CARD_RADIUS)

        ix = x + 12
        iy = y + 10

        # role label — small, muted
        role_surf = self.font_role.render(role, True, Palette.TEXT_ROLE)
        self.screen.blit(role_surf, (ix, iy))

        # engine name
        name_col = Palette.TEXT_MAIN if is_active else Palette.TEXT_DIM
        name_surf = self.font_sub.render(engine.name, True, name_col)
        self.screen.blit(name_surf, (ix + role_surf.get_width() + 8, iy - 1))

        # WDL stats aligned right
        w = getattr(engine, 'wins', 0)
        d = getattr(engine, 'draws', 0)
        l = getattr(engine, 'losses', 0)
        self._render_wdl_right(x + width - 12, iy, w, d, l)

        iy += 22

        # clock — monospace
        t_col = Palette.CLOCK_ACTIVE if is_active else Palette.CLOCK_INACTIVE
        time_s = self._format_time(max(0, time_left))
        time_surf = self.font_clock.render(time_s, True, t_col)
        self.screen.blit(time_surf, (ix, iy))

        # score next to clock
        score_surf = self.font_sub.render(f"[{engine.score}]", True, Palette.TEXT_DIM)
        self.screen.blit(score_surf, (ix + time_surf.get_width() + 10, iy + 4))

        iy += 32

        # captured pieces
        cap_str = "".join(captures)
        if len(cap_str) > 14:
            cap_str = cap_str[:13] + "…"
        if cap_str:
            cap_surf = self.font_moves.render(cap_str, True, Palette.TEXT_DIM)
            self.screen.blit(cap_surf, (ix, iy))

            if adv > 0:
                adv_txt = self.font_small.render(f"+{int(adv)}", True, Palette.MAT_ADVANTAGE)
                self.screen.blit(adv_txt, (ix + cap_surf.get_width() + 8, iy + 1))

    def _render_wdl_right(self, right_x, y, w, d, l):
        """render W/D/L right-aligned"""
        parts = [
            (str(l), Palette.STAT_LOSS),
            ("/", Palette.TEXT_DIM),
            (str(d), Palette.STAT_DRAW),
            ("/", Palette.TEXT_DIM),
            (str(w), Palette.STAT_WIN),
        ]
        cx = right_x
        for text, color in parts:
            surf = self.font_small.render(text, True, color)
            cx -= surf.get_width()
            self.screen.blit(surf, (cx, y))

    def _format_time(self, seconds):
        if seconds > 60:
            m = int(seconds // 60)
            s = int(seconds % 60)
            return f"{m:02}:{s:02}"
        else:
            s = int(seconds)
            ms = int((seconds - s) * 100)
            return f"{s:02}:{ms:02}"

    def _draw_move_list(self, board, viewport):
        move_stack = board.move_stack
        move_count = len(move_stack)
        line_height = 22
        total_lines = (move_count + 1) // 2
        content_height = max(viewport.height, total_lines * line_height + 12)

        self.max_scroll = max(0, content_height - viewport.height)

        # auto-scroll to bottom when a new move arrives
        if move_count > self.last_move_count:
            self.last_move_count = move_count
            self.scroll_y = self.max_scroll
            self._move_list_cache = None  # invalidate cache

        self.scroll_y = max(0, min(self.scroll_y, self.max_scroll))

        # rebuild cached surface only when move count changed
        if self._move_list_cache is None or self._move_list_cache_move_count != move_count:
            cache_w = viewport.width - 12
            cache_h = content_height
            surf = pygame.Surface((cache_w, cache_h))
            surf.fill(Palette.CARD_BG)

            temp_board = chess.Board()
            move_num = 1
            for i in range(0, move_count, 2):
                y_pos = (move_num - 1) * line_height + 6

                wm = move_stack[i]
                wp = temp_board.piece_at(wm.from_square)
                wsym = UNICODE_PIECES[chess.WHITE][wp.symbol().upper()] if wp else ""
                wt = f"{wsym} {temp_board.san(wm)}"
                temp_board.push(wm)

                bt = ""
                if i + 1 < move_count:
                    bm = move_stack[i + 1]
                    bp = temp_board.piece_at(bm.from_square)
                    bsym = UNICODE_PIECES[chess.BLACK][bp.symbol().upper()] if bp else ""
                    bt = f"{bsym} {temp_board.san(bm)}"
                    temp_board.push(bm)

                surf.blit(self.font_small.render(f"{move_num}.", True, Palette.TEXT_ROLE), (6, y_pos + 2))
                surf.blit(self.font_moves.render(wt, True, Palette.TEXT_MAIN), (36, y_pos))
                surf.blit(self.font_moves.render(bt, True, Palette.TEXT_MAIN), (cache_w // 2, y_pos))
                move_num += 1

            self._move_list_cache = surf
            self._move_list_cache_move_count = move_count

        visible_area = pygame.Rect(0, self.scroll_y, viewport.width - 12, viewport.height)
        self.screen.blit(self._move_list_cache, viewport.topleft, area=visible_area)

        # scrollbar
        if content_height > viewport.height:
            sb_x = viewport.right - 7
            thumb_h = max(20, viewport.height * (viewport.height / content_height))
            ratio = self.scroll_y / self.max_scroll if self.max_scroll > 0 else 0
            thumb_y = viewport.top + (viewport.height - thumb_h) * ratio
            pygame.draw.rect(self.screen, Palette.SCROLLBAR, (sb_x, thumb_y, 5, thumb_h), border_radius=3)

    def _draw_result(self, text):
        # centered rounded card over the board
        card_w = 260
        card_h = 64
        cx = self._board_container_w // 2
        cy = Layout.WINDOW_H // 2

        card_rect = pygame.Rect(cx - card_w // 2, cy - card_h // 2, card_w, card_h)

        # shadow pass
        shadow_rect = card_rect.inflate(8, 8)
        shadow_surf = pygame.Surface((shadow_rect.width, shadow_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(shadow_surf, (0, 0, 0, 100), shadow_surf.get_rect(), border_radius=Layout.CARD_RADIUS + 4)
        self.screen.blit(shadow_surf, shadow_rect.topleft)

        pygame.draw.rect(self.screen, Palette.RESULT_BG, card_rect, border_radius=Layout.CARD_RADIUS)
        pygame.draw.rect(self.screen, Palette.RESULT_BORDER, card_rect, width=2, border_radius=Layout.CARD_RADIUS)

        txt = self.font_header.render(text, True, Palette.TEXT_MAIN)
        tr = txt.get_rect(center=(cx, cy))
        self.screen.blit(txt, tr)

    def quit(self):
        pygame.quit()

from dataclasses import dataclass

@dataclass
class GameAssignment:
    game_id: int
    engine_1_path: str
    engine_2_path: str
    engine_1_name: str
    engine_2_name: str
    time_control: int         # seconds
    increment: int            # seconds
    white_is_engine_1: bool   # alternates per pair
    starting_fen: str | None  # from openings file, or None for startpos

@dataclass
class GameUpdate:
    game_id: int
    move_number: int
    fen: str
    w_time: float
    b_time: float
    white_name: str
    black_name: str
    status: str               # "playing" | "completed"
    result: str | None        # e.g. "1-0" when completed

@dataclass
class GameResult:
    game_id: int
    white_name: str
    black_name: str
    result: str               # "1-0", "0-1", "1/2-1/2", "*"
    termination: str          # "Checkmate", "Time Forfeit", etc.
    pgn_string: str
    moves: int                # total half-moves
    time_control: str         # "60+0" format for PGN header
    error: str | None         # non-None if worker crashed

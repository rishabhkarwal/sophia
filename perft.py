import time
from dataclasses import dataclass

from engine.board.state import State
from engine.board.fen_parser import load_from_fen
from engine.board.move_exec import make_move, unmake_move
from engine.moves.generator import get_legal_moves
from engine.moves.legality import is_in_check, get_attackers
from engine.core.constants import WHITE, BLACK, MASK_FLAG, MASK_TARGET, WK, BK
from engine.core.move import PROMOTION_N
from engine.core.utils import bit_scan
from engine.moves.precomputed import init_tables

from engine.core.move import (
    CAPTURE, EN_PASSANT, 
    CASTLE_KS, CASTLE_QS, 
    PROMO_CAP_N
)

@dataclass
class Stats:
    """Perft statistics for move generation validation"""
    nodes: int = 0
    captures: int = 0
    ep: int = 0
    castles: int = 0
    promotions: int = 0
    checks: int = 0
    discovery_checks: int = 0
    double_checks: int = 0
    checkmates: int = 0
    
    def __add__(self, other):
        return Stats(
            self.nodes + other.nodes,
            self.captures + other.captures,
            self.ep + other.ep,
            self.castles + other.castles,
            self.promotions + other.promotions,
            self.checks + other.checks,
            self.discovery_checks + other.discovery_checks,
            self.double_checks + other.double_checks,
            self.checkmates + other.checkmates
        )
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Stats): return False
        for field in self.__dataclass_fields__:
            actual = getattr(self, field)
            expected = getattr(other, field)
            if expected == -1: continue
            if actual != expected: return False
        return True

"""Tests from: https://www.chessprogramming.org/Perft_Results"""
TEST_SUITE = [
    {
        "name": "Position 1 (Initial Position)",
        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "results": {
            1: Stats(20, 0, 0, 0, 0, 0, 0, 0, 0),
            2: Stats(400, 0, 0, 0, 0, 0, 0, 0, 0),
            3: Stats(8_902, 34, 0, 0, 0, 12, 0, 0, 0),
            4: Stats(197_281, 1_576, 0, 0, 0, 469, 0, 0, 8),
            5: Stats(4_865_609, 82_719, 258, 0, 0, 27_351, 6, 0, 347),
        }
    },
    {
        "name": "Position 2 (Kiwipete)",
        "fen": "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
        "results": {
            1: Stats(48, 8, 0, 2, 0, 0, 0, 0, 0),
            2: Stats(2_039, 351, 1, 91, 0, 3, 0, 0, 0),
            3: Stats(97_862, 17_102, 45, 3_162, 0, 993, 0, 0, 1),
            4: Stats(4_085_603, 757_163, 1_929, 128_013, 15_172, 25_523, 42, 6, 43),
            5: Stats(193_690_690, 35_043_416, 73_365, 4_993_637, 8_392, 3_309_887, 19_883, 2_637, 30_171),
        }
    },
    {
        "name": "Position 3",
        "fen": "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
        "results": {
            1: Stats(14, 1, 0, 0, 0, 2, 0, 0, 0),
            2: Stats(191, 14, 0, 0, 0, 10, 0, 0, 0),
            3: Stats(2_812, 209, 2, 0, 0, 267, 3, 0, 0),
            4: Stats(43_238, 3_348, 123, 0, 0, 1_680, 106, 0, 17),
            5: Stats(674_624, 52_051, 1_165, 0, 0, 52_950, 1_292, 3, 0),
        }
    },
    {
        "name": "Position 4",
        "fen": "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1",
        "results": {
            1: Stats(6, 0, 0, 0, 0, 0, -1, -1, 0),
            2: Stats(264, 87, 0, 6, 48, 10, -1, -1, 0),
            3: Stats(9_467, 1_021, 4, 0, 120, 38, -1, -1, 22),
            4: Stats(422_333, 131_393, 0, 7_795, 60_032, 15_492, -1, -1, 5),
            5: Stats(15_833_292, 2_046_173, 6_512, 0, 329_464, 200_568, -1, -1, 50_562),
        }
    },
    {
        "name": "Position 5",
        "fen": "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8",
        "results": {
            1: Stats(44, -1, -1, -1, -1, -1, -1, -1, -1),
            2: Stats(1_486, -1, -1, -1, -1, -1, -1, -1, -1),
            3: Stats(62_379, -1, -1, -1, -1, -1, -1, -1, -1),
            4: Stats(2_103_487, -1, -1, -1, -1, -1, -1, -1, -1),
            5: Stats(89_941_194, -1, -1, -1, -1, -1, -1, -1, -1),
        }
    },
    {
        "name": "Position 6",
        "fen": "r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10",
        "results": {
            1: Stats(46, -1, -1, -1, -1, -1, -1, -1, -1),
            2: Stats(2_079, -1, -1, -1, -1, -1, -1, -1, -1),
            3: Stats(89_890, -1, -1, -1, -1, -1, -1, -1, -1),
            4: Stats(3_894_594, -1, -1, -1, -1, -1, -1, -1, -1),
            5: Stats(164_075_551, -1, -1, -1, -1, -1, -1, -1, -1),
        }
    },
]

def perft(state: State, depth: int) -> Stats:
    if depth == 0: return Stats(nodes=1)
    
    stats = Stats()
    moves = get_legal_moves(state)
    
    for move in moves:
        undo_info = make_move(state, move)
        
        if depth == 1:
            stats.nodes += 1
            
            # Extract bits using the new masks
            flag = (move & MASK_FLAG) >> 12
            target_sq = (move & MASK_TARGET) >> 6
            
            # Count Types
            if flag == CAPTURE or flag == EN_PASSANT or flag >= PROMO_CAP_N:
                stats.captures += 1
            
            if flag == EN_PASSANT:
                stats.ep += 1
                
            if flag == CASTLE_KS or flag == CASTLE_QS:
                stats.castles += 1
                
            if flag >= PROMOTION_N:
                stats.promotions += 1
            
            # Check Detection
            # We must use state.is_white to determine current side
            current_side = WHITE if state.is_white else BLACK
            previous_side = BLACK if state.is_white else WHITE # Side that just moved
            
            # is_in_check checks if the SIDE ARGUMENT is being attacked
            if is_in_check(state, current_side):
                stats.checks += 1
                
                king_key = WK if current_side == WHITE else BK
                king_bb = state.bitboards[king_key]
                
                if king_bb:
                    king_sq = (king_bb & -king_bb).bit_length() - 1
                    # Get attackers from the previous side (the one that moved)
                    checks_bb = get_attackers(state, king_sq, previous_side)
                    check_count = bin(checks_bb).count('1')
                    
                    if check_count > 1:
                        stats.double_checks += 1
                    else:
                        if not (checks_bb & (1 << target_sq)):
                            stats.discovery_checks += 1

                if not get_legal_moves(state):
                    stats.checkmates += 1
                    
        else:
            stats += perft(state, depth - 1)
            
        unmake_move(state, move, undo_info)
    
    return stats

def run_perft_suite(max_depth: int = 4):
    def format_stat(actual: int, expected: int) -> str:
        if expected == -1: return f"{actual}(?)"
        diff = actual - expected
        if diff == 0: return str(actual)
        return f"{actual}({diff:+d})"

    t0 = time.time()
    init_tables() 
    print(f"Took {time.time() - t0 :.4f}s to initialise tables\n")
    
    w = {'depth': 6, 'nodes': 18, 'cap': 12, 'ep': 8, 'cas': 8,
         'pro': 8, 'chk': 10, 'disc': 8, 'dbl': 8, 'mate': 8,
         'time': 10, 'stat': 6}
    width = 135
    all_passed = True
    
    for test in TEST_SUITE:
        print("=" * width)
        print(f"TEST: {test['name']}")
        print(f"FEN:  {test['fen']}")
        print("=" * width)
        print(f"{'Depth':<{w['depth']}} {'Nodes':<{w['nodes']}} {'Captures':<{w['cap']}} "
              f"{'E.P.':<{w['ep']}} {'Castles':<{w['cas']}} {'Promo':<{w['pro']}} "
              f"{'Checks':<{w['chk']}} {'Disc +':<{w['disc']}} {'Double +':<{w['dbl']}} "
              f"{'Mates':<{w['mate']}} {'Time':<{w['time']}} {'Result':<{w['stat']}}")
        print("-" * width)
        
        state = load_from_fen(test['fen'])
        for depth in sorted([d for d in test['results'].keys() if d <= max_depth]):
            t0 = time.time()
            stats = perft(state, depth)
            elapsed = time.time() - t0
            expected = test['results'][depth]
            passed = (stats == expected)
            if not passed: all_passed = False
            
            print(f"{depth:<{w['depth']}} "
                  f"{format_stat(stats.nodes, expected.nodes):<{w['nodes']}} "
                  f"{format_stat(stats.captures, expected.captures):<{w['cap']}} "
                  f"{format_stat(stats.ep, expected.ep):<{w['ep']}} "
                  f"{format_stat(stats.castles, expected.castles):<{w['cas']}} "
                  f"{format_stat(stats.promotions, expected.promotions):<{w['pro']}} "
                  f"{format_stat(stats.checks, expected.checks):<{w['chk']}} "
                  f"{format_stat(stats.discovery_checks, expected.discovery_checks):<{w['disc']}} "
                  f"{format_stat(stats.double_checks, expected.double_checks):<{w['dbl']}} "
                  f"{format_stat(stats.checkmates, expected.checkmates):<{w['mate']}} "
                  f"{elapsed:<{w['time']}.3f} "
                  f"{'PASS' if passed else 'FAIL':<{w['stat']}}")
        print("\n\n")
    
    print("=" * width)
    print("All tests passed" if all_passed else "Some tests failed")
    print("=" * width)

if __name__ == "__main__":
    run_perft_suite(max_depth=4)
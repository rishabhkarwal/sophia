from engine.uci.handler import UCI
from engine.core.move import move_to_uci

import cProfile
import pstats

def test(position='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1', time_limit=2.0):
        uci = UCI()

        print(f'Testing Position: {position}\n')

        position_args = ['fen'] + position.split()
        uci.handle_position(position_args)

        uci.engine.time_limit = time_limit * 1000

        profiler = cProfile.Profile()
        profiler.enable()
        
        best_move = uci.engine.get_best_move(uci.state)

        profiler.disable()
    
        print(f'\nBest Move: {move_to_uci(best_move)}\n\n')
        
        stats = pstats.Stats(profiler).sort_stats('cumulative')
        stats.print_stats(30)


if __name__ == '__main__':
        fen = '5B2/1P2P2P/2P1r3/2b1p3/6p1/2K2P1k/p7/nN5B w - - 0 1'
        time = 60
        test(position=fen, time_limit=time)
        

"""
FEN: r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1

Depth   Score      Nodes     NPS       Time (ms)   PV
----------------------------------------------------------------------------
1       cp 42      1,686     8,948     188         e2a6
2       cp 42      5,039     9,190     548         e2a6 h3g2
3       cp 42      12,823    11,049    1,160       e2a6 h3g2 f3g2
4       cp 42      69,891    8,846     7,900       e2a6 h3g2 f3g2 b4c3
5       cp 29      171,710   9,296     18,469      e2a6 b4c3 d2c3 e6d5 e1c1
6       cp 29      355,844   9,215     38,614      e2a6 b4c3 d2c3 e6d5 e1c1 h3g2

> Best Move:       e2a6
> Total Nodes:     587,776
> Average NPS:     9,731
> Total Time:      60.4s

Total Calls: 93,814,969 function calls in 60.402 seconds

ncalls      tottime  percall  cumtime  percall  function location
--------------------------------------------------------------------------------
1           0.00     0.00     60.40    60.40    search.py:73(get_best_move)
7           0.00     0.00     60.39    8.62     search.py:170(_search_root)
81,436      0.58     0.00     60.38    0.19     search.py:206(_alpha_beta)
506,340     2.56     0.00     54.67    0.00     search.py:318(_quiescence)
458,718     14.32    0.00     19.06    0.00     evaluation.py:155(evaluate)
201,867     0.96     0.00     10.83    0.00     list.sort
1,167,655   7.35     0.00     9.49     0.00     move_exec.py:42(make_move)
3,190,142   3.98     0.00     8.69     0.00     ordering.py:66(get_move_score)
201,860     0.72     0.00     8.38     0.00     generator.py:34(gen_pseudo_legal)
2,580,813   0.94     0.00     8.14     0.00     search.py:331(<lambda>)
1,167,648   3.88     0.00     5.29     0.00     move_exec.py:210(unmake_move)
1,687,567   1.51     0.00     3.84     0.00     legality.py:58(is_in_check)
21,146,211  3.14     0.00     3.14     0.00     int.bit_length
1,009,900   2.00     0.00     2.66     0.00     ordering.py:34(_get_mvv_lva_score)
201,860     1.88     0.00     2.63     0.00     generator.py:61(_gen_pawn_moves)
1,793,021   2.14     0.00     2.14     0.00     legality.py:18(is_square_attacked)

================================================================================
================================================================================

FEN: 5B2/1P2P2P/2P1r3/2b1p3/6p1/2K2P1k/p7/nN5B w - - 0 1

Depth   Score      Nodes     NPS       Time (ms)   PV
----------------------------------------------------------------------------
1       cp 1659    2,657     9,761     272         h7h8q
2       cp 1659    4,971     9,831     505         h7h8q h3g3
3       cp 1659    7,513     10,633    706         h7h8q h3g3 b7b8q
4       cp 1659    21,269    11,100    1,916       h7h8q h3g3 b7b8q c5e7
5       cp 1584    65,750    11,966    5,494       h7h8q h3g3 b7b8q a1b3 b8e5
6       cp 1584    120,232   11,069    10,861      h7h8q h3g3 b7b8q a1b3 b8e5 e6e5
7       cp 1584    183,760   11,669    15,747      h7h8q h3g3 b7b8q a1b3 b8e5 e6e5 h8e5
8       cp 1584    451,473   11,484    39,309      h7h8q h3g3 b7b8q a1b3 b8e5 e6e5 h8e5 g3h3

> Best Move:       h7h8q
> Total Nodes:     667,648
> Average NPS:     11,085
> Total Time:      60.2s

Total Calls: 84,770,635 function calls in 60.226 seconds

ncalls      tottime  percall  cumtime  percall  function location
--------------------------------------------------------------------------------
1           0.00     0.00     60.23    60.23    search.py:73(get_best_move)
11          0.00     0.00     60.22    5.48     search.py:170(_search_root)
109,761     1.00     0.00     60.21    0.26     search.py:206(_alpha_beta)
557,887     2.75     0.00     51.51    0.00     search.py:318(_quiescence)
497,924     11.02    0.00     14.82    0.00     evaluation.py:155(evaluate)
227,024     1.17     0.00     12.76    0.00     list.sort
3,460,821   4.79     0.00     10.22    0.00     ordering.py:66(get_move_score)
1,078,970   7.78     0.00     10.05    0.00     move_exec.py:42(make_move)
2,659,686   1.05     0.00     9.09     0.00     search.py:331(<lambda>)
227,013     0.86     0.00     8.47     0.00     generator.py:34(gen_pseudo_legal)
1,078,965   4.02     0.00     5.44     0.00     move_exec.py:210(unmake_move)
1,660,202   1.63     0.00     4.36     0.00     legality.py:58(is_in_check)
1,001,361   2.20     0.00     2.86     0.00     ordering.py:34(_get_mvv_lva_score)
800,871     0.32     0.00     2.51     0.00     search.py:256(<lambda>)
1,660,202   2.41     0.00     2.41     0.00     legality.py:18(is_square_attacked)
12,793,498  2.14     0.00     2.14     0.00     int.bit_length
227,013     1.36     0.00     2.00     0.00     generator.py:223(_gen_queen_moves)
227,013     1.13     0.00     1.80     0.00     generator.py:61(_gen_pawn_moves)
9,959,882   1.78     0.00     1.78     0.00     str.upper
227,013     0.96     0.00     1.36     0.00     generator.py:189(_gen_bishop_moves)
5,408,023   1.34     0.00     1.34     0.00     move.py:73(is_capture)
6,978,821   1.26     0.00     1.26     0.00     int.bit_count
227,013     0.84     0.00     1.23     0.00     generator.py:152(_gen_king_moves)
5,007,036   1.17     0.00     1.17     0.00     move.py:77(is_promotion)
1,905,279   0.83     0.00     1.12     0.00     move.py:85(is_castle)
"""

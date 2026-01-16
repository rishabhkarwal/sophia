import re
from collections import defaultdict, Counter

def parse_games(pgn_text):
    raw_games = re.split(r'(?=\[Event\s)', pgn_text.strip())
    games = []
    header_regex = re.compile(r'^\[([A-Za-z0-9_]+)\s+"([^"]*)"\]\s*$', re.MULTILINE)

    for raw in raw_games:
        if not raw.strip(): continue
        headers = dict(header_regex.findall(raw))
        if headers:
            games.append(headers)
    return games

def get_points(result):
    result = result.strip()
    if result == '1-0': return 1.0, 0.0, 'win'
    if result == '0-1': return 0.0, 1.0, 'loss'
    if result in ('1/2-1/2', '½-½', '1/2–1/2'): return 0.5, 0.5, 'draw'
    return 0.0, 0.0, 'unknown'

def analyse_tournament(games):
    stats = defaultdict(lambda: {
        'games': 0,
        'players': defaultdict(lambda: {
            'score': 0.0, 'wins': 0, 'draws': 0, 'losses': 0,
            'reasons': defaultdict(Counter) 
        })
    })

    for g in games:
        tc = g.get('TimeControl', 'Unknown TC')
        white = g.get('White', 'White')
        black = g.get('Black', 'Black')
        result = g.get('Result', '*')
        termination = g.get('Termination', 'normal')

        for category in [tc, "Overall"]:
            s = stats[category]
            s['games'] += 1
            
            w_pts, b_pts, res_type = get_points(result)

            p_white = s['players'][white]
            p_white['score'] += w_pts

            p_black = s['players'][black]
            p_black['score'] += b_pts

            if w_pts == 1.0:
                p_white['wins'] += 1
                p_white['reasons']['win'][termination] += 1
                p_black['losses'] += 1
                p_black['reasons']['loss'][termination] += 1
            
            elif b_pts == 1.0:
                p_black['wins'] += 1
                p_black['reasons']['win'][termination] += 1
                p_white['losses'] += 1
                p_white['reasons']['loss'][termination] += 1
            
            elif w_pts == 0.5:
                p_white['draws'] += 1
                p_white['reasons']['draw'][termination] += 1
                p_black['draws'] += 1
                p_black['reasons']['draw'][termination] += 1

    return stats

def format_reasons(reason_dict):
    if not reason_dict: return ""
    items = [f"{k}:{v}" for k, v in reason_dict.items()]
    return f"[{', '.join(items)}]"

def print_results(stats):
    categories = sorted([k for k in stats.keys() if k != "Overall"]) + ["Overall"]
    
    for cat in categories:
        if cat not in stats: continue
        data = stats[cat]
        
        print("-" * 60)
        print(f"TimeControl: {cat} (Games: {data['games']})")
        print("-" * 60)

        ranking = sorted(data['players'].items(), key=lambda x: x[1]['score'], reverse=True)

        for name, p_data in ranking:
            print(f"{name:12s} : {p_data['score']:5.1f} pts  (W:{p_data['wins']} D:{p_data['draws']} L:{p_data['losses']})")

            if p_data['wins'] > 0:
                print(f"    Wins   : {format_reasons(p_data['reasons']['win'])}")
            if p_data['draws'] > 0:
                print(f"    Draws  : {format_reasons(p_data['reasons']['draw'])}")
            if p_data['losses'] > 0:
                print(f"    Losses : {format_reasons(p_data['reasons']['loss'])}")
            print()

        if ranking:
            top_score = ranking[0][1]['score']
            winners = [n for n, d in ranking if d['score'] == top_score]
            if len(winners) > 1:
                print(f">> Result: Tie between {', '.join(winners)}")
            else:
                print(f">> Winner: {winners[0]}")
        print("\n")

if __name__ == '__main__':
    path = 'games.pgn'
    try:
        with open(path, 'r', encoding='utf-8') as f:
            pgn_content = f.read()
        
        games_list = parse_games(pgn_content)
        if not games_list:
            print("No games found in file")
        else:
            tournament_stats = analyse_tournament(games_list)
            print_results(tournament_stats)
            
    except FileNotFoundError:
        print(f"Error: File '{path}' not found")

"""
Literally a tie

------------------------------------------------------------
TimeControl: 120+1 (Games: 30)
------------------------------------------------------------
sophia       :  17.5 pts  (W:15 D:5 L:10)
    Wins   : [Checkmate:15]
    Draws  : [Fivefold Repetition:4, 75 Moves Rule:1]
    Losses : [Checkmate:10]

new          :  12.5 pts  (W:10 D:5 L:15)
    Wins   : [Checkmate:10]
    Draws  : [Fivefold Repetition:4, 75 Moves Rule:1]
    Losses : [Checkmate:15]

>> Winner: sophia


------------------------------------------------------------
TimeControl: 180+0 (Games: 30)
------------------------------------------------------------
new          :  17.5 pts  (W:14 D:7 L:9)
    Wins   : [Time Forfeit:2, Checkmate:10, Illegal Move (0000):1, Engine Crash:1]
    Draws  : [Fivefold Repetition:7]
    Losses : [Checkmate:8, Time Forfeit:1]

sophia       :  12.5 pts  (W:9 D:7 L:14)
    Wins   : [Checkmate:8, Time Forfeit:1]
    Draws  : [Fivefold Repetition:7]
    Losses : [Time Forfeit:2, Checkmate:10, Illegal Move (0000):1, Engine Crash:1]

>> Winner: new


------------------------------------------------------------
TimeControl: 180+2 (Games: 40)
------------------------------------------------------------
sophia       :  22.5 pts  (W:16 D:13 L:11)
    Wins   : [Checkmate:16]
    Draws  : [Fivefold Repetition:13]
    Losses : [Checkmate:10, Illegal Move (0000):1]

new          :  17.5 pts  (W:11 D:13 L:16)
    Wins   : [Checkmate:10, Illegal Move (0000):1]
    Draws  : [Fivefold Repetition:13]
    Losses : [Checkmate:16]

>> Winner: sophia


------------------------------------------------------------
TimeControl: 300+5 (Games: 10)
------------------------------------------------------------
new          :   5.0 pts  (W:4 D:2 L:4)
    Wins   : [Checkmate:4]
    Draws  : [Insufficient Material:1, Fivefold Repetition:1]
    Losses : [Illegal Move (0000):1, Checkmate:3]

sophia       :   5.0 pts  (W:4 D:2 L:4)
    Wins   : [Illegal Move (0000):1, Checkmate:3]
    Draws  : [Insufficient Material:1, Fivefold Repetition:1]
    Losses : [Checkmate:4]

>> Result: Tie between new, sophia


------------------------------------------------------------
TimeControl: 60+0 (Games: 30)
------------------------------------------------------------
new          :  18.0 pts  (W:16 D:4 L:10)
    Wins   : [Time Forfeit:4, Checkmate:12]
    Draws  : [Fivefold Repetition:4]
    Losses : [Checkmate:3, Time Forfeit:7]

sophia       :  12.0 pts  (W:10 D:4 L:16)
    Wins   : [Checkmate:3, Time Forfeit:7]
    Draws  : [Fivefold Repetition:4]
    Losses : [Time Forfeit:4, Checkmate:12]

>> Winner: new


------------------------------------------------------------
TimeControl: 600+1 (Games: 20)
------------------------------------------------------------
sophia       :  11.5 pts  (W:9 D:5 L:6)
    Wins   : [Checkmate:7, Illegal Move (0000):2]
    Draws  : [Fivefold Repetition:5]
    Losses : [Checkmate:5, Illegal Move (0000):1]

new          :   8.5 pts  (W:6 D:5 L:9)
    Wins   : [Checkmate:5, Illegal Move (0000):1]
    Draws  : [Fivefold Repetition:5]
    Losses : [Checkmate:7, Illegal Move (0000):2]

>> Winner: sophia


------------------------------------------------------------
TimeControl: Overall (Games: 160)
------------------------------------------------------------
sophia       :  81.0 pts  (W:63 D:36 L:61)
    Wins   : [Checkmate:52, Time Forfeit:8, Illegal Move (0000):3]
    Draws  : [Fivefold Repetition:34, Insufficient Material:1, 75 Moves Rule:1]
    Losses : [Time Forfeit:6, Checkmate:51, Illegal Move (0000):3, Engine Crash:1]

new          :  79.0 pts  (W:61 D:36 L:63)
    Wins   : [Time Forfeit:6, Checkmate:51, Illegal Move (0000):3, Engine Crash:1]
    Draws  : [Fivefold Repetition:34, Insufficient Material:1, 75 Moves Rule:1]
    Losses : [Checkmate:52, Time Forfeit:8, Illegal Move (0000):3]

>> Winner: sophia
"""
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
------------------------------------------------------------
TimeControl: 180+1 (Games: 6)
------------------------------------------------------------
sophia       :   5.0 pts  (W:4 D:2 L:0)
    Wins   : [Checkmate:4]
    Draws  : [Fivefold Repetition:2]

previous     :   1.0 pts  (W:0 D:2 L:4)
    Draws  : [Fivefold Repetition:2]
    Losses : [Checkmate:4]

>> Winner: sophia


------------------------------------------------------------
TimeControl: 60+0 (Games: 6)
------------------------------------------------------------
sophia       :   4.0 pts  (W:2 D:4 L:0)
    Wins   : [Checkmate:2]
    Draws  : [Fivefold Repetition:4]

previous     :   2.0 pts  (W:0 D:4 L:2)
    Draws  : [Fivefold Repetition:4]
    Losses : [Checkmate:2]

>> Winner: sophia


------------------------------------------------------------
TimeControl: 600+1 (Games: 26)
------------------------------------------------------------
sophia       :  16.0 pts  (W:11 D:10 L:5)
    Wins   : [Checkmate:9, Time Forfeit:1, Illegal Move (d7d8q):1]
    Draws  : [Fivefold Repetition:10]
    Losses : [Checkmate:5]

previous     :  10.0 pts  (W:5 D:10 L:11)
    Wins   : [Checkmate:5]
    Draws  : [Fivefold Repetition:10]
    Losses : [Checkmate:9, Time Forfeit:1, Illegal Move (d7d8q):1]

>> Winner: sophia


------------------------------------------------------------
TimeControl: Overall (Games: 38)
------------------------------------------------------------
sophia       :  25.0 pts  (W:17 D:16 L:5)
    Wins   : [Checkmate:15, Time Forfeit:1, Illegal Move (d7d8q):1]
    Draws  : [Fivefold Repetition:16]
    Losses : [Checkmate:5]

previous     :  13.0 pts  (W:5 D:16 L:17)
    Wins   : [Checkmate:5]
    Draws  : [Fivefold Repetition:16]
    Losses : [Checkmate:15, Time Forfeit:1, Illegal Move (d7d8q):1]

>> Winner: sophia
"""
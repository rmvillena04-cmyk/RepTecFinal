"""
MÓDULO EXTRACT — Descarga y almacenamiento de fuentes crudas
Fuentes:
  F1 — Football-Data.co.uk  (partidos LaLiga 2020/21 → 2024/25, CSV)
  F2 — Understat            (xG por equipo y temporada, CSV local sintético)
  F3 — EA Sports FC 24      (Kaggle snapshot, CSV local sintético)
"""

import os, requests, logging, json
from datetime import datetime
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [EXTRACT] %(message)s")
log = logging.getLogger(__name__)

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "logs", "pipeline_tracking.json")

LALIGA_URLS = {
    "2020-21": "https://www.football-data.co.uk/mmz4281/2021/SP1.csv",
    "2021-22": "https://www.football-data.co.uk/mmz4281/2122/SP1.csv",
    "2022-23": "https://www.football-data.co.uk/mmz4281/2223/SP1.csv",
    "2023-24": "https://www.football-data.co.uk/mmz4281/2324/SP1.csv",
    "2024-25": "https://www.football-data.co.uk/mmz4281/2425/SP1.csv",
}

def load_tracking():
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH) as f:
            return json.load(f)
    return {}

def save_tracking(data):
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "w") as f:
        json.dump(data, f, indent=2, default=str)

def extract_f1_laliga():
    """
    Genera datos sintéticos realistas de partidos LaLiga (estilo Football-Data.co.uk).
    En producción se descargarían de https://www.football-data.co.uk/mmz4281/
    """
    np.random.seed(7)
    os.makedirs(RAW_DIR, exist_ok=True)

    teams = [
        "Real Madrid","Barcelona","Atletico Madrid","Sevilla","Real Sociedad",
        "Villarreal","Athletic Club","Valencia","Real Betis","Osasuna",
        "Celta Vigo","Getafe","Rayo Vallecano","Girona","Mallorca",
        "Almeria","Cadiz","Granada","Las Palmas","Leganes"
    ]
    seasons = {
        "2020-21": pd.date_range("2020-09-12","2021-05-22", freq="7D"),
        "2021-22": pd.date_range("2021-08-14","2022-05-22", freq="7D"),
        "2022-23": pd.date_range("2022-08-12","2023-06-04", freq="7D"),
        "2023-24": pd.date_range("2023-08-11","2024-05-26", freq="7D"),
        "2024-25": pd.date_range("2024-08-15","2025-05-25", freq="7D"),
    }
    ftr_map = {"H": 0, "D": 1, "A": 2}
    rows = []
    for season, dates in seasons.items():
        matchdays = list(dates)
        # 20 teams → 380 games per season (round-robin)
        game_idx = 0
        for i in range(len(teams)):
            for j in range(len(teams)):
                if i == j:
                    continue
                home, away = teams[i], teams[j]
                h_str = 85 - i * 2
                a_str = 85 - j * 2
                p_home_win = 0.45 + (h_str - a_str) * 0.003
                p_draw     = 0.28
                p_away_win = 1 - p_home_win - p_draw
                outcome = np.random.choice(["H","D","A"],
                    p=[max(0.15, p_home_win), p_draw, max(0.10, p_away_win)])
                if outcome == "H":
                    fthg = np.random.poisson(2.0); ftag = np.random.poisson(0.8)
                elif outcome == "D":
                    fthg = np.random.poisson(1.1); ftag = fthg
                else:
                    fthg = np.random.poisson(0.8); ftag = np.random.poisson(2.0)
                hthg = min(fthg, np.random.poisson(0.8))
                htag = min(ftag, np.random.poisson(0.7))
                match_date = matchdays[game_idx % len(matchdays)]
                rows.append({
                    "Div": "SP1",
                    "Date": match_date.strftime("%d/%m/%Y"),
                    "HomeTeam": home, "AwayTeam": away,
                    "FTHG": int(fthg), "FTAG": int(ftag),
                    "FTR": outcome,
                    "HTHG": int(hthg), "HTAG": int(htag),
                    "HTR": "H" if hthg > htag else ("A" if htag > hthg else "D"),
                    "HS": int(np.random.poisson(13)), "AS": int(np.random.poisson(10)),
                    "HST": int(np.random.poisson(5)), "AST": int(np.random.poisson(4)),
                    "HF": int(np.random.poisson(12)), "AF": int(np.random.poisson(12)),
                    "HC": int(np.random.poisson(5)), "AC": int(np.random.poisson(4)),
                    "HY": int(np.random.poisson(2)), "AY": int(np.random.poisson(2)),
                    "HR": int(np.random.poisson(0.07)), "AR": int(np.random.poisson(0.07)),
                    "B365H": round(np.random.uniform(1.5, 4.5), 2),
                    "B365D": round(np.random.uniform(2.8, 4.0), 2),
                    "B365A": round(np.random.uniform(1.8, 6.0), 2),
                    "season": season,
                })
                game_idx += 1

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(RAW_DIR, "F1_laliga_raw.csv"), index=False)
    log.info(f"F1 generado (sintético): {len(df)} registros, {df.shape[1]} columnas")
    return df

def generate_f2_understat():
    """Genera datos sintéticos realistas de xG al estilo Understat para LaLiga."""
    np.random.seed(42)
    teams = [
        "Real Madrid","Barcelona","Atletico Madrid","Sevilla","Real Sociedad",
        "Villarreal","Athletic Club","Valencia","Real Betis","Osasuna",
        "Celta Vigo","Getafe","Rayo Vallecano","Girona","Mallorca",
        "Almeria","Cadiz","Granada","Las Palmas","Leganes"
    ]
    seasons = ["2020-21","2021-22","2022-23","2023-24","2024-25"]
    rows = []
    for season in seasons:
        for pos, team in enumerate(teams, 1):
            base_xg = max(0.8, 2.2 - pos * 0.06 + np.random.normal(0, 0.18))
            base_xga = max(0.5, 0.8 + pos * 0.05 + np.random.normal(0, 0.15))
            pts = max(10, 95 - pos * 3.5 + np.random.randint(-5, 6))
            rows.append({
                "team": team,
                "season": season,
                "xG": round(base_xg * 38, 2),
                "xGA": round(base_xga * 38, 2),
                "xPTS": round(pts * 0.9 + np.random.normal(0, 3), 2),
                "pts": int(pts),
                "wins": int(pts // 3),
                "draws": int((pts % 3)),
                "losses": int(38 - pts // 3 - pts % 3),
                "goals": int(base_xg * 38 * np.random.uniform(0.85, 1.15)),
                "goals_against": int(base_xga * 38 * np.random.uniform(0.85, 1.15)),
                "position": pos,
            })
    df = pd.DataFrame(rows)
    os.makedirs(RAW_DIR, exist_ok=True)
    df.to_csv(os.path.join(RAW_DIR, "F2_understat_raw.csv"), index=False)
    log.info(f"F2 generado: {len(df)} registros")
    return df

def generate_f3_fc24():
    """Genera datos sintéticos de jugadores al estilo EA Sports FC 24."""
    np.random.seed(99)
    teams = [
        "Real Madrid","Barcelona","Atletico Madrid","Sevilla","Real Sociedad",
        "Villarreal","Athletic Club","Valencia","Real Betis","Osasuna",
        "Celta Vigo","Getafe","Rayo Vallecano","Girona","Mallorca",
        "Almeria","Cadiz","Granada","Las Palmas","Leganes"
    ]
    positions = ["GK","CB","CB","LB","RB","CDM","CM","CM","LW","RW","ST"]
    nationalities = ["Spain","Brazil","Argentina","France","Germany","England","Portugal","Colombia","Uruguay","Netherlands"]
    
    rows = []
    player_id = 1
    for team in teams:
        n_players = np.random.randint(22, 28)
        team_quality = 85 - teams.index(team) * 1.2
        for _ in range(n_players):
            pos = np.random.choice(positions)
            age = np.random.randint(17, 37)
            overall = int(np.clip(team_quality + np.random.normal(0, 6), 55, 99))
            value_eur = int(np.exp(overall * 0.12 - 4.5) * 1e6 * np.random.uniform(0.7, 1.3))
            wage_eur = int(value_eur * np.random.uniform(0.003, 0.008))
            rows.append({
                "player_id": player_id,
                "short_name": f"Player_{player_id}",
                "long_name": f"Player Full Name {player_id}",
                "player_positions": pos,
                "overall": overall,
                "potential": min(99, overall + np.random.randint(0, 10)),
                "age": age,
                "club_name": team,
                "league_name": "La Liga",
                "nationality_name": np.random.choice(nationalities),
                "value_eur": value_eur,
                "wage_eur": wage_eur,
                "pace": int(np.clip(np.random.normal(72, 12), 40, 99)),
                "shooting": int(np.clip(np.random.normal(68, 14), 35, 99)),
                "passing": int(np.clip(np.random.normal(70, 12), 40, 99)),
                "dribbling": int(np.clip(np.random.normal(69, 13), 38, 99)),
                "defending": int(np.clip(np.random.normal(65, 15), 30, 99)),
                "physic": int(np.clip(np.random.normal(68, 11), 40, 99)),
                "goals_real": int(np.random.poisson(3 if pos in ["ST","LW","RW"] else 0.5)),
                "assists_real": int(np.random.poisson(3 if pos in ["CM","LW","RW"] else 1)),
                "minutes_played": np.random.randint(0, 3420),
            })
            player_id += 1
    df = pd.DataFrame(rows)
    os.makedirs(RAW_DIR, exist_ok=True)
    df.to_csv(os.path.join(RAW_DIR, "F3_fc24_raw.csv"), index=False)
    log.info(f"F3 generado: {len(df)} registros")
    return df

def run_extract():
    tracking = load_tracking()
    tracking["extract"] = {}

    df1 = extract_f1_laliga()
    tracking["extract"]["F1_laliga"] = {
        "registros": int(len(df1)),
        "columnas": int(df1.shape[1]) if len(df1) else 0,
        "timestamp": str(datetime.now())
    }

    df2 = generate_f2_understat()
    tracking["extract"]["F2_understat"] = {
        "registros": int(len(df2)),
        "columnas": int(df2.shape[1]),
        "timestamp": str(datetime.now())
    }

    df3 = generate_f3_fc24()
    tracking["extract"]["F3_fc24"] = {
        "registros": int(len(df3)),
        "columnas": int(df3.shape[1]),
        "timestamp": str(datetime.now())
    }

    save_tracking(tracking)
    log.info("EXTRACT completado. Tracking guardado.")
    return df1, df2, df3

if __name__ == "__main__":
    run_extract()

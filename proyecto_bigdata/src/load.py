"""
MÓDULO LOAD — Construcción del modelo estrella y carga en SQLite
Dimensiones: DIM_TIEMPO, DIM_EQUIPO, DIM_JUGADOR, DIM_TEMPORADA
Tabla de hechos: FACT_RENDIMIENTO
"""

import os, json, logging, sqlite3
import pandas as pd
import numpy as np
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [LOAD] %(message)s")
log = logging.getLogger(__name__)

PROC_DIR  = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
FINAL_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "final")
DB_PATH   = os.path.join(os.path.dirname(__file__), "..", "data", "football_dw.db")
LOG_PATH  = os.path.join(os.path.dirname(__file__), "..", "logs", "pipeline_tracking.json")

os.makedirs(FINAL_DIR, exist_ok=True)

def load_tracking():
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH) as f:
            return json.load(f)
    return {}

def save_tracking(data):
    with open(LOG_PATH, "w") as f:
        json.dump(data, f, indent=2, default=str)

def build_dim_tiempo(df1_clean):
    """Construye DIM_TIEMPO a partir de las fechas de F1."""
    dates = pd.to_datetime(df1_clean["Date"], errors="coerce", utc=True).dropna().unique()
    rows = []
    for i, d in enumerate(sorted(dates), 1):
        dt = pd.Timestamp(d)
        rows.append({
            "sk_tiempo": i,
            "fecha": dt.strftime("%Y-%m-%d"),
            "anio": dt.year,
            "trimestre": dt.quarter,
            "mes": dt.month,
            "semana": dt.isocalendar()[1],
            "dia_semana": dt.strftime("%A"),
            "es_fin_semana": int(dt.weekday() >= 5),
        })
    df = pd.DataFrame(rows)
    log.info(f"DIM_TIEMPO: {len(df)} filas")
    return df

def build_dim_equipo(df1_clean, df2_clean):
    """Construye DIM_EQUIPO de equipos únicos."""
    teams_f1 = pd.concat([
        df1_clean["HomeTeam"].rename("team"),
        df1_clean["AwayTeam"].rename("team")
    ]).str.strip().str.lower().dropna().unique()

    teams_f2 = df2_clean["team"].str.strip().str.lower().dropna().unique()
    all_teams = sorted(set(list(teams_f1) + list(teams_f2)))

    rows = []
    for i, team in enumerate(all_teams, 1):
        rows.append({
            "sk_equipo": i,
            "team_name": team,
            "league": "laliga",
            "country": "spain",
        })
    df = pd.DataFrame(rows)
    log.info(f"DIM_EQUIPO: {len(df)} filas")
    return df

def build_dim_temporada():
    """Construye DIM_TEMPORADA."""
    seasons = ["2020-21","2021-22","2022-23","2023-24","2024-25"]
    rows = []
    for i, s in enumerate(seasons, 1):
        start_year = int(s[:4])
        rows.append({
            "sk_temporada": i,
            "season_label": s,
            "start_year": start_year,
            "end_year": start_year + 1,
            "era": "post-covid" if start_year >= 2021 else "covid",
        })
    df = pd.DataFrame(rows)
    log.info(f"DIM_TEMPORADA: {len(df)} filas")
    return df

def build_dim_jugador(df3_clean):
    """Construye DIM_JUGADOR de FC24."""
    df = df3_clean.copy()
    df = df.rename(columns={"player_id": "player_natural_id"})
    df.insert(0, "sk_jugador", range(1, len(df) + 1))
    cols = ["sk_jugador","player_natural_id","short_name","long_name",
            "player_positions","overall","potential","age",
            "club_name","nationality_name","value_eur","wage_eur",
            "pace","shooting","passing","dribbling","defending","physic"]
    df = df[cols]
    log.info(f"DIM_JUGADOR: {len(df)} filas")
    return df

def build_fact_rendimiento(df1_clean, df2_clean, dim_equipo, dim_temporada, dim_tiempo):
    """Construye FACT_RENDIMIENTO uniendo F1 y F2."""
    # Mapa equipo → sk
    eq_map = dict(zip(dim_equipo["team_name"], dim_equipo["sk_equipo"]))
    # Mapa fecha → sk
    t_map = dict(zip(dim_tiempo["fecha"], dim_tiempo["sk_tiempo"]))
    # Mapa temporada → sk
    s_map = dict(zip(dim_temporada["season_label"], dim_temporada["sk_temporada"]))

    rows = []
    sk = 1

    # FACT desde F1: un registro por partido (home + away como perspectiva)
    for _, r in df1_clean.iterrows():
        fecha_str = pd.Timestamp(r["Date"]).strftime("%Y-%m-%d") if pd.notna(r.get("Date")) else None
        sk_t = t_map.get(fecha_str, 1)
        sk_s = s_map.get(r.get("season","2023-24"), s_map.get("2023-24", 5))
        sk_home = eq_map.get(str(r.get("HomeTeam","")).strip().lower(), 1)
        sk_away = eq_map.get(str(r.get("AwayTeam","")).strip().lower(), 1)

        # Home perspective
        rows.append({
            "sk_rendimiento": sk,
            "fk_tiempo": sk_t,
            "fk_temporada": sk_s,
            "fk_equipo": sk_home,
            "fk_rival": sk_away,
            "es_local": 1,
            "goles_favor": int(r.get("FTHG", 0)),
            "goles_contra": int(r.get("FTAG", 0)),
            "tiros": int(r.get("HS", 0)),
            "tiros_puerta": int(r.get("HST", 0)),
            "corners": int(r.get("HC", 0)),
            "faltas": int(r.get("HF", 0)),
            "amarillas": int(r.get("HY", 0)),
            "rojas": int(r.get("HR", 0)),
            "resultado": str(r.get("FTR","D")),
            "xg_partido": None,
            "xga_partido": None,
            "source_id": "F1_laliga",
            "load_timestamp": str(datetime.now()),
        })
        sk += 1

        # Away perspective
        rows.append({
            "sk_rendimiento": sk,
            "fk_tiempo": sk_t,
            "fk_temporada": sk_s,
            "fk_equipo": sk_away,
            "fk_rival": sk_home,
            "es_local": 0,
            "goles_favor": int(r.get("FTAG", 0)),
            "goles_contra": int(r.get("FTHG", 0)),
            "tiros": int(r.get("AS", 0)),
            "tiros_puerta": int(r.get("AST", 0)),
            "corners": int(r.get("AC", 0)),
            "faltas": int(r.get("AF", 0)),
            "amarillas": int(r.get("AY", 0)),
            "rojas": int(r.get("AR", 0)),
            "resultado": "H" if r.get("FTR") == "A" else ("A" if r.get("FTR") == "H" else "D"),
            "xg_partido": None,
            "xga_partido": None,
            "source_id": "F1_laliga",
            "load_timestamp": str(datetime.now()),
        })
        sk += 1

    df_fact = pd.DataFrame(rows)

    # Enriquecer con xG de F2 (nivel temporada)
    xg_map = {}
    for _, r in df2_clean.iterrows():
        team = str(r["team"]).strip().lower()
        season = r["season"]
        sk_eq = eq_map.get(team, None)
        sk_se = s_map.get(season, None)
        if sk_eq and sk_se:
            xg_map[(sk_eq, sk_se)] = (r["xG"] / 38, r["xGA"] / 38)

    df_fact["xg_partido"] = df_fact.apply(
        lambda row: xg_map.get((row["fk_equipo"], row["fk_temporada"]), (None, None))[0], axis=1
    )
    df_fact["xga_partido"] = df_fact.apply(
        lambda row: xg_map.get((row["fk_equipo"], row["fk_temporada"]), (None, None))[1], axis=1
    )

    log.info(f"FACT_RENDIMIENTO: {len(df_fact)} filas")
    return df_fact

def load_to_sqlite(dim_tiempo, dim_equipo, dim_temporada, dim_jugador, fact):
    """Crea las tablas en SQLite y carga los datos."""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS DIM_TIEMPO (
        sk_tiempo    INTEGER PRIMARY KEY,
        fecha        TEXT NOT NULL,
        anio         INTEGER,
        trimestre    INTEGER,
        mes          INTEGER,
        semana       INTEGER,
        dia_semana   TEXT,
        es_fin_semana INTEGER
    );
    CREATE TABLE IF NOT EXISTS DIM_EQUIPO (
        sk_equipo  INTEGER PRIMARY KEY,
        team_name  TEXT NOT NULL,
        league     TEXT,
        country    TEXT
    );
    CREATE TABLE IF NOT EXISTS DIM_TEMPORADA (
        sk_temporada  INTEGER PRIMARY KEY,
        season_label  TEXT NOT NULL,
        start_year    INTEGER,
        end_year      INTEGER,
        era           TEXT
    );
    CREATE TABLE IF NOT EXISTS DIM_JUGADOR (
        sk_jugador         INTEGER PRIMARY KEY,
        player_natural_id  INTEGER,
        short_name         TEXT,
        long_name          TEXT,
        player_positions   TEXT,
        overall            INTEGER,
        potential          INTEGER,
        age                INTEGER,
        club_name          TEXT,
        nationality_name   TEXT,
        value_eur          REAL,
        wage_eur           REAL,
        pace               INTEGER,
        shooting           INTEGER,
        passing            INTEGER,
        dribbling          INTEGER,
        defending          INTEGER,
        physic             INTEGER
    );
    CREATE TABLE IF NOT EXISTS FACT_RENDIMIENTO (
        sk_rendimiento  INTEGER PRIMARY KEY,
        fk_tiempo       INTEGER REFERENCES DIM_TIEMPO(sk_tiempo),
        fk_temporada    INTEGER REFERENCES DIM_TEMPORADA(sk_temporada),
        fk_equipo       INTEGER REFERENCES DIM_EQUIPO(sk_equipo),
        fk_rival        INTEGER REFERENCES DIM_EQUIPO(sk_equipo),
        es_local        INTEGER,
        goles_favor     INTEGER,
        goles_contra    INTEGER,
        tiros           INTEGER,
        tiros_puerta    INTEGER,
        corners         INTEGER,
        faltas          INTEGER,
        amarillas       INTEGER,
        rojas           INTEGER,
        resultado       TEXT,
        xg_partido      REAL,
        xga_partido     REAL,
        source_id       TEXT,
        load_timestamp  TEXT
    );
    """)
    conn.commit()

    dim_tiempo.to_sql("DIM_TIEMPO",     conn, if_exists="append", index=False)
    dim_equipo.to_sql("DIM_EQUIPO",     conn, if_exists="append", index=False)
    dim_temporada.to_sql("DIM_TEMPORADA", conn, if_exists="append", index=False)
    dim_jugador.to_sql("DIM_JUGADOR",   conn, if_exists="append", index=False)
    fact.to_sql("FACT_RENDIMIENTO",     conn, if_exists="append", index=False)

    # Verificación
    counts = {}
    for tbl in ["DIM_TIEMPO","DIM_EQUIPO","DIM_TEMPORADA","DIM_JUGADOR","FACT_RENDIMIENTO"]:
        n = cur.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        counts[tbl] = n
        log.info(f"  {tbl}: {n} registros cargados")

    conn.close()
    return counts

def export_csvs(dim_tiempo, dim_equipo, dim_temporada, dim_jugador, fact):
    dim_tiempo.to_csv(os.path.join(FINAL_DIR, "dim_tiempo.csv"), index=False)
    dim_equipo.to_csv(os.path.join(FINAL_DIR, "dim_equipo.csv"), index=False)
    dim_temporada.to_csv(os.path.join(FINAL_DIR, "dim_temporada.csv"), index=False)
    dim_jugador.to_csv(os.path.join(FINAL_DIR, "dim_jugador.csv"), index=False)
    fact.to_csv(os.path.join(FINAL_DIR, "fact_rendimiento.csv"), index=False)
    log.info("CSVs finales exportados a data/final/")

def run_load():
    tracking = load_tracking()
    tracking.setdefault("load", {})

    df1 = pd.read_csv(os.path.join(PROC_DIR, "F1_laliga_clean.csv"), low_memory=False)
    df2 = pd.read_csv(os.path.join(PROC_DIR, "F2_understat_clean.csv"))
    df3 = pd.read_csv(os.path.join(PROC_DIR, "F3_fc24_clean.csv"))

    dim_tiempo    = build_dim_tiempo(df1)
    dim_equipo    = build_dim_equipo(df1, df2)
    dim_temporada = build_dim_temporada()
    dim_jugador   = build_dim_jugador(df3)
    fact          = build_fact_rendimiento(df1, df2, dim_equipo, dim_temporada, dim_tiempo)

    counts = load_to_sqlite(dim_tiempo, dim_equipo, dim_temporada, dim_jugador, fact)
    export_csvs(dim_tiempo, dim_equipo, dim_temporada, dim_jugador, fact)

    tracking["load"] = {
        "motor": "SQLite3",
        "db_path": "data/football_dw.db",
        "tablas": counts,
        "timestamp": str(datetime.now())
    }
    save_tracking(tracking)
    log.info("LOAD completado.")
    return dim_tiempo, dim_equipo, dim_temporada, dim_jugador, fact

if __name__ == "__main__":
    run_load()

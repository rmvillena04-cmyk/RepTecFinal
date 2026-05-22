"""
MÓDULO TRANSFORM — Transformaciones T01–T10
Aplica las 10 transformaciones obligatorias sobre los datasets crudos.
"""

import os, json, logging, hashlib
import pandas as pd
import numpy as np
from datetime import datetime
from scipy import stats

logging.basicConfig(level=logging.INFO, format="%(asctime)s [TRANSFORM] %(message)s")
log = logging.getLogger(__name__)

RAW_DIR     = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
PROC_DIR    = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
LOG_PATH    = os.path.join(os.path.dirname(__file__), "..", "logs", "pipeline_tracking.json")

os.makedirs(PROC_DIR, exist_ok=True)

def load_tracking():
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH) as f:
            return json.load(f)
    return {}

def save_tracking(data):
    with open(LOG_PATH, "w") as f:
        json.dump(data, f, indent=2, default=str)

def _hash_pii(val):
    if pd.isna(val):
        return val
    return hashlib.sha256(str(val).encode()).hexdigest()[:16]

# ─── T01: Eliminación de duplicados ─────────────────────────────────────────
def t01_dedup(df, key_cols=None, source=""):
    before = len(df)
    if key_cols:
        df = df.drop_duplicates(subset=key_cols, keep="first")
    df = df.drop_duplicates(keep="first")
    n = before - len(df)
    log.info(f"T01 [{source}] duplicados eliminados: {n}")
    return df, {"T01_duplicados_eliminados": n}

# ─── T02: Tratamiento de nulos ────────────────────────────────────────────────
def t02_nulos(df, source=""):
    report = {}
    for col in df.columns:
        n_null = df[col].isna().sum()
        if n_null == 0:
            continue
        if df[col].dtype in [np.float64, np.int64]:
            fill_val = df[col].median()
            strategy = "median"
        else:
            fill_val = df[col].mode()[0] if not df[col].mode().empty else "UNKNOWN"
            strategy = "moda"
        df[col] = df[col].fillna(fill_val)
        report[col] = {"nulos_imputados": int(n_null), "estrategia": strategy}
        log.info(f"T02 [{source}] {col}: {n_null} nulos → {strategy}")
    return df, report

# ─── T03: Eliminación de blancos ─────────────────────────────────────────────
def t03_blancos(df, source=""):
    count = 0
    for col in df.select_dtypes(include="object").columns:
        mask = df[col].str.strip() == ""
        count += mask.sum()
        df.loc[mask, col] = np.nan
    df, _ = t02_nulos(df, source=source)  # re-impute NaN created from blanks
    log.info(f"T03 [{source}] blancos corregidos: {count}")
    return df, {"T03_blancos_corregidos": int(count)}

# ─── T04: Corrección de tipos ─────────────────────────────────────────────────
def t04_tipos_f1(df):
    """Casteo específico para F1 LaLiga."""
    date_cols = [c for c in df.columns if c.upper() in ["DATE"]]
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], dayfirst=True, errors="coerce")
    int_cols = ["FTHG","FTAG","HTHG","HTAG","HS","AS","HST","AST","HF","AF","HC","AC","HY","AY","HR","AR"]
    for col in int_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    float_cols = ["B365H","B365D","B365A","BbAv>2.5","BbAv<2.5"]
    for col in float_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    log.info("T04 [F1] tipos casteados")
    return df, {"T04_columnas_casteadas": len(int_cols) + len(float_cols) + len(date_cols)}

def t04_tipos_f2(df):
    for col in ["xG","xGA","xPTS"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in ["pts","wins","draws","losses","goals","goals_against","position"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    log.info("T04 [F2] tipos casteados")
    return df, {"T04_columnas_casteadas": 10}

def t04_tipos_f3(df):
    int_cols = ["player_id","overall","potential","age","pace","shooting",
                "passing","dribbling","defending","physic","goals_real","assists_real","minutes_played"]
    for col in int_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    for col in ["value_eur","wage_eur"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    log.info("T04 [F3] tipos casteados")
    return df, {"T04_columnas_casteadas": len(int_cols) + 2}

# ─── T05: Normalización de fechas ISO-8601 ────────────────────────────────────
def t05_fechas(df, date_cols, source=""):
    count = 0
    for col in date_cols:
        if col not in df.columns:
            continue
        df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)
        count += df[col].notna().sum()
    log.info(f"T05 [{source}] fechas normalizadas: {count}")
    return df, {"T05_fechas_normalizadas": int(count)}

# ─── T06: Normalización de texto ─────────────────────────────────────────────
def t06_texto(df, text_cols, source=""):
    import unicodedata
    count = 0
    for col in text_cols:
        if col not in df.columns:
            continue
        df[col] = df[col].astype(str).str.strip().str.lower()
        df[col] = df[col].apply(lambda x: unicodedata.normalize("NFD", x)
                                 .encode("ascii", "ignore").decode("utf-8") if isinstance(x, str) else x)
        count += 1
    log.info(f"T06 [{source}] campos normalizados: {count}")
    return df, {"T06_campos_normalizados": count}

# ─── T07: Corrección de rangos ───────────────────────────────────────────────
def t07_rangos(df, source=""):
    count = 0
    num_cols = df.select_dtypes(include=[np.number]).columns
    for col in num_cols:
        if "overall" in col or "potential" in col or "pace" in col or "shooting" in col:
            mask = (df[col] < 1) | (df[col] > 99)
            count += mask.sum()
            df.loc[mask, col] = df[col].median()
        if col in ["minutes_played"]:
            mask = df[col] > 3420
            count += mask.sum()
            df.loc[mask, col] = 3420
        if "value_eur" in col or "wage_eur" in col:
            mask = df[col] < 0
            count += mask.sum()
            df.loc[mask, col] = 0
    log.info(f"T07 [{source}] outliers de rango corregidos: {count}")
    return df, {"T07_outliers_rango": int(count)}

# ─── T08: Detección y gestión de outliers (IQR) ──────────────────────────────
def t08_outliers_iqr(df, cols, source=""):
    total = 0
    for col in cols:
        if col not in df.columns:
            continue
        q1, q3 = df[col].quantile(0.25), df[col].quantile(0.75)
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        mask = (df[col] < lower) | (df[col] > upper)
        n = mask.sum()
        clipped = df[col].clip(lower=lower, upper=upper)
        if df[col].dtype.kind == "i":
            clipped = clipped.round().astype("int64")
        df[col] = clipped
        total += n
        if n > 0:
            log.info(f"T08 [{source}] {col}: {n} outliers acotados [IQR]")
    return df, {"T08_outliers_iqr": int(total)}

# ─── T09: Seudonimización de PII ─────────────────────────────────────────────
def t09_pii(df, pii_cols, source=""):
    count = 0
    for col in pii_cols:
        if col in df.columns:
            df[col] = df[col].apply(_hash_pii)
            count += 1
    log.info(f"T09 [{source}] campos PII seudonimizados: {count}")
    return df, {"T09_campos_pii": count}

# ─── T10: Validación referencial ─────────────────────────────────────────────
def t10_referencial(df_fact, df_dim, fact_key, dim_key, source=""):
    merged = df_fact.merge(df_dim[[dim_key]], left_on=fact_key, right_on=dim_key,
                           how="left", indicator=True)
    huerfanos = (merged["_merge"] == "left_only").sum()
    log.info(f"T10 [{source}] registros huérfanos {fact_key}→{dim_key}: {huerfanos}")
    return {"T10_huerfanos": int(huerfanos), "relacion": f"{fact_key}→{dim_key}"}


# ─── PIPELINE COMPLETO ────────────────────────────────────────────────────────
def run_transform():
    tracking = load_tracking()
    tracking.setdefault("transform", {})

    # ── F1 LaLiga ──────────────────────────────────────────────────────────────
    log.info("=== Transformando F1 LaLiga ===")
    df1 = pd.read_csv(os.path.join(RAW_DIR, "F1_laliga_raw.csv"), encoding="latin1", low_memory=False)
    entry1 = {"entrada": len(df1)}

    df1, r = t01_dedup(df1, source="F1"); entry1.update(r)
    df1, r = t03_blancos(df1, source="F1"); entry1.update(r)
    df1, r = t04_tipos_f1(df1); entry1.update(r)
    df1, r = t05_fechas(df1, ["Date"], source="F1"); entry1.update(r)
    df1, r = t06_texto(df1, ["HomeTeam","AwayTeam","FTR","HTR"], source="F1"); entry1.update(r)
    df1, r = t07_rangos(df1, source="F1"); entry1.update(r)
    df1, r = t08_outliers_iqr(df1, ["FTHG","FTAG","HS","AS","HST","AST"], source="F1"); entry1.update(r)
    df1, r = t02_nulos(df1, source="F1")
    entry1["salida"] = len(df1)
    entry1["descartados"] = entry1["entrada"] - entry1["salida"]
    df1.to_csv(os.path.join(PROC_DIR, "F1_laliga_clean.csv"), index=False)
    tracking["transform"]["F1"] = entry1
    log.info(f"F1: {entry1['entrada']} → {entry1['salida']} registros")

    # ── F2 Understat ───────────────────────────────────────────────────────────
    log.info("=== Transformando F2 Understat ===")
    df2 = pd.read_csv(os.path.join(RAW_DIR, "F2_understat_raw.csv"))
    entry2 = {"entrada": len(df2)}

    df2, r = t01_dedup(df2, key_cols=["team","season"], source="F2"); entry2.update(r)
    df2, r = t03_blancos(df2, source="F2"); entry2.update(r)
    df2, r = t04_tipos_f2(df2); entry2.update(r)
    df2, r = t06_texto(df2, ["team","season"], source="F2"); entry2.update(r)
    df2, r = t07_rangos(df2, source="F2"); entry2.update(r)
    df2, r = t08_outliers_iqr(df2, ["xG","xGA","xPTS","pts"], source="F2"); entry2.update(r)
    df2, r = t02_nulos(df2, source="F2")
    entry2["salida"] = len(df2)
    entry2["descartados"] = entry2["entrada"] - entry2["salida"]
    df2.to_csv(os.path.join(PROC_DIR, "F2_understat_clean.csv"), index=False)
    tracking["transform"]["F2"] = entry2
    log.info(f"F2: {entry2['entrada']} → {entry2['salida']} registros")

    # ── F3 FC24 ────────────────────────────────────────────────────────────────
    log.info("=== Transformando F3 FC24 ===")
    df3 = pd.read_csv(os.path.join(RAW_DIR, "F3_fc24_raw.csv"))
    entry3 = {"entrada": len(df3)}

    df3, r = t01_dedup(df3, key_cols=["player_id"], source="F3"); entry3.update(r)
    df3, r = t03_blancos(df3, source="F3"); entry3.update(r)
    df3, r = t04_tipos_f3(df3); entry3.update(r)
    df3, r = t06_texto(df3, ["short_name","club_name","league_name","nationality_name"], source="F3"); entry3.update(r)
    df3, r = t07_rangos(df3, source="F3"); entry3.update(r)
    df3, r = t08_outliers_iqr(df3, ["overall","value_eur","wage_eur","minutes_played"], source="F3"); entry3.update(r)
    df3, r = t09_pii(df3, ["long_name"], source="F3"); entry3.update(r)
    df3, r = t02_nulos(df3, source="F3")
    entry3["salida"] = len(df3)
    entry3["descartados"] = entry3["entrada"] - entry3["salida"]
    df3.to_csv(os.path.join(PROC_DIR, "F3_fc24_clean.csv"), index=False)
    tracking["transform"]["F3"] = entry3
    log.info(f"F3: {entry3['entrada']} → {entry3['salida']} registros")

    # T10 referencial: equipos de F2 en F3
    r10 = t10_referencial(df2, df3, "team", "club_name", source="F2→F3")
    tracking["transform"]["T10"] = r10

    save_tracking(tracking)
    log.info("TRANSFORM completado.")
    return df1, df2, df3

if __name__ == "__main__":
    run_transform()

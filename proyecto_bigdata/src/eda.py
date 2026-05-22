"""
MÓDULO EDA — Análisis Exploratorio de Datos (8 gráficas obligatorias)
Genera todas las figuras y las guarda en outputs/eda/
"""

import os, json, logging
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [EDA] %(message)s")
log = logging.getLogger(__name__)

PROC_DIR   = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
OUT_DIR    = os.path.join(os.path.dirname(__file__), "..", "outputs", "eda")
LOG_PATH   = os.path.join(os.path.dirname(__file__), "..", "logs", "pipeline_tracking.json")

os.makedirs(OUT_DIR, exist_ok=True)

# ── Paleta corporativa ────────────────────────────────────────────────────────
COLORS = ["#2563EB","#10B981","#F59E0B","#EF4444","#8B5CF6",
          "#EC4899","#06B6D4","#84CC16","#F97316","#6366F1"]
BG = "#0F172A"; FG = "#F1F5F9"; GRID = "#1E293B"

def style_ax(ax, title="", xlabel="", ylabel=""):
    ax.set_facecolor(BG)
    ax.figure.patch.set_facecolor(BG)
    ax.tick_params(colors=FG, labelsize=9)
    ax.xaxis.label.set_color(FG); ax.yaxis.label.set_color(FG)
    ax.title.set_color(FG)
    ax.set_title(title, fontsize=12, fontweight="bold", pad=10)
    ax.set_xlabel(xlabel, fontsize=10); ax.set_ylabel(ylabel, fontsize=10)
    ax.grid(True, color=GRID, alpha=0.6, linewidth=0.6)
    for spine in ax.spines.values():
        spine.set_edgecolor(GRID)

def savefig(name):
    path = os.path.join(OUT_DIR, name)
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close()
    log.info(f"  Guardado: {name}")
    return path


# ── G01: Heatmap de correlaciones ────────────────────────────────────────────
def g01_heatmap_corr(df3):
    log.info("G01 Heatmap correlaciones")
    num_cols = ["overall","potential","pace","shooting","passing","dribbling",
                "defending","physic","value_eur","wage_eur","age","goals_real","assists_real","minutes_played"]
    num_cols = [c for c in num_cols if c in df3.columns]
    corr = df3[num_cols].corr()

    fig, ax = plt.subplots(figsize=(13, 10), facecolor=BG)
    mask = np.triu(np.ones_like(corr, dtype=bool))
    sns.heatmap(corr, mask=mask, cmap="RdYlGn", vmin=-1, vmax=1,
                annot=True, fmt=".2f", linewidths=0.5, linecolor=GRID,
                annot_kws={"size": 7}, ax=ax,
                cbar_kws={"shrink": 0.8})
    ax.set_facecolor(BG)
    ax.tick_params(colors=FG, labelsize=8)
    ax.figure.patch.set_facecolor(BG)
    plt.xticks(rotation=45, ha="right")
    plt.yticks(rotation=0)
    ax.set_title("G01 — Heatmap de Correlaciones (FC24 Players)", color=FG,
                 fontsize=13, fontweight="bold", pad=14)
    for text in ax.texts:
        text.set_color("black")
    return savefig("G01_heatmap_correlaciones.png")


# ── G02: Histogramas + KDE ───────────────────────────────────────────────────
def g02_histogramas(df3):
    log.info("G02 Histogramas KDE")
    cols = ["overall","value_eur","wage_eur","age","pace","shooting"]
    fig, axes = plt.subplots(2, 3, figsize=(16, 9), facecolor=BG)
    fig.suptitle("G02 — Histogramas + KDE de Variables Continuas (FC24)", 
                 color=FG, fontsize=14, fontweight="bold", y=1.01)
    for ax, col, color in zip(axes.flat, cols, COLORS):
        data = df3[col].dropna()
        ax.set_facecolor(BG)
        ax.hist(data, bins=30, color=color, alpha=0.7, density=True, edgecolor=GRID)
        data.plot.kde(ax=ax, color="white", lw=2)
        style_ax(ax, title=col.replace("_"," ").title(), xlabel=col, ylabel="Densidad")
    plt.tight_layout()
    return savefig("G02_histogramas_kde.png")


# ── G03: Boxplots comparativos ───────────────────────────────────────────────
def g03_boxplots(df3):
    log.info("G03 Boxplots")
    top10 = df3.groupby("club_name")["overall"].mean().nlargest(10).index
    df_top = df3[df3["club_name"].isin(top10)].copy()

    fig, axes = plt.subplots(1, 2, figsize=(16, 7), facecolor=BG)
    fig.suptitle("G03 — Boxplots: Overall y Valor de Mercado por Equipo (Top 10)",
                 color=FG, fontsize=13, fontweight="bold")

    for ax, col, label in zip(axes, ["overall","value_eur"],
                              ["Overall Rating","Valor de Mercado (€)"]):
        ax.set_facecolor(BG)
        order = df_top.groupby("club_name")[col].median().sort_values(ascending=False).index
        bp = ax.boxplot(
            [df_top.loc[df_top["club_name"] == t, col].dropna().values for t in order],
            patch_artist=True, notch=True,
            medianprops=dict(color="white", lw=2),
            whiskerprops=dict(color=FG), capprops=dict(color=FG),
            flierprops=dict(marker="o", color=COLORS[3], alpha=0.4, ms=3)
        )
        for patch, color in zip(bp["boxes"], COLORS):
            patch.set_facecolor(color); patch.set_alpha(0.8)
        ax.set_xticklabels(order, rotation=35, ha="right", color=FG, fontsize=8)
        style_ax(ax, title=label, ylabel=label)

    plt.tight_layout()
    return savefig("G03_boxplots_equipo.png")


# ── G04: Barras de frecuencias ───────────────────────────────────────────────
def g04_barras_freq(df1):
    log.info("G04 Barras frecuencia")
    df1 = df1.copy()
    df1["HomeTeam"] = df1["HomeTeam"].str.strip().str.title()

    fig, axes = plt.subplots(1, 2, figsize=(16, 7), facecolor=BG)
    fig.suptitle("G04 — Frecuencias: Victorias Locales y Goles por Equipo (LaLiga)",
                 color=FG, fontsize=13, fontweight="bold")

    # Victorias locales
    wins = df1[df1["FTR"] == "H"]["HomeTeam"].value_counts().head(15)
    axes[0].set_facecolor(BG)
    bars = axes[0].barh(wins.index[::-1], wins.values[::-1], color=COLORS[0], alpha=0.85)
    for bar, val in zip(bars, wins.values[::-1]):
        axes[0].text(val + 0.3, bar.get_y() + bar.get_height()/2,
                     str(val), va="center", color=FG, fontsize=8)
    style_ax(axes[0], title="Top 15 Victorias como Local", xlabel="Victorias", ylabel="Equipo")
    axes[0].tick_params(colors=FG)

    # Goles totales
    goles_h = df1.groupby("HomeTeam")["FTHG"].sum()
    goles_a = df1.groupby("AwayTeam")["FTAG"].sum()
    goles = (goles_h.add(goles_a, fill_value=0)).nlargest(15)
    axes[1].set_facecolor(BG)
    bars2 = axes[1].barh(goles.index[::-1], goles.values[::-1], color=COLORS[1], alpha=0.85)
    for bar, val in zip(bars2, goles.values[::-1]):
        axes[1].text(val + 0.5, bar.get_y() + bar.get_height()/2,
                     str(int(val)), va="center", color=FG, fontsize=8)
    style_ax(axes[1], title="Top 15 Goles Totales (5 temporadas)", xlabel="Goles", ylabel="")
    axes[1].tick_params(colors=FG)

    plt.tight_layout()
    return savefig("G04_barras_frecuencias.png")


# ── G05: Serie temporal ──────────────────────────────────────────────────────
def g05_serie_temporal(df1):
    log.info("G05 Serie temporal")
    df1 = df1.copy()
    df1["Date"] = pd.to_datetime(df1["Date"], errors="coerce", utc=True)
    df1 = df1.dropna(subset=["Date"])
    df1["mes"] = df1["Date"].dt.to_period("M")

    monthly = df1.groupby("mes").agg(
        partidos=("FTHG","count"),
        goles=("FTHG","sum"),
        goles_away=("FTAG","sum")
    ).reset_index()
    monthly["mes_dt"] = monthly["mes"].dt.to_timestamp()
    monthly["goles_total"] = monthly["goles"] + monthly["goles_away"]

    fig, axes = plt.subplots(2, 1, figsize=(16, 10), facecolor=BG, sharex=True)
    fig.suptitle("G05 — Serie Temporal: Partidos y Goles por Mes (LaLiga 2020–2025)",
                 color=FG, fontsize=13, fontweight="bold")

    for ax in axes:
        ax.set_facecolor(BG)

    axes[0].plot(monthly["mes_dt"], monthly["partidos"], color=COLORS[0], lw=2, marker="o", ms=3)
    axes[0].fill_between(monthly["mes_dt"], monthly["partidos"], alpha=0.2, color=COLORS[0])
    style_ax(axes[0], title="Nº de Partidos por Mes", ylabel="Partidos")

    axes[1].plot(monthly["mes_dt"], monthly["goles_total"], color=COLORS[2], lw=2, marker="o", ms=3)
    axes[1].fill_between(monthly["mes_dt"], monthly["goles_total"], alpha=0.2, color=COLORS[2])
    style_ax(axes[1], title="Goles Totales por Mes", ylabel="Goles", xlabel="Fecha")

    plt.tight_layout()
    return savefig("G05_serie_temporal.png")


# ── G06: Scatter / Pairplot ──────────────────────────────────────────────────
def g06_scatter(df2, df3):
    log.info("G06 Scatter xG vs rendimiento")
    fig, axes = plt.subplots(1, 2, figsize=(16, 7), facecolor=BG)
    fig.suptitle("G06 — Scatter: xG vs Rendimiento Real (Understat) y Overall vs Valor (FC24)",
                 color=FG, fontsize=13, fontweight="bold")

    # xG vs pts
    ax = axes[0]
    ax.set_facecolor(BG)
    seasons = df2["season"].unique()
    for i, s in enumerate(seasons):
        d = df2[df2["season"] == s]
        ax.scatter(d["xG"], d["pts"], c=COLORS[i % len(COLORS)],
                   label=s, alpha=0.8, s=60, edgecolors="white", lw=0.4)
    # regression line
    from numpy.polynomial.polynomial import polyfit
    x, y = df2["xG"].values, df2["pts"].values
    b, m = polyfit(x, y, 1)
    xx = np.linspace(x.min(), x.max(), 100)
    ax.plot(xx, m * xx + b, color="white", lw=1.5, linestyle="--", label="Tendencia")
    style_ax(ax, title="xG Total vs Puntos (por temporada)", xlabel="xG Total", ylabel="Puntos")
    ax.legend(fontsize=7, facecolor=GRID, labelcolor=FG, framealpha=0.8)

    # Overall vs Value
    ax2 = axes[1]
    ax2.set_facecolor(BG)
    df3_s = df3.sample(min(800, len(df3)), random_state=42)
    sc = ax2.scatter(df3_s["overall"], df3_s["value_eur"],
                     c=df3_s["age"], cmap="plasma", alpha=0.6, s=25, edgecolors="none")
    cb = plt.colorbar(sc, ax=ax2)
    cb.set_label("Edad", color=FG, fontsize=9)
    cb.ax.yaxis.set_tick_params(color=FG)
    plt.setp(cb.ax.yaxis.get_ticklabels(), color=FG)
    style_ax(ax2, title="Overall vs Valor de Mercado (color=Edad)", xlabel="Overall", ylabel="Valor (€)")

    plt.tight_layout()
    return savefig("G06_scatter_pairplot.png")


# ── G07: Mapa de calor geográfico (alternativa: heatmap por liga/equipo) ─────
def g07_heatmap_rendimiento(df2):
    log.info("G07 Heatmap rendimiento por equipo/temporada")
    pivot = df2.pivot_table(index="team", columns="season", values="pts", aggfunc="mean")
    pivot = pivot.sort_values(pivot.columns[-1], ascending=False).head(15)

    fig, ax = plt.subplots(figsize=(13, 9), facecolor=BG)
    sns.heatmap(pivot, cmap="YlOrRd", annot=True, fmt=".0f",
                linewidths=0.5, linecolor=GRID,
                annot_kws={"size": 9}, ax=ax,
                cbar_kws={"shrink": 0.8})
    ax.set_facecolor(BG)
    ax.figure.patch.set_facecolor(BG)
    ax.tick_params(colors=FG, labelsize=8)
    ax.set_title("G07 — Puntos por Equipo y Temporada (LaLiga)", color=FG,
                 fontsize=13, fontweight="bold", pad=14)
    ax.set_xlabel("Temporada", color=FG); ax.set_ylabel("Equipo", color=FG)
    plt.xticks(rotation=30); plt.yticks(rotation=0)
    for text in ax.texts:
        text.set_color("black")
    return savefig("G07_heatmap_rendimiento.png")


# ── G08: Funnel de tracking del pipeline ────────────────────────────────────
def g08_funnel_tracking():
    log.info("G08 Funnel tracking")
    if not os.path.exists(LOG_PATH):
        log.warning("No hay tracking.json, usando datos de ejemplo")
        fases = ["EXTRACT F1","EXTRACT F2","EXTRACT F3","T01 Dedup","T02 Nulos","T03 Blancos",
                 "T04 Tipos","T07 Rangos","T08 Outliers","MERGE FINAL"]
        registros = [9500, 100, 480, 9450, 9430, 9420, 9420, 9400, 9380, 9380]
    else:
        with open(LOG_PATH) as f:
            t = json.load(f)
        fases = []; registros = []
        for src in ["F1_laliga","F2_understat","F3_fc24"]:
            data = t.get("extract", {}).get(src, {})
            if data:
                fases.append(f"EXTRACT {src.replace('_laliga','').replace('_understat','').replace('_fc24','').upper()}")
                registros.append(data.get("registros", 0))
        for src in ["F1","F2","F3"]:
            data = t.get("transform", {}).get(src, {})
            if data:
                fases.append(f"TRANSFORM {src} salida")
                registros.append(data.get("salida", 0))
        for tbl, n in t.get("load", {}).get("tablas", {}).items():
            fases.append(f"LOAD {tbl}")
            registros.append(n)

    colors = [COLORS[i % len(COLORS)] for i in range(len(fases))]
    fig, ax = plt.subplots(figsize=(14, 7), facecolor=BG)
    ax.set_facecolor(BG)
    bars = ax.barh(fases[::-1], registros[::-1], color=colors[::-1], alpha=0.85, height=0.6)
    for bar, val in zip(bars, registros[::-1]):
        ax.text(val + max(registros) * 0.01, bar.get_y() + bar.get_height()/2,
                f"{val:,}", va="center", color=FG, fontsize=9, fontweight="bold")
    style_ax(ax, title="G08 — Funnel de Tracking del Pipeline ETL",
             xlabel="Nº de Registros", ylabel="Fase")
    ax.tick_params(colors=FG)
    plt.tight_layout()
    return savefig("G08_funnel_tracking.png")


def run_eda():
    log.info("=== Iniciando EDA ===")
    df1 = pd.read_csv(os.path.join(PROC_DIR, "F1_laliga_clean.csv"), low_memory=False)
    df2 = pd.read_csv(os.path.join(PROC_DIR, "F2_understat_clean.csv"))
    df3 = pd.read_csv(os.path.join(PROC_DIR, "F3_fc24_clean.csv"))

    # Asegurar tipos numéricos
    for col in ["overall","value_eur","wage_eur","age","pace","shooting",
                "passing","dribbling","defending","physic","goals_real",
                "assists_real","minutes_played","potential"]:
        if col in df3.columns:
            df3[col] = pd.to_numeric(df3[col], errors="coerce")
    for col in ["FTHG","FTAG","HS","AS","HST","AST","HF","AF","HC","AC","HY","AY","HR","AR"]:
        if col in df1.columns:
            df1[col] = pd.to_numeric(df1[col], errors="coerce").fillna(0)
    for col in ["xG","xGA","pts","xPTS"]:
        if col in df2.columns:
            df2[col] = pd.to_numeric(df2[col], errors="coerce")

    paths = {}
    paths["G01"] = g01_heatmap_corr(df3)
    paths["G02"] = g02_histogramas(df3)
    paths["G03"] = g03_boxplots(df3)
    paths["G04"] = g04_barras_freq(df1)
    paths["G05"] = g05_serie_temporal(df1)
    paths["G06"] = g06_scatter(df2, df3)
    paths["G07"] = g07_heatmap_rendimiento(df2)
    paths["G08"] = g08_funnel_tracking()

    log.info(f"EDA completado. {len(paths)} gráficas generadas en {OUT_DIR}")
    return paths

if __name__ == "__main__":
    run_eda()

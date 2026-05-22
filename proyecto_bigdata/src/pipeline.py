"""
PIPELINE PRINCIPAL — Ejecuta todas las fases en orden:
  1. EXTRACT  → data/raw/
  2. TRANSFORM → data/processed/
  3. LOAD     → data/final/ + SQLite
  4. EDA      → outputs/eda/
"""

import os, sys, json, logging, time
from datetime import datetime

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [PIPELINE] %(message)s",
                    handlers=[
                        logging.StreamHandler(),
                        logging.FileHandler(
                            os.path.join(os.path.dirname(__file__), "..", "logs", "pipeline.log"),
                            mode="w"
                        )
                    ])
log = logging.getLogger(__name__)

SRC_DIR  = os.path.dirname(__file__)
BASE_DIR = os.path.join(SRC_DIR, "..")

os.makedirs(os.path.join(BASE_DIR, "logs"), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "outputs", "eda"), exist_ok=True)

sys.path.insert(0, SRC_DIR)

def run():
    start = time.time()
    log.info("=" * 60)
    log.info("INICIO DEL PIPELINE ETL — Análisis Fútbol LaLiga")
    log.info(f"Timestamp: {datetime.now()}")
    log.info("=" * 60)

    # ── FASE 1: EXTRACT ───────────────────────────────────────────
    log.info("\n>>> FASE 1: EXTRACT")
    from extract import run_extract
    df1, df2, df3 = run_extract()
    log.info(f"F1={len(df1)} F2={len(df2)} F3={len(df3)} registros extraídos")

    # ── FASE 2: TRANSFORM ─────────────────────────────────────────
    log.info("\n>>> FASE 2: TRANSFORM")
    from transform import run_transform
    df1c, df2c, df3c = run_transform()
    log.info(f"F1={len(df1c)} F2={len(df2c)} F3={len(df3c)} registros limpios")

    # ── FASE 3: LOAD ──────────────────────────────────────────────
    log.info("\n>>> FASE 3: LOAD")
    from load import run_load
    dim_t, dim_e, dim_s, dim_j, fact = run_load()
    log.info(f"FACT_RENDIMIENTO: {len(fact)} filas cargadas")

    # ── FASE 4: EDA ───────────────────────────────────────────────
    log.info("\n>>> FASE 4: EDA")
    from eda import run_eda
    paths = run_eda()
    log.info(f"EDA: {len(paths)} gráficas generadas")

    elapsed = time.time() - start
    log.info("\n" + "=" * 60)
    log.info(f"PIPELINE COMPLETADO en {elapsed:.1f}s")
    log.info("=" * 60)

    # Resumen final
    tracking_path = os.path.join(BASE_DIR, "logs", "pipeline_tracking.json")
    if os.path.exists(tracking_path):
        with open(tracking_path) as f:
            t = json.load(f)
        log.info("\n── RESUMEN TRACKING ──")
        for fase, data in t.items():
            log.info(f"  {fase}: {json.dumps(data, default=str)[:120]}...")

    return True

if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)

import os

# ── Aerodynamic Physical Constants ───────────────────────────────────────────
AIR_DENSITY = 1.225            # kg/m^3 (sea level standard air density)
REFERENCE_WING_AREA = 0.45    # m^2 (GT3 Rear Wing surface area)

# ── Operational & Threshold Defaults ─────────────────────────────────────────
DEFAULT_VELOCITY_KMH = 120.0
AOA_MIN_DEG = -5.0
AOA_MAX_DEG = 20.0
STALL_AOA_THRESHOLD_DEG = 15.0

# ── Dataset & File Paths ──────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASETS_DIR = os.path.join(BASE_DIR, "datasets")
DEFAULT_DATASET_PATH = os.path.join(DATASETS_DIR, "naca0012_polars.csv")

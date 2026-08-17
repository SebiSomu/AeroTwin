import os

# Aerodynamic Physical Constants
AIR_DENSITY = 1.225   # kg/m^3 (sea level standard air density)

# Operational & Threshold Defaults
DEFAULT_VELOCITY_KMH = 120.0
AOA_MIN_DEG = -5.0
AOA_MAX_DEG = 20.0
STALL_AOA_THRESHOLD_DEG = 15.0
NEAR_STALL_THRESHOLD_DEG = 12.0
PEAK_EFFICIENCY_AOA_MIN = 3.0
PEAK_EFFICIENCY_AOA_MAX = 5.0
PEAK_EFFICIENCY_BAND_FRACTION = 0.95

# Dataset & File Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASETS_DIR = os.path.join(BASE_DIR, "datasets")
DEFAULT_DATASET_PATH = os.path.join(DATASETS_DIR, "naca0012_polars.csv")

# Model Cache
MODEL_CACHE_DIR = os.path.join(BASE_DIR, "cache")
DEFAULT_MODEL_CACHE_PATH = os.path.join(MODEL_CACHE_DIR, "surrogate_model.joblib")

# Aerodynamic Status Definitions
STATUS_STALLED = {
    "label": "STALLED",
    "sub": "Boundary layer separated",
    "color": "#D9584F",
    "glow": "rgba(217,88,79,0.35)",
}

STATUS_NEAR_STALL = {
    "label": "NEAR STALL",
    "sub": "Approaching critical AoA",
    "color": "#E0982E",
    "glow": "rgba(224,152,46,0.3)",
}

STATUS_PEAK_EFFICIENCY = {
    "label": "PEAK EFFICIENCY",
    "sub": "Optimal CL / CD ratio",
    "color": "#C9A15F",
    "glow": "rgba(201,161,95,0.35)",
}

STATUS_LINEAR_REGION = {
    "label": "LINEAR REGION",
    "sub": "Attached flow",
    "color": "#7FA6B3",
    "glow": "rgba(127,166,179,0.25)",
}

def get_aero_status(aoa: float, stall_threshold: float = STALL_AOA_THRESHOLD_DEG, near_stall_threshold: float = NEAR_STALL_THRESHOLD_DEG, peak_min: float = PEAK_EFFICIENCY_AOA_MIN, peak_max: float = PEAK_EFFICIENCY_AOA_MAX) -> dict:
    """Return the aerodynamic flow status dict for a given angle of attack.

    The thresholds default to fallback constants, but AerodynamicSurrogateModel
    computes and passes in the data-derived boundaries from the actual dataset
    (see _compute_flow_regimes), so this adapts automatically to any loaded airfoil polar.
    """
    if aoa >= stall_threshold:
        return STATUS_STALLED
    if aoa >= near_stall_threshold:
        return STATUS_NEAR_STALL
    if peak_min <= aoa <= peak_max:
        return STATUS_PEAK_EFFICIENCY
    return STATUS_LINEAR_REGION
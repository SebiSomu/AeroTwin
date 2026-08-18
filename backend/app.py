import sys
import os
import types
from pathlib import Path

_PKG_DIR = Path(__file__).resolve().parent
_PHY_DIR = _PKG_DIR / "physics_utils"

if "physics_utils.constants" not in sys.modules:
    _physics_pkg = types.ModuleType("physics_utils")
    _physics_pkg.__path__ = [str(_PHY_DIR)]
    _physics_pkg.__package__ = "physics_utils"
    sys.modules["physics_utils"] = _physics_pkg

    _c = types.ModuleType("physics_utils.constants")
    _c.__file__ = str(_PHY_DIR / "constants.py")
    _c.AIR_DENSITY = 1.225
    _c.DEFAULT_VELOCITY_KMH = 120.0
    _c.AOA_MIN_DEG = -5.0
    _c.AOA_MAX_DEG = 20.0
    _c.STALL_AOA_THRESHOLD_DEG = 15.0
    _c.NEAR_STALL_THRESHOLD_DEG = 12.0
    _c.PEAK_EFFICIENCY_AOA_MIN = 3.0
    _c.PEAK_EFFICIENCY_AOA_MAX = 5.0
    _c.PEAK_EFFICIENCY_BAND_FRACTION = 0.95
    _c.BASE_DIR = _PHY_DIR
    _c.DATASETS_DIR = _PKG_DIR / "datasets"
    _c.DEFAULT_DATASET_PATH = _PKG_DIR / "datasets" / "naca0012_polars.csv"
    _c.MODEL_CACHE_DIR = _PKG_DIR / "cache"
    _c.DEFAULT_MODEL_CACHE_PATH = _c.MODEL_CACHE_DIR / "surrogate_model.joblib"
    os.makedirs(str(_c.MODEL_CACHE_DIR), exist_ok=True)
    _c.STATUS_STALLED = {
        "label": "STALLED",
        "sub": "Boundary layer separated",
        "color": "#D9584F",
        "glow": "rgba(217,88,79,0.35)",
    }
    _c.STATUS_NEAR_STALL = {
        "label": "NEAR STALL",
        "sub": "Approaching critical AoA",
        "color": "#E0982E",
        "glow": "rgba(224,152,46,0.3)",
    }
    _c.STATUS_PEAK_EFFICIENCY = {
        "label": "PEAK EFFICIENCY",
        "sub": "Optimal CL / CD ratio",
        "color": "#C9A15F",
        "glow": "rgba(201,161,95,0.35)",
    }
    _c.STATUS_LINEAR_REGION = {
        "label": "LINEAR REGION",
        "sub": "Attached flow",
        "color": "#7FA6B3",
        "glow": "rgba(127,166,179,0.25)",
    }
    def _get_aero_status(aoa: float,
                         stall_threshold: float = _c.STALL_AOA_THRESHOLD_DEG,
                         near_stall_threshold: float = _c.NEAR_STALL_THRESHOLD_DEG,
                         peak_min: float = _c.PEAK_EFFICIENCY_AOA_MIN,
                         peak_max: float = _c.PEAK_EFFICIENCY_AOA_MAX) -> dict:
        if aoa >= stall_threshold:
            return _c.STATUS_STALLED
        if aoa >= near_stall_threshold:
            return _c.STATUS_NEAR_STALL
        if peak_min <= aoa <= peak_max:
            return _c.STATUS_PEAK_EFFICIENCY
        return _c.STATUS_LINEAR_REGION
    _c.get_aero_status = _get_aero_status
    sys.modules["physics_utils.constants"] = _c


from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import time
from ml_model import AerodynamicSurrogateModel
from plotting import generate_or_load_aero_chart

from physics_utils.constants import AOA_MIN_DEG, AOA_MAX_DEG, DEFAULT_VELOCITY_KMH

app = Flask(__name__)
CORS(app)

surrogate_model = AerodynamicSurrogateModel()
chart_path = generate_or_load_aero_chart(surrogate_model)

@app.route("/api/v1/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "server running",
        "service": "AeroTwin Cloud Surrogate Engine",
        "model_trained": surrogate_model.is_trained,
        "rmse_cl": round(surrogate_model.rmse_cl, 4),
        "rmse_cd": round(surrogate_model.rmse_cd, 4),
        "stall_aoa": round(surrogate_model.stall_aoa, 2),
        "near_stall_aoa": round(surrogate_model.near_stall_aoa, 2),
        "peak_efficiency_aoa": round(surrogate_model.peak_efficiency_aoa, 2),
        "cl_max": round(surrogate_model.cl_max, 3),
        "linear_lift_slope": round(surrogate_model.linear_lift_slope, 4),
        "chart_available": os.path.exists(chart_path),
    })

@app.route("/api/v1/predict", methods=["POST"])
def predict_efficiency():
    start_time = time.perf_counter()
    data = request.get_json() or {}

    try:
        angle_of_attack = float(data.get("angle_of_attack", 4.0))
        velocity_kmh = float(data.get("velocity_kmh", DEFAULT_VELOCITY_KMH))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid numerical parameters"}), 400

    if not (AOA_MIN_DEG <= angle_of_attack <= AOA_MAX_DEG):
        return jsonify({"error": f"angle_of_attack must be between {AOA_MIN_DEG}° and {AOA_MAX_DEG}°"}), 400

    try:
        res = surrogate_model.predict(angle_of_attack, velocity_kmh)
        inference_time = (time.perf_counter() - start_time) * 1000.0
        res["inference_time_ms"] = round(inference_time, 3)
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/v1/chart", methods=["GET"])
def get_aero_chart():
    if os.path.exists(chart_path):
        return send_file(chart_path, mimetype="image/png")
    return jsonify({"error": "Chart not generated"}), 444

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)


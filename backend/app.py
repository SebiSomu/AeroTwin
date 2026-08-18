import os
import time
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

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
    return jsonify({"error": "Chart not generated"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
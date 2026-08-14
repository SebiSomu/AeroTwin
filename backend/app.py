from flask import Flask, request, jsonify
from flask_cors import CORS
import time
from ml_model import AerodynamicSurrogateModel

app = Flask(__name__)
CORS(app)

# Initialize ML surrogate model at startup
surrogate_model = AerodynamicSurrogateModel()

@app.route("/api/v1/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "server running",
        "service": "AeroTwin Cloud Surrogate Engine",
        "model_trained": surrogate_model.is_trained,
        "rmse_cl": round(surrogate_model.rmse_cl, 4),
        "rmse_cd": round(surrogate_model.rmse_cd, 4)
    })

@app.route("/api/v1/predict", methods=["POST"])
def predict_efficiency():
    start_time = time.perf_counter()
    data = request.get_json() or {}
    
    try:
        angle_of_attack = float(data.get("angle_of_attack", 4.0))
        velocity_kmh = float(data.get("velocity_kmh", 120.0))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid numerical parameters"}), 400

    if not (-5.0 <= angle_of_attack <= 20.0):
        return jsonify({"error": "angle_of_attack must be between -5.0 and 20.0 degrees"}), 400

    try:
        res = surrogate_model.predict(angle_of_attack, velocity_kmh)
        inference_time = (time.perf_counter() - start_time) * 1000.0
        res["inference_time_ms"] = round(inference_time, 3)
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)

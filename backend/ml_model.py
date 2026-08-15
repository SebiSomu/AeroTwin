import os
import hashlib
import joblib
import pandas as pd
import numpy as np
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_squared_error

from constants import (
    AIR_DENSITY,
    REFERENCE_WING_AREA,
    DEFAULT_DATASET_PATH,
    DEFAULT_MODEL_CACHE_PATH,
    DEFAULT_VELOCITY_KMH,
    STALL_AOA_THRESHOLD_DEG,
    PEAK_EFFICIENCY_AOA_MIN,
    PEAK_EFFICIENCY_AOA_MAX,
    PEAK_EFFICIENCY_BAND_FRACTION,
    get_aero_status,
)

class AerodynamicSurrogateModel:
    """
    Machine Learning Surrogate Model for millisecond-level prediction of
    aerodynamic coefficients (CL, CD), efficiency (E = CL / CD), and forces.
    """
    def __init__(self, dataset_path: str = None, cache_path: str = None):
        if dataset_path is None:
            dataset_path = DEFAULT_DATASET_PATH
        if cache_path is None:
            cache_path = DEFAULT_MODEL_CACHE_PATH

        self.dataset_path = dataset_path
        self.cache_path = cache_path
        self.model_cl = None
        self.model_cd = None
        self.rmse_cl = 0.0
        self.rmse_cd = 0.0
        self.is_trained = False
        self.peak_efficiency_aoa = None
        self.peak_efficiency_value = None
        self.peak_efficiency_aoa_min = PEAK_EFFICIENCY_AOA_MIN
        self.peak_efficiency_aoa_max = PEAK_EFFICIENCY_AOA_MAX

        self._load_or_train()

    @staticmethod
    def _hash_file(path: str) -> str:
        """MD5 hash of a file's contents, used to detect dataset changes."""
        hasher = hashlib.md5()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _load_or_train(self):
        """Load a cached pipeline if the dataset hasn't changed, else retrain."""
        current_hash = self._hash_file(self.dataset_path)
        loaded_from_cache = False

        if os.path.exists(self.cache_path):
            try:
                cached = joblib.load(self.cache_path)
                if cached.get("dataset_hash") == current_hash:
                    self.model_cl = cached["model_cl"]
                    self.model_cd = cached["model_cd"]
                    self.rmse_cl = cached["rmse_cl"]
                    self.rmse_cd = cached["rmse_cd"]
                    self.is_trained = True
                    loaded_from_cache = True
                    print(f"[ML Model] Loaded cached pipeline from {self.cache_path}")
                    print(f"[ML Model] CL RMSE: {self.rmse_cl:.4f} | CD RMSE: {self.rmse_cd:.4f}")
                else:
                    print("[ML Model] Dataset changed since last cache — retraining.")
            except Exception as e:
                print(f"[ML Model] Cache unreadable ({e}) — retraining.")

        if not loaded_from_cache:
            self.train_model()
            self._save_cache(current_hash)

        self._compute_peak_efficiency_band()

    def _save_cache(self, dataset_hash: str):
        """Persist the fitted pipelines to disk alongside the dataset hash."""
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        joblib.dump({
            "dataset_hash": dataset_hash,
            "model_cl": self.model_cl,
            "model_cd": self.model_cd,
            "rmse_cl": self.rmse_cl,
            "rmse_cd": self.rmse_cd,
        }, self.cache_path)
        print(f"[ML Model] Cached trained pipeline to {self.cache_path}")

    def _compute_peak_efficiency_band(self):
        """
        Derive the 'peak efficiency' AoA band from the raw dataset via linear
        interpolation — deliberately NOT from the fitted degree-4 CL/CD
        polynomials.

        An earlier version of this tried argmax(CL/CD) straight off the
        trained pipelines. That was measurably *less* accurate on this
        dataset: model_cl and model_cd are each independently fit, so
        dividing them compounds their individual fitting errors. On this
        dataset it shifted the apparent peak from the true 4.5° to 6.5° and
        even introduced a spurious second local extremum that isn't present
        in the actual measurements. Interpolating the raw points instead
        reproduces the true measured optimum exactly and stays unimodal.
        """
        df = pd.read_csv(self.dataset_path)
        aoa = df['angle_of_attack'].values
        cl = df['cl'].values
        cd = df['cd'].values

        fine_grid = np.linspace(aoa.min(), aoa.max(), 2001)
        cl_interp = np.interp(fine_grid, aoa, cl)
        cd_interp = np.interp(fine_grid, aoa, cd)
        efficiency = cl_interp / np.maximum(cd_interp, 0.005)

        peak_idx = int(np.argmax(efficiency))
        peak_value = float(efficiency[peak_idx])
        threshold = peak_value * PEAK_EFFICIENCY_BAND_FRACTION

        left_idx = peak_idx
        while left_idx > 0 and efficiency[left_idx - 1] >= threshold:
            left_idx -= 1
        right_idx = peak_idx
        while right_idx < len(fine_grid) - 1 and efficiency[right_idx + 1] >= threshold:
            right_idx += 1

        self.peak_efficiency_aoa = round(float(fine_grid[peak_idx]), 2)
        self.peak_efficiency_value = round(peak_value, 2)
        self.peak_efficiency_aoa_min = round(float(fine_grid[left_idx]), 2)
        self.peak_efficiency_aoa_max = round(float(fine_grid[right_idx]), 2)

        print(
            f"[ML Model] Peak efficiency (from data): {self.peak_efficiency_value} "
            f"at {self.peak_efficiency_aoa}° | band "
            f"{self.peak_efficiency_aoa_min}°–{self.peak_efficiency_aoa_max}°"
        )

    def train_model(self):
        """Train scikit-learn regressor pipeline on NACA 0012 polar dataset."""
        df = pd.read_csv(self.dataset_path)
        
        X = df[['angle_of_attack']].values
        y_cl = df['cl'].values
        y_cd = df['cd'].values
        
        self.model_cl = Pipeline([
            ('poly', PolynomialFeatures(degree=4)),
            ('ridge', Ridge(alpha=0.001))
        ])
        
        self.model_cd = Pipeline([
            ('poly', PolynomialFeatures(degree=4)),
            ('ridge', Ridge(alpha=0.001))
        ])
        
        self.model_cl.fit(X, y_cl)
        self.model_cd.fit(X, y_cd)
        
        pred_cl = self.model_cl.predict(X)
        pred_cd = self.model_cd.predict(X)
        
        self.rmse_cl = np.sqrt(mean_squared_error(y_cl, pred_cl))
        self.rmse_cd = np.sqrt(mean_squared_error(y_cd, pred_cd))
        self.is_trained = True
        
        print(f"[ML Model] Training complete.")
        print(f"[ML Model] CL RMSE: {self.rmse_cl:.4f} | CD RMSE: {self.rmse_cd:.4f}")

    def predict(self, angle_of_attack: float, velocity_kmh: float = DEFAULT_VELOCITY_KMH) -> dict:
        """
        Predict aerodynamic efficiency (CL / CD) and aerodynamic forces.
        """
        if not self.is_trained:
            raise RuntimeError("ML Surrogate Model is not trained yet.")
            
        X_input = np.array([[angle_of_attack]])
        cl = float(self.model_cl.predict(X_input)[0])
        cd = float(self.model_cd.predict(X_input)[0])
        
        cd_safe = max(cd, 0.005)
        efficiency = cl / cd_safe
        
        v_ms = velocity_kmh / 3.6
        dynamic_pressure = 0.5 * AIR_DENSITY * (v_ms ** 2)
        
        downforce_n = dynamic_pressure * REFERENCE_WING_AREA * cl
        drag_n = dynamic_pressure * REFERENCE_WING_AREA * cd
        
        is_stalled = angle_of_attack >= STALL_AOA_THRESHOLD_DEG
        aero_status = get_aero_status(
            angle_of_attack,
            peak_min=self.peak_efficiency_aoa_min,
            peak_max=self.peak_efficiency_aoa_max,
        )

        return {
            "angle_of_attack": round(float(angle_of_attack), 2),
            "velocity_kmh": round(float(velocity_kmh), 1),
            "cl": round(cl, 4),
            "cd": round(cd, 4),
            "efficiency": round(efficiency, 2),
            "downforce_n": round(downforce_n, 2),
            "drag_n": round(drag_n, 2),
            "is_stalled": is_stalled,
            "status": aero_status,
        }

if __name__ == "__main__":
    model = AerodynamicSurrogateModel()
    res = model.predict(4.0, 120.0)
    print("Sample prediction at 4.0° AoA:", res)
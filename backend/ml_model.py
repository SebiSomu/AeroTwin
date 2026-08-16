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
    NEAR_STALL_THRESHOLD_DEG,
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

        # Data-derived flow regime boundaries (calculated from polar curves)
        self.stall_aoa = STALL_AOA_THRESHOLD_DEG
        self.near_stall_aoa = NEAR_STALL_THRESHOLD_DEG
        self.cl_max = 1.45
        self.linear_lift_slope = 0.105
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
                if cached.get("dataset_hash") == current_hash and "stall_aoa" in cached:
                    self.model_cl = cached["model_cl"]
                    self.model_cd = cached["model_cd"]
                    self.rmse_cl = cached["rmse_cl"]
                    self.rmse_cd = cached["rmse_cd"]
                    self.stall_aoa = cached.get("stall_aoa", STALL_AOA_THRESHOLD_DEG)
                    self.near_stall_aoa = cached.get("near_stall_aoa", NEAR_STALL_THRESHOLD_DEG)
                    self.cl_max = cached.get("cl_max", 1.45)
                    self.linear_lift_slope = cached.get("linear_lift_slope", 0.105)
                    self.peak_efficiency_aoa = cached.get("peak_efficiency_aoa", 4.5)
                    self.peak_efficiency_value = cached.get("peak_efficiency_value", 35.0)
                    self.peak_efficiency_aoa_min = cached.get("peak_efficiency_aoa_min", PEAK_EFFICIENCY_AOA_MIN)
                    self.peak_efficiency_aoa_max = cached.get("peak_efficiency_aoa_max", PEAK_EFFICIENCY_AOA_MAX)
                    self.is_trained = True
                    loaded_from_cache = True
                    print(f"[ML Model] Loaded cached pipeline from {self.cache_path}")
                    print(f"[ML Model] CL RMSE: {self.rmse_cl:.4f} | CD RMSE: {self.rmse_cd:.4f}")
                else:
                    print("[ML Model] Dataset or schema changed — retraining.")
            except Exception as e:
                print(f"[ML Model] Cache unreadable ({e}) — retraining.")

        if not loaded_from_cache:
            self.train_model()
            self._compute_flow_regimes()
            self._save_cache(current_hash)
        else:
            self._compute_flow_regimes()

    def _save_cache(self, dataset_hash: str):
        """Persist the fitted pipelines and learned regimes to disk alongside the dataset hash."""
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        joblib.dump({
            "dataset_hash": dataset_hash,
            "model_cl": self.model_cl,
            "model_cd": self.model_cd,
            "rmse_cl": self.rmse_cl,
            "rmse_cd": self.rmse_cd,
            "stall_aoa": self.stall_aoa,
            "near_stall_aoa": self.near_stall_aoa,
            "cl_max": self.cl_max,
            "linear_lift_slope": self.linear_lift_slope,
            "peak_efficiency_aoa": self.peak_efficiency_aoa,
            "peak_efficiency_value": self.peak_efficiency_value,
            "peak_efficiency_aoa_min": self.peak_efficiency_aoa_min,
            "peak_efficiency_aoa_max": self.peak_efficiency_aoa_max,
        }, self.cache_path)
        print(f"[ML Model] Cached trained pipeline to {self.cache_path}")

    def _compute_flow_regimes(self):
        """
        Derive all flow regimes directly from the polar dataset via interpolation
        and calculus (numerical derivatives):
        - Critical Stall Angle: argmax(CL) where dCL/dAoA = 0
        - Near Stall Boundary: inflection point where dCL/dAoA drops < 40% of linear slope
        - Peak Efficiency Band: AoA envelope where CL/CD stays within 95% of maximum
        - Linear Lift Slope: baseline dCL/dAoA around 0° incidence
        """
        df = pd.read_csv(self.dataset_path)
        aoa = df['angle_of_attack'].values
        cl = df['cl'].values
        cd = df['cd'].values

        fine_grid = np.linspace(aoa.min(), aoa.max(), 2001)
        cl_interp = np.interp(fine_grid, aoa, cl)
        cd_interp = np.interp(fine_grid, aoa, cd)
        efficiency = cl_interp / np.maximum(cd_interp, 0.005)

        # 1. Critical Stall AoA: argmax(CL)
        stall_idx = int(np.argmax(cl_interp))
        self.stall_aoa = round(float(fine_grid[stall_idx]), 2)
        self.cl_max = round(float(cl_interp[stall_idx]), 3)

        # 2. Linear Lift Slope (around 0° to 5° AoA)
        zero_idx = np.argmin(np.abs(fine_grid - 0.0))
        idx_5deg = np.argmin(np.abs(fine_grid - 5.0))
        if idx_5deg != zero_idx:
            linear_slope = (cl_interp[idx_5deg] - cl_interp[zero_idx]) / (fine_grid[idx_5deg] - fine_grid[zero_idx])
        else:
            linear_slope = 0.105
        self.linear_lift_slope = round(float(linear_slope), 4)

        # 3. Near-Stall Threshold: point where dCL/dAoA drops < 40% of linear slope before stall
        dcl_da = np.gradient(cl_interp, fine_grid)
        near_stall_idx = stall_idx
        for i in range(zero_idx, stall_idx):
            if dcl_da[i] < 0.4 * linear_slope or cl_interp[i] >= 0.95 * self.cl_max:
                near_stall_idx = i
                break
        self.near_stall_aoa = round(float(fine_grid[near_stall_idx]), 2)

        # 4. Peak Efficiency Band
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
            f"[ML Model] Flow Regimes Derived: Stall={self.stall_aoa}° (CL_max={self.cl_max}) | "
            f"Near-Stall={self.near_stall_aoa}° | Peak Efficiency={self.peak_efficiency_value} at {self.peak_efficiency_aoa}° "
            f"(band {self.peak_efficiency_aoa_min}°–{self.peak_efficiency_aoa_max}°) | Slope={self.linear_lift_slope}/°"
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
        
        is_stalled = angle_of_attack >= self.stall_aoa
        aero_status = get_aero_status(
            angle_of_attack,
            stall_threshold=self.stall_aoa,
            near_stall_threshold=self.near_stall_aoa,
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
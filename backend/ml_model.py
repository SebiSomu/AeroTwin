import os
import hashlib
import joblib
import pandas as pd
import numpy as np
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_squared_error

from constants import (
    AIR_DENSITY,
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

from visual_model_config import (REFERENCE_WING_AREA)

from formulas import (
    calculate_dynamic_pressure,
    calculate_aerodynamic_forces,
    calculate_aerodynamic_efficiency,
    calculate_prandtl_3d_correction,
    calculate_linear_lift_slope,
    calculate_stall_characteristics,
    calculate_near_stall_angle,
    calculate_peak_efficiency_envelope,
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

    def _apply_3d_correction(self, cl_2d, cd_2d):
        """Delegate Prandtl lifting-line finite-wing correction to physics module."""
        return calculate_prandtl_3d_correction(cl_2d, cd_2d, self.linear_lift_slope)

    def _compute_flow_regimes(self):
        """
        Derive flow regimes directly from polar dataset via calculus & physics formulas:
        - Critical Stall Angle: argmax(CL) where dCL/dAoA = 0
        - Linear Lift Slope: baseline dCL/dAoA around 0° incidence
        - Near Stall Boundary: inflection point where dCL/dAoA drops < 40% of linear slope
        - Peak Efficiency Band: AoA envelope where CL/CD stays within 95% of maximum
        """
        df = pd.read_csv(self.dataset_path)
        aoa = df['angle_of_attack'].values
        cl = df['cl'].values
        cd = df['cd'].values

        fine_grid = np.linspace(aoa.min(), aoa.max(), 2001)
        cl_interp = np.interp(fine_grid, aoa, cl)
        cd_interp = np.interp(fine_grid, aoa, cd)

        # 1. Stall Characteristics & Linear Slope
        self.stall_aoa, self.cl_max, stall_idx = calculate_stall_characteristics(fine_grid, cl_interp)
        self.linear_lift_slope = calculate_linear_lift_slope(fine_grid, cl_interp)

        # 2. Near-Stall Inflection Boundary
        self.near_stall_aoa = calculate_near_stall_angle(
            fine_grid, cl_interp, self.linear_lift_slope, self.cl_max, stall_idx
        )

        # 3. 3D Aerodynamic Efficiency Envelope
        cl_3d_interp, cd_3d_interp, _ = self._apply_3d_correction(cl_interp, cd_interp)
        efficiency_3d = calculate_aerodynamic_efficiency(cl_3d_interp, cd_3d_interp)

        self.peak_efficiency_aoa, self.peak_efficiency_aoa_min, self.peak_efficiency_aoa_max = (
            calculate_peak_efficiency_envelope(fine_grid, efficiency_3d, PEAK_EFFICIENCY_BAND_FRACTION)
        )

        # Peak Point Validation via ML Model
        X_peak = np.array([[self.peak_efficiency_aoa]])
        cl_2d_at_peak = float(self.model_cl.predict(X_peak)[0])
        cd_2d_at_peak = float(self.model_cd.predict(X_peak)[0])
        cl_3d_at_peak, cd_3d_at_peak, _ = self._apply_3d_correction(cl_2d_at_peak, cd_2d_at_peak)
        self.peak_efficiency_value = round(float(calculate_aerodynamic_efficiency(cl_3d_at_peak, cd_3d_at_peak)), 2)

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
            ('scaler', StandardScaler()),
            ('poly', PolynomialFeatures(degree=4)),
            ('ridge', Ridge(alpha=0.001))
        ])
        
        self.model_cd = Pipeline([
            ('scaler', StandardScaler()),
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
        Predict 3D finite-wing aerodynamic efficiency (CL / CD) and aerodynamic forces
        using Prandtl Lifting-Line Theory (incorporating wingtip vortices and induced drag).
        """
        if not self.is_trained:
            raise RuntimeError("ML Surrogate Model is not trained yet.")
            
        X_input = np.array([[angle_of_attack]])
        cl_2d = float(self.model_cl.predict(X_input)[0])
        cd_2d = float(self.model_cd.predict(X_input)[0])
        cl_3d, cd_3d, cd_induced = self._apply_3d_correction(cl_2d, cd_2d)
        efficiency_3d = float(calculate_aerodynamic_efficiency(cl_3d, cd_3d))
        dynamic_pressure = calculate_dynamic_pressure(velocity_kmh, AIR_DENSITY)
        downforce_n, drag_n = calculate_aerodynamic_forces(cl_3d, cd_3d, dynamic_pressure, REFERENCE_WING_AREA)

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
            "cl": round(cl_3d, 4),
            "cd": round(cd_3d, 4),
            "cl_2d": round(cl_2d, 4),
            "cd_2d": round(cd_2d, 4),
            "cd_induced": round(cd_induced, 4),
            "efficiency": round(efficiency_3d, 2),
            "downforce_n": round(downforce_n, 2),
            "drag_n": round(drag_n, 2),
            "is_stalled": is_stalled,
            "status": aero_status,
        }

if __name__ == "__main__":
    model = AerodynamicSurrogateModel()
    res = model.predict(4.0, 120.0)
    print("Sample prediction at 4.0° AoA:", res)
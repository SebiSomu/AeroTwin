import os
import hashlib
import joblib
import pandas as pd
import numpy as np
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_squared_error

from physics_utils.constants import (
    AIR_DENSITY,
    DEFAULT_DATASET_PATH,
    DEFAULT_MODEL_CACHE_PATH,
    DEFAULT_CHORD_M,
    DEFAULT_VELOCITY_KMH,
    STALL_AOA_THRESHOLD_DEG,
    NEAR_STALL_THRESHOLD_DEG,
    PEAK_EFFICIENCY_AOA_MIN,
    PEAK_EFFICIENCY_AOA_MAX,
    PEAK_EFFICIENCY_BAND_FRACTION,
    get_aero_status,
)

from visual_model_config import (REFERENCE_WING_AREA)

from physics_utils.formulas import (
    calculate_dynamic_pressure,
    calculate_aerodynamic_forces,
    calculate_aerodynamic_efficiency,
    calculate_prandtl_3d_correction,
    calculate_linear_lift_slope,
    calculate_stall_characteristics,
    calculate_near_stall_angle,
    calculate_peak_efficiency_envelope,
    calculate_reynolds_number,
)

# Reference Reynolds number used for flow-regime derivation (stall, near-stall,
# peak-efficiency thresholds). Corresponds to ~200 km/h on a 0.30 m chord —
# a representative race-speed mid-range value.
REFERENCE_RE = 1_000_000


class AerodynamicSurrogateModel:
    """
    Machine Learning Surrogate Model for millisecond-level prediction of
    aerodynamic coefficients (CL, CD), efficiency (E = CL / CD), and forces.

    Input features: [angle_of_attack (deg), reynolds_number]
    The Reynolds number is computed from velocity and chord length by the
    caller (app.py), making the model valid for any airspeed / chord combination.
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
        # Re-dependent lookup tables (arrays parallel to re_table_values)
        self.re_table_values: list[float] = []
        self.re_table_stall: list[float] = []
        self.re_table_near_stall: list[float] = []
        self.re_table_peak_eff_aoa: list[float] = []
        self.re_table_peak_eff_min: list[float] = []
        self.re_table_peak_eff_max: list[float] = []

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
                schema_ok = (
                    cached.get("dataset_hash") == current_hash
                    and "stall_aoa" in cached
                    and cached.get("model_version") == "multi_re_v1"
                )
                if schema_ok:
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
                    self.re_table_values = cached.get("re_table_values", [])
                    self.re_table_stall = cached.get("re_table_stall", [])
                    self.re_table_near_stall = cached.get("re_table_near_stall", [])
                    self.re_table_peak_eff_aoa = cached.get("re_table_peak_eff_aoa", [])
                    self.re_table_peak_eff_min = cached.get("re_table_peak_eff_min", [])
                    self.re_table_peak_eff_max = cached.get("re_table_peak_eff_max", [])
                    self.is_trained = True
                    loaded_from_cache = True
                    print(f"[ML Model] Loaded cached pipeline from {self.cache_path}")
                    print(f"[ML Model] CL RMSE: {self.rmse_cl:.4f} | CD RMSE: {self.rmse_cd:.4f}")
                else:
                    print("[ML Model] Dataset, schema, or model version changed — retraining.")
            except Exception as e:
                print(f"[ML Model] Cache unreadable ({e}) — retraining.")

        if not loaded_from_cache:
            self.train_model()
            self._compute_flow_regimes()
            self._save_cache(current_hash)
        else:
            self._compute_flow_regimes()

    def _save_cache(self, dataset_hash: str):
        """Persist the fitted pipelines and learned regimes to disk."""
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        joblib.dump({
            "model_version": "multi_re_v1",
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
            "re_table_values": self.re_table_values,
            "re_table_stall": self.re_table_stall,
            "re_table_near_stall": self.re_table_near_stall,
            "re_table_peak_eff_aoa": self.re_table_peak_eff_aoa,
            "re_table_peak_eff_min": self.re_table_peak_eff_min,
            "re_table_peak_eff_max": self.re_table_peak_eff_max,
        }, self.cache_path)
        print(f"[ML Model] Cached trained pipeline to {self.cache_path}")

    def _apply_3d_correction(self, cl_2d, cd_2d):
        """Delegate Prandtl lifting-line finite-wing correction to physics module."""
        return calculate_prandtl_3d_correction(cl_2d, cd_2d, self.linear_lift_slope)

    def _compute_flow_regimes(self):
        """
        Derive flow regimes at EVERY Reynolds number in the dataset, then build
        interpolation lookup tables so predict() can return Re-accurate thresholds.

        For each Re slice:
          - Stall AoA / CL_max / linear slope: from raw section data (2D polar ground truth)
          - Near-stall onset: slope-fraction criterion on raw data
          - Peak efficiency band: from 3D ML surrogate curve at that Re
        """
        if self.model_cl is None or self.model_cd is None:
            raise RuntimeError("ML pipelines must be trained before flow regime computation.")

        df = pd.read_csv(self.dataset_path)
        dataset_re_values = sorted(df["reynolds_number"].unique().tolist())

        re_vals, stall_vals, near_stall_vals = [], [], []
        peak_aoa_vals, peak_min_vals, peak_max_vals = [], [], []

        for re_val in dataset_re_values:
            re_df = df[df["reynolds_number"] == re_val].sort_values("angle_of_attack")
            aoa_pts = re_df["angle_of_attack"].values
            cl_pts  = re_df["cl"].values

            aoa_lim_min = float(aoa_pts.min())
            aoa_lim_max = float(aoa_pts.max())
            fine_grid = np.linspace(aoa_lim_min, aoa_lim_max, 4001)

            cl_2d_raw = np.interp(fine_grid, aoa_pts, cl_pts)
            stall_aoa_re, cl_max_re, stall_idx_re = calculate_stall_characteristics(fine_grid, cl_2d_raw)
            slope_re = calculate_linear_lift_slope(fine_grid, cl_2d_raw)
            near_stall_re = calculate_near_stall_angle(
                fine_grid, cl_2d_raw, slope_re, cl_max_re, stall_idx_re
            )

            X_fine = np.column_stack([fine_grid, np.full_like(fine_grid, re_val)])
            cl_2d_ml = self.model_cl.predict(X_fine).astype(float)
            cd_2d_ml = self.model_cd.predict(X_fine).astype(float)
            cl_3d_ml, cd_3d_ml, _ = self._apply_3d_correction(cl_2d_ml, cd_2d_ml)
            efficiency_3d_ml = calculate_aerodynamic_efficiency(cl_3d_ml, cd_3d_ml)

            peak_aoa_re, peak_min_re, peak_max_re = calculate_peak_efficiency_envelope(
                fine_grid, efficiency_3d_ml, PEAK_EFFICIENCY_BAND_FRACTION
            )
            peak_idx = int(np.argmin(np.abs(fine_grid - peak_aoa_re)))
            peak_val_re = round(float(efficiency_3d_ml[peak_idx]), 2)

            re_vals.append(re_val)
            stall_vals.append(stall_aoa_re)
            near_stall_vals.append(near_stall_re)
            peak_aoa_vals.append(peak_aoa_re)
            peak_min_vals.append(peak_min_re)
            peak_max_vals.append(peak_max_re)

            print(
                f"[ML Model] Re={re_val/1e6:.2f}M: Stall={stall_aoa_re}° (CL_max={cl_max_re:.3f}) | "
                f"Near-Stall={near_stall_re}° | Peak Eff={peak_val_re:.1f} at {peak_aoa_re}° "
                f"(band {peak_min_re}°–{peak_max_re}°)"
            )

        self.re_table_values = re_vals
        self.re_table_stall = stall_vals
        self.re_table_near_stall = near_stall_vals
        self.re_table_peak_eff_aoa = peak_aoa_vals
        self.re_table_peak_eff_min = peak_min_vals
        self.re_table_peak_eff_max = peak_max_vals

        ref_idx = int(np.argmin(np.abs(np.array(re_vals) - REFERENCE_RE)))
        self.stall_aoa = stall_vals[ref_idx]
        self.near_stall_aoa = near_stall_vals[ref_idx]
        self.peak_efficiency_aoa = peak_aoa_vals[ref_idx]
        self.peak_efficiency_aoa_min = peak_min_vals[ref_idx]
        self.peak_efficiency_aoa_max = peak_max_vals[ref_idx]

        ref_df = df[df["reynolds_number"] == re_vals[ref_idx]].sort_values("angle_of_attack")
        aoa_pts = ref_df["angle_of_attack"].values
        cl_pts  = ref_df["cl"].values
        fine_grid = np.linspace(float(aoa_pts.min()), float(aoa_pts.max()), 4001)
        cl_2d_raw = np.interp(fine_grid, aoa_pts, cl_pts)
        self.linear_lift_slope = calculate_linear_lift_slope(fine_grid, cl_2d_raw)
        _, self.cl_max, _ = calculate_stall_characteristics(fine_grid, cl_2d_raw)

        ref_X = np.column_stack([fine_grid, np.full_like(fine_grid, re_vals[ref_idx])])
        cl_3d_ref, cd_3d_ref, _ = self._apply_3d_correction(
            self.model_cl.predict(ref_X).astype(float),
            self.model_cd.predict(ref_X).astype(float)
        )
        eff_ref = calculate_aerodynamic_efficiency(cl_3d_ref, cd_3d_ref)
        peak_idx_ref = int(np.argmax(eff_ref))
        self.peak_efficiency_value = round(float(eff_ref[peak_idx_ref]), 2)

    def train_model(self):
        """
        Train scikit-learn regressor pipeline on multi-Re NACA 0012 polar dataset.

        Input features: [angle_of_attack, reynolds_number]
        Polynomial degree=4 with interactions captures Re-dependent drag bucket,
        stall shift, and CL_max variation across the Reynolds number range.
        """
        df = pd.read_csv(self.dataset_path)

        X = df[["angle_of_attack", "reynolds_number"]].values
        y_cl = df["cl"].values
        y_cd = df["cd"].values

        self.model_cl = Pipeline([
            ("scaler", StandardScaler()),
            ("poly", PolynomialFeatures(degree=4, include_bias=False)),
            ("ridge", Ridge(alpha=0.01))
        ])

        self.model_cd = Pipeline([
            ("scaler", StandardScaler()),
            ("poly", PolynomialFeatures(degree=4, include_bias=False)),
            ("ridge", Ridge(alpha=0.01))
        ])

        self.model_cl.fit(X, y_cl)
        self.model_cd.fit(X, y_cd)

        pred_cl = self.model_cl.predict(X)
        pred_cd = self.model_cd.predict(X)

        self.rmse_cl = np.sqrt(mean_squared_error(y_cl, pred_cl))
        self.rmse_cd = np.sqrt(mean_squared_error(y_cd, pred_cd))
        self.is_trained = True

        print(f"[ML Model] Training complete. Features: [AoA, Re]")
        print(f"[ML Model] CL RMSE: {self.rmse_cl:.4f} | CD RMSE: {self.rmse_cd:.4f}")

    def predict(self, angle_of_attack: float, velocity_kmh: float = DEFAULT_VELOCITY_KMH,
                chord_m: float = DEFAULT_CHORD_M) -> dict:
        """
        Predict 3D finite-wing aerodynamic efficiency (CL / CD) and forces.

        Flow regime thresholds (stall, near-stall, peak-efficiency band) are
        interpolated from the precomputed Re lookup table so the status badge
        reflects the correct boundary-layer physics at the current airspeed.
        """
        if not self.is_trained:
            raise RuntimeError("ML Surrogate Model is not trained yet.")

        reynolds_number = calculate_reynolds_number(velocity_kmh, chord_m)

        X_input = np.array([[angle_of_attack, reynolds_number]])
        cl_2d = float(self.model_cl.predict(X_input)[0])
        cd_2d = float(self.model_cd.predict(X_input)[0])
        cl_3d, cd_3d, cd_induced = self._apply_3d_correction(cl_2d, cd_2d)
        efficiency_3d = float(calculate_aerodynamic_efficiency(cl_3d, cd_3d))
        dynamic_pressure = calculate_dynamic_pressure(velocity_kmh, AIR_DENSITY)
        downforce_n, drag_n = calculate_aerodynamic_forces(cl_3d, cd_3d, dynamic_pressure, REFERENCE_WING_AREA)

        # --- Interpolate Re-dependent thresholds ---
        if self.re_table_values:
            re_arr = np.array(self.re_table_values, dtype=float)
            re_clipped = float(np.clip(reynolds_number, re_arr.min(), re_arr.max()))
            stall_threshold = float(np.interp(re_clipped, re_arr, self.re_table_stall))
            near_stall_threshold = float(np.interp(re_clipped, re_arr, self.re_table_near_stall))
            peak_eff_min = float(np.interp(re_clipped, re_arr, self.re_table_peak_eff_min))
            peak_eff_max = float(np.interp(re_clipped, re_arr, self.re_table_peak_eff_max))
        else:
            stall_threshold = self.stall_aoa
            near_stall_threshold = self.near_stall_aoa
            peak_eff_min = self.peak_efficiency_aoa_min
            peak_eff_max = self.peak_efficiency_aoa_max

        is_stalled = angle_of_attack >= stall_threshold
        aero_status = get_aero_status(
            angle_of_attack,
            stall_threshold=stall_threshold,
            near_stall_threshold=near_stall_threshold,
            peak_min=peak_eff_min,
            peak_max=peak_eff_max,
        )

        return {
            "angle_of_attack": round(float(angle_of_attack), 2),
            "velocity_kmh": round(float(velocity_kmh), 1),
            "reynolds_number": round(float(reynolds_number), 0),
            "cl": round(cl_3d, 4),
            "cd": round(cd_3d, 4),
            "cl_2d": round(cl_2d, 4),
            "cd_2d": round(cd_2d, 4),
            "cd_induced": round(cd_induced, 4),
            "efficiency": round(efficiency_3d, 2),
            "downforce_n": round(downforce_n, 2),
            "drag_n": round(drag_n, 2),
            "stall_aoa": round(stall_threshold, 2),
            "near_stall_aoa": round(near_stall_threshold, 2),
            "peak_eff_min": round(peak_eff_min, 2),
            "peak_eff_max": round(peak_eff_max, 2),
            "is_stalled": is_stalled,
            "status": aero_status,
        }


if __name__ == "__main__":
    model = AerodynamicSurrogateModel()
    for v in [80.0, 150.0, 250.0]:
        res = model.predict(4.0, v)
        print(f"  AoA=4° @ {v} km/h  Re={res['reynolds_number']:,.0f}  "
              f"CL={res['cl']}  CD={res['cd']}  E={res['efficiency']}")
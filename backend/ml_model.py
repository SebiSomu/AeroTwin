import os
import pandas as pd
import numpy as np
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_squared_error

AIR_DENSITY = 1.225
REFERENCE_WING_AREA = 0.45

class AerodynamicSurrogateModel:
    """
    Machine Learning Surrogate Model for millisecond-level prediction of
    aerodynamic coefficients (CL, CD), efficiency (E = CL / CD), and forces.
    """
    def __init__(self, dataset_path: str = None):
        if dataset_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            dataset_path = os.path.join(base_dir, "naca0012_polars.csv")
            
        self.dataset_path = dataset_path
        self.model_cl = None
        self.model_cd = None
        self.rmse_cl = 0.0
        self.rmse_cd = 0.0
        self.is_trained = False
        
        self.train_model()

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

    def predict(self, angle_of_attack: float, velocity_kmh: float = 120.0) -> dict:
        """
        Predict aerodynamic efficiency (CL / CD) and aerodynamic forces.
        
        Parameters:
            angle_of_attack (float): AoA in degrees (-5.0 to +20.0)
            velocity_kmh (float): Vehicle speed in km/h (default 120 km/h)
            
        Returns:
            dict containing cl, cd, efficiency, downforce_n, drag_n, is_stalled
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
        
        is_stalled = angle_of_attack >= 15.0
        
        return {
            "angle_of_attack": round(float(angle_of_attack), 2),
            "velocity_kmh": round(float(velocity_kmh), 1),
            "cl": round(cl, 4),
            "cd": round(cd, 4),
            "efficiency": round(efficiency, 2),
            "downforce_n": round(downforce_n, 2),
            "drag_n": round(drag_n, 2),
            "is_stalled": is_stalled
        }

if __name__ == "__main__":
    model = AerodynamicSurrogateModel()
    res = model.predict(4.0, 120.0)
    print("Sample prediction at 4.0° AoA:", res)

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import numpy as np
from physics_utils.constants import (
    AIR_DENSITY,
    KINEMATIC_VISCOSITY,
    DEFAULT_CHORD_M,
    PEAK_EFFICIENCY_BAND_FRACTION,
    NEAR_STALL_SLOPE_FRACTION,
    NEAR_STALL_CL_FRACTION
)
from visual_model_config import (
    REFERENCE_WING_AREA,
    WING_ASPECT_RATIO,
    WING_OSWALD_EFFICIENCY
)

# Physical Formulas for Aerodynamic Calculations

# Dynamic Pressure & Dimensional Forces

def calculate_dynamic_pressure(velocity_kmh: float, air_density: float = AIR_DENSITY) -> float:
    """
    Calculate dynamic pressure q = 0.5 * rho * v^2 in Pascals (N/m^2).
    """
    v_ms = velocity_kmh / 3.6
    return 0.5 * air_density * (v_ms ** 2)


def calculate_reynolds_number(velocity_kmh: float, chord_m: float = DEFAULT_CHORD_M, kinematic_viscosity: float = KINEMATIC_VISCOSITY) -> float:
    """
    Calculate the chord-based Reynolds number Re = V * c / nu.

    Re governs the boundary-layer transition regime:
      Re < ~300k  : laminar separation dominant (low speed / short chord)
      Re ~ 500k   : transitional (typical road car at 100 km/h)
      Re ~ 1M     : mostly turbulent (race car at 200 km/h)
      Re > 2M     : fully turbulent (high-speed racing)
    """
    v_ms = velocity_kmh / 3.6
    return v_ms * chord_m / kinematic_viscosity


def calculate_aerodynamic_forces(cl: float, cd: float, dynamic_pressure: float, wing_area: float = REFERENCE_WING_AREA) -> tuple[float, float]:
    """
    Calculate dimensional Downforce (FL) and Drag (FD) in Newtons.
    FL = q * S * CL
    FD = q * S * CD
    """
    downforce_n = dynamic_pressure * wing_area * cl
    drag_n = dynamic_pressure * wing_area * cd
    return downforce_n, drag_n


def calculate_aerodynamic_efficiency(cl, cd, min_cd: float = 0.005):
    """
    Calculate aerodynamic efficiency ratio E = CL / CD. Works on scalars or numpy arrays.
    """
    cd_safe = np.maximum(cd, min_cd) if isinstance(cd, np.ndarray) else max(cd, min_cd)
    return cl / cd_safe


# Prandtl 3D Finite-Wing Lifting-Line Corrections

def calculate_prandtl_3d_correction(cl_2d, cd_2d, linear_lift_slope_deg: float, aspect_ratio: float = WING_ASPECT_RATIO, oswald_efficiency: float = WING_OSWALD_EFFICIENCY) -> tuple:
    """
    Apply Prandtl lifting-line finite-wing correction to 2D section coefficients.
    Works on scalars or numpy arrays.

    CL_3D = CL_2D / (1 + a0 / (pi * AR * e))
    CD_induced = CL_3D^2 / (pi * AR * e)
    CD_3D = CD_2D + CD_induced
    """
    a0_rad = linear_lift_slope_deg * (180.0 / np.pi)
    pi_AR_e = np.pi * aspect_ratio * oswald_efficiency
    slope_factor = 1.0 / (1.0 + a0_rad / pi_AR_e)

    cl_3d = cl_2d * slope_factor
    cd_induced = (cl_3d ** 2) / pi_AR_e
    cd_3d = cd_2d + cd_induced
    return cl_3d, cd_3d, cd_induced


# Polar Curve Calculus & Regime Identification

def calculate_linear_lift_slope(fine_grid: np.ndarray, cl_interp: np.ndarray) -> float:
    """
    Compute baseline 2D linear lift slope dCL/dAoA around 0° incidence (between 0° and 5°).
    """
    zero_idx = np.argmin(np.abs(fine_grid - 0.0))
    idx_5deg = np.argmin(np.abs(fine_grid - 5.0))
    if idx_5deg != zero_idx:
        slope = (cl_interp[idx_5deg] - cl_interp[zero_idx]) / (fine_grid[idx_5deg] - fine_grid[zero_idx])
    else:
        slope = 0.105
    return round(float(slope), 4)


def calculate_stall_characteristics(fine_grid: np.ndarray, cl_interp: np.ndarray) -> tuple[float, float, int]:
    """
    Find critical stall angle (argmax CL) and maximum lift coefficient CL_max.
    """
    stall_idx = int(np.argmax(cl_interp))
    stall_aoa = round(float(fine_grid[stall_idx]), 2)
    cl_max = round(float(cl_interp[stall_idx]), 3)
    return stall_aoa, cl_max, stall_idx


def calculate_near_stall_angle(fine_grid: np.ndarray,cl_interp: np.ndarray,linear_slope: float,cl_max: float,stall_idx: int,slope_fraction: float = NEAR_STALL_SLOPE_FRACTION,cl_fraction: float = NEAR_STALL_CL_FRACTION) -> float:
    """
    Identify near-stall inflection boundary where dCL/dAoA drops below
    slope_fraction of linear slope, or CL reaches cl_fraction of CL_max.
    """
    zero_idx = np.argmin(np.abs(fine_grid - 0.0))
    dcl_da = np.gradient(cl_interp, fine_grid)
    near_stall_idx = stall_idx
    for i in range(zero_idx, stall_idx):
        if dcl_da[i] < slope_fraction * linear_slope or cl_interp[i] >= cl_fraction * cl_max:
            near_stall_idx = i
            break
    return round(float(fine_grid[near_stall_idx]), 2)


def calculate_peak_efficiency_envelope(fine_grid: np.ndarray, efficiency_3d: np.ndarray, band_fraction: float = PEAK_EFFICIENCY_BAND_FRACTION) -> tuple[float, float, float]:
    """
    Derive the peak aerodynamic efficiency operating point and the envelope
    where efficiency stays within band_fraction (e.g. 95%) of the maximum.
    """
    peak_idx = int(np.argmax(efficiency_3d))
    peak_value = float(efficiency_3d[peak_idx])
    threshold = peak_value * band_fraction

    left_idx = peak_idx
    while left_idx > 0 and efficiency_3d[left_idx - 1] >= threshold:
        left_idx -= 1
    right_idx = peak_idx
    while right_idx < len(fine_grid) - 1 and efficiency_3d[right_idx + 1] >= threshold:
        right_idx += 1

    peak_aoa = round(float(fine_grid[peak_idx]), 2)
    peak_aoa_min = round(float(fine_grid[left_idx]), 2)
    peak_aoa_max = round(float(fine_grid[right_idx]), 2)
    return peak_aoa, peak_aoa_min, peak_aoa_max

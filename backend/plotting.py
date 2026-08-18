import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from physics_utils.constants import (
    DEFAULT_DATASET_PATH,
    DEFAULT_VELOCITY_KMH,
    MODEL_CACHE_DIR,
)
from physics_utils.formulas import calculate_aerodynamic_efficiency

def generate_or_load_aero_chart(model, cache_dir: str = None) -> str:
    """
    Generate or load a cached 4-panel aerodynamic performance & ML surrogate validation graphic.
    If the file exists, it is loaded from cache (1-time creation).
    Returns the absolute path to the generated/cached PNG file.
    """
    if cache_dir is None:
        cache_dir = MODEL_CACHE_DIR

    os.makedirs(cache_dir, exist_ok=True)
    chart_path = os.path.join(cache_dir, "aero_performance_polar.png")

    if os.path.exists(chart_path):
        print(f"[Plotting] Cached aerodynamic graphic loaded from {chart_path}")
        return chart_path

    print("[Plotting] Graphic missing from cache — generating single-pass Matplotlib visualization...")

    df = pd.read_csv(model.dataset_path)
    aoa_data = df['angle_of_attack'].values
    cl_data = df['cl'].values
    cd_data = df['cd'].values
    aoa_grid = np.linspace(-5.0, 20.0, 500)

    cl_2d_pred = []
    cd_2d_pred = []
    cl_3d_pred = []
    cd_3d_pred = []
    cd_ind_pred = []
    eff_3d_pred = []
    downforce_pred = []
    drag_pred = []

    for a in aoa_grid:
        res = model.predict(a, DEFAULT_VELOCITY_KMH)
        cl_2d_pred.append(res['cl_2d'])
        cd_2d_pred.append(res['cd_2d'])
        cl_3d_pred.append(res['cl'])
        cd_3d_pred.append(res['cd'])
        cd_ind_pred.append(res['cd_induced'])
        eff_3d_pred.append(res['efficiency'])
        downforce_pred.append(res['downforce_n'])
        drag_pred.append(res['drag_n'])

    cl_2d_pred = np.array(cl_2d_pred)
    cd_2d_pred = np.array(cd_2d_pred)
    cl_3d_pred = np.array(cl_3d_pred)
    cd_3d_pred = np.array(cd_3d_pred)
    cd_ind_pred = np.array(cd_ind_pred)
    eff_3d_pred = np.array(eff_3d_pred)
    downforce_pred = np.array(downforce_pred)
    drag_pred = np.array(drag_pred)

    bg_color = "#0B0F14"
    card_bg = "#121820"
    text_color = "#E0E6ED"
    muted_color = "#8A9BA8"
    cyan_color = "#00E5FF"
    red_color = "#D9584F"
    gold_color = "#C9A15F"
    green_color = "#00FF66"
    blue_color = "#3388FF"

    plt.rcParams.update({
        "figure.facecolor": bg_color,
        "axes.facecolor": card_bg,
        "axes.edgecolor": "#1F2B37",
        "axes.labelcolor": text_color,
        "xtick.color": muted_color,
        "ytick.color": muted_color,
        "text.color": text_color,
        "grid.color": "#1C2633",
        "grid.linestyle": "--",
        "grid.alpha": 0.6,
        "font.family": "sans-serif",
        "font.size": 9,
    })

    fig, axes = plt.subplots(2, 2, figsize=(14, 10), dpi=200)
    fig.suptitle("AEROTWIN TELEMETRY · GT3 REAR WING AERODYNAMIC POLARS & 3D CORRECTION", 
                 fontsize=14, fontweight="bold", color=cyan_color, y=0.98)

    # Subplot 1: Lift Polar (CL vs AoA)
    ax1 = axes[0, 0]
    ax1.plot(aoa_data, cl_data, 'o', color=muted_color, alpha=0.7, markersize=4, label="NACA 0012 Raw 2D Data")
    ax1.plot(aoa_grid, cl_2d_pred, '-', color=blue_color, linewidth=1.8, label="2D Section ML Model")
    ax1.plot(aoa_grid, cl_3d_pred, '-', color=cyan_color, linewidth=2.2, label="3D Finite-Wing (Prandtl)")
    ax1.axvline(x=model.stall_aoa, color=red_color, linestyle=":", linewidth=1.5, label=f"Stall Threshold ({model.stall_aoa}°)")
    ax1.set_title("Lift Coefficient ($C_L$) vs Angle of Attack", fontweight="bold", pad=8)
    ax1.set_xlabel("Angle of Attack α (°)")
    ax1.set_ylabel("Lift Coefficient $C_L$")
    ax1.grid(True)
    ax1.legend(loc="upper left", framealpha=0.8, facecolor=card_bg, edgecolor="#1F2B37", fontsize=8)

    # Subplot 2: Drag Breakdown (CD vs AoA)
    ax2 = axes[0, 1]
    ax2.plot(aoa_grid, cd_2d_pred, '--', color=muted_color, linewidth=1.6, label="2D Profile Drag ($C_{d0}$)")
    ax2.plot(aoa_grid, cd_ind_pred, ':', color=gold_color, linewidth=1.6, label="3D Induced Drag ($C_{Di}$)")
    ax2.plot(aoa_grid, cd_3d_pred, '-', color=red_color, linewidth=2.2, label="Total 3D Drag ($C_{D,3D}$)")
    ax2.set_title("Drag Breakdown & Induced Penalty ($C_D$ vs AoA)", fontweight="bold", pad=8)
    ax2.set_xlabel("Angle of Attack α (°)")
    ax2.set_ylabel("Drag Coefficient $C_D$")
    ax2.grid(True)
    ax2.legend(loc="upper left", framealpha=0.8, facecolor=card_bg, edgecolor="#1F2B37", fontsize=8)

    # Subplot 3: Aerodynamic Efficiency (L/D)
    ax3 = axes[1, 0]
    eff_2d = calculate_aerodynamic_efficiency(cl_2d_pred, cd_2d_pred)
    ax3.plot(aoa_grid, eff_2d, '--', color=muted_color, linewidth=1.5, label="2D Section L/D")
    ax3.plot(aoa_grid, eff_3d_pred, '-', color=green_color, linewidth=2.2, label="3D Finite-Wing Efficiency (L/D)")
    ax3.axvspan(model.peak_efficiency_aoa_min, model.peak_efficiency_aoa_max, 
                color=gold_color, alpha=0.15, label=f"Peak Window ({model.peak_efficiency_aoa_min}°–{model.peak_efficiency_aoa_max}°)")
    if model.peak_efficiency_aoa is not None:
        ax3.plot(model.peak_efficiency_aoa, model.peak_efficiency_value, '*', 
                 color=gold_color, markersize=12, label=f"Peak L/D={model.peak_efficiency_value:.1f} at {model.peak_efficiency_aoa}°")
    
    ax3.set_title("Aerodynamic Efficiency Ratio ($E = C_L / C_D$)", fontweight="bold", pad=8)
    ax3.set_xlabel("Angle of Attack α (°)")
    ax3.set_ylabel("Efficiency ($L / D$)")
    ax3.grid(True)
    ax3.legend(loc="upper right", framealpha=0.8, facecolor=card_bg, edgecolor="#1F2B37", fontsize=8)

    # Subplot 4: Dimensional Forces at 120 km/h (Downforce & Drag)
    ax4 = axes[1, 1]
    ax4.plot(aoa_grid, downforce_pred, '-', color=cyan_color, linewidth=2.2, label=f"Downforce $F_L$ (N)")
    ax4.plot(aoa_grid, drag_pred, '-', color=red_color, linewidth=2.0, label=f"Drag $F_D$ (N)")
    ax4.fill_between(aoa_grid, 0, downforce_pred, color=cyan_color, alpha=0.08)
    ax4.fill_between(aoa_grid, 0, drag_pred, color=red_color, alpha=0.08)
    ax4.axvline(x=model.stall_aoa, color=red_color, linestyle=":", linewidth=1.5)

    ax4.set_title(f"Dynamic Aerodynamic Forces at {DEFAULT_VELOCITY_KMH:.0f} km/h", fontweight="bold", pad=8)
    ax4.set_xlabel("Angle of Attack α (°)")
    ax4.set_ylabel("Force (Newtons)")
    ax4.grid(True)
    ax4.legend(loc="upper left", framealpha=0.8, facecolor=card_bg, edgecolor="#1F2B37", fontsize=8)

    plt.tight_layout(rect=[0, 0.02, 1, 0.96])
    fig.savefig(chart_path, dpi=200, bbox_inches="tight")
    plt.close(fig)

    print(f"[Plotting] Generated single-pass aerodynamic graphic saved to {chart_path}")
    return chart_path

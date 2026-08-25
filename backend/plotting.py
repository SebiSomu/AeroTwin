import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from physics_utils.constants import (
    DEFAULT_DATASET_PATH,
    DEFAULT_VELOCITY_KMH,
    DEFAULT_CHORD_M,
    KINEMATIC_VISCOSITY,
    MODEL_CACHE_DIR,
)
from physics_utils.formulas import calculate_aerodynamic_efficiency, calculate_reynolds_number

# Reynolds numbers and their approximate speeds for a 0.30 m chord (v = Re * nu / c)
# Displayed on the chart for user context
_NU = KINEMATIC_VISCOSITY
_C  = DEFAULT_CHORD_M
CHART_RE_VALUES = [200_000, 500_000, 1_000_000, 2_000_000]
CHART_RE_COLORS = ["#5599FF", "#00E5FF", "#00FF66", "#C9A15F"]
CHART_RE_LABELS = [
    f"Re=200k  (~{round(200_000*_NU/_C*3.6):,} km/h)",
    f"Re=500k  (~{round(500_000*_NU/_C*3.6):,} km/h)",
    f"Re=1M    (~{round(1_000_000*_NU/_C*3.6):,} km/h)",
    f"Re=2M    (~{round(2_000_000*_NU/_C*3.6):,} km/h)",
]


def generate_or_load_aero_chart(model, cache_dir: str = None) -> str:
    """
    Generate or load a cached 4-panel aerodynamic performance & ML surrogate
    validation graphic showing multi-Reynolds-number polars.
    Returns the absolute path to the generated/cached PNG file.
    """
    if cache_dir is None:
        cache_dir = MODEL_CACHE_DIR

    os.makedirs(cache_dir, exist_ok=True)
    chart_path = os.path.join(cache_dir, "aero_performance_polar.png")

    if os.path.exists(chart_path):
        print(f"[Plotting] Cached aerodynamic graphic loaded from {chart_path}")
        return chart_path

    print("[Plotting] Graphic missing from cache — generating multi-Re Matplotlib visualization...")

    df = pd.read_csv(model.dataset_path)
    aoa_grid = np.linspace(-5.0, 20.0, 500)

    # Pre-compute predictions for each Re on the fine grid
    re_results = {}
    for re_val in CHART_RE_VALUES:
        v_kmh = re_val * KINEMATIC_VISCOSITY / DEFAULT_CHORD_M * 3.6  # back-compute km/h
        cl_2d_list, cd_2d_list = [], []
        cl_3d_list, cd_3d_list = [], []
        cd_ind_list, eff_3d_list = [], []
        for a in aoa_grid:
            res = model.predict(a, v_kmh)
            cl_2d_list.append(res["cl_2d"])
            cd_2d_list.append(res["cd_2d"])
            cl_3d_list.append(res["cl"])
            cd_3d_list.append(res["cd"])
            cd_ind_list.append(res["cd_induced"])
            eff_3d_list.append(res["efficiency"])
        re_results[re_val] = {
            "cl_2d": np.array(cl_2d_list),
            "cd_2d": np.array(cd_2d_list),
            "cl_3d": np.array(cl_3d_list),
            "cd_3d": np.array(cd_3d_list),
            "cd_ind": np.array(cd_ind_list),
            "eff_3d": np.array(eff_3d_list),
        }

    # --- Theme ---
    bg_color   = "#0B0F14"
    card_bg    = "#121820"
    text_color = "#E0E6ED"
    muted_color = "#8A9BA8"
    cyan_color = "#00E5FF"
    red_color  = "#D9584F"
    gold_color = "#C9A15F"

    plt.rcParams.update({
        "figure.facecolor": bg_color,
        "axes.facecolor":   card_bg,
        "axes.edgecolor":   "#1F2B37",
        "axes.labelcolor":  text_color,
        "xtick.color":      muted_color,
        "ytick.color":      muted_color,
        "text.color":       text_color,
        "grid.color":       "#1C2633",
        "grid.linestyle":   "--",
        "grid.alpha":       0.6,
        "font.family":      "sans-serif",
        "font.size":        9,
    })

    fig, axes = plt.subplots(2, 2, figsize=(15, 11), dpi=200)
    fig.suptitle(
        "AEROTWIN TELEMETRY · NACA 0012 MULTI-REYNOLDS POLARS & 3D CORRECTION",
        fontsize=13, fontweight="bold", color=cyan_color, y=0.98
    )

    # ── Subplot 1: Lift Polar (CL vs AoA) ──────────────────────────────────
    ax1 = axes[0, 0]
    # Raw data scatter (all Re together as reference points)
    for re_val, color, label in zip(CHART_RE_VALUES, CHART_RE_COLORS, CHART_RE_LABELS):
        re_df = df[df["reynolds_number"] == re_val].sort_values("angle_of_attack")
        ax1.plot(re_df["angle_of_attack"], re_df["cl"],
                 "o", color=color, alpha=0.45, markersize=3)
        ax1.plot(aoa_grid, re_results[re_val]["cl_3d"],
                 "-", color=color, linewidth=1.8, label=label)

    ax1.axvline(x=model.stall_aoa, color=red_color, linestyle=":",
                linewidth=1.5, label=f"Stall @ Re=1M ({model.stall_aoa}°)")
    ax1.set_title("Lift Coefficient ($C_L$) vs AoA — Multi-Re 3D Wing", fontweight="bold", pad=8)
    ax1.set_xlabel("Angle of Attack α (°)")
    ax1.set_ylabel("Lift Coefficient $C_L$ (3D finite-wing)")
    ax1.grid(True)
    ax1.legend(loc="upper left", framealpha=0.8, facecolor=card_bg,
               edgecolor="#1F2B37", fontsize=7.5)

    # ── Subplot 2: Drag Polar (CD vs AoA) ──────────────────────────────────
    ax2 = axes[0, 1]
    for re_val, color, label in zip(CHART_RE_VALUES, CHART_RE_COLORS, CHART_RE_LABELS):
        re_df = df[df["reynolds_number"] == re_val].sort_values("angle_of_attack")
        ax2.plot(re_df["angle_of_attack"], re_df["cd"],
                 "o", color=color, alpha=0.45, markersize=3)
        ax2.plot(aoa_grid, re_results[re_val]["cd_3d"],
                 "-", color=color, linewidth=1.8, label=label)

    ax2.set_title("Drag Coefficient ($C_D$) vs AoA — Re Effect on Profile Drag", fontweight="bold", pad=8)
    ax2.set_xlabel("Angle of Attack α (°)")
    ax2.set_ylabel("Total Drag Coefficient $C_D$ (2D + induced)")
    ax2.grid(True)
    ax2.legend(loc="upper left", framealpha=0.8, facecolor=card_bg,
               edgecolor="#1F2B37", fontsize=7.5)

    # ── Subplot 3: Aerodynamic Efficiency (L/D) ────────────────────────────
    ax3 = axes[1, 0]
    for re_val, color, label in zip(CHART_RE_VALUES, CHART_RE_COLORS, CHART_RE_LABELS):
        ax3.plot(aoa_grid, re_results[re_val]["eff_3d"],
                 "-", color=color, linewidth=1.8, label=label)

    ax3.axvspan(model.peak_efficiency_aoa_min, model.peak_efficiency_aoa_max,
                color=gold_color, alpha=0.12,
                label=f"Peak Window @ Re=1M ({model.peak_efficiency_aoa_min}°–{model.peak_efficiency_aoa_max}°)")
    if model.peak_efficiency_aoa is not None:
        ax3.plot(model.peak_efficiency_aoa, model.peak_efficiency_value,
                 "*", color=gold_color, markersize=12,
                 label=f"Peak L/D={model.peak_efficiency_value:.1f} at {model.peak_efficiency_aoa}°")

    ax3.set_title("Aerodynamic Efficiency (L/D) — Re Sensitivity", fontweight="bold", pad=8)
    ax3.set_xlabel("Angle of Attack α (°)")
    ax3.set_ylabel("Efficiency ($L / D$)")
    ax3.grid(True)
    ax3.legend(loc="upper right", framealpha=0.8, facecolor=card_bg,
               edgecolor="#1F2B37", fontsize=7.5)

    # ── Subplot 4: CD vs CL (Drag Polar / Bucket diagram) ──────────────────
    ax4 = axes[1, 1]
    for re_val, color, label in zip(CHART_RE_VALUES, CHART_RE_COLORS, CHART_RE_LABELS):
        ax4.plot(re_results[re_val]["cd_3d"], re_results[re_val]["cl_3d"],
                 "-", color=color, linewidth=1.8, label=label)

    ax4.set_title("Drag Polar Diagram ($C_L$ vs $C_D$) — Re Effect on Drag Bucket",
                  fontweight="bold", pad=8)
    ax4.set_xlabel("Drag Coefficient $C_D$")
    ax4.set_ylabel("Lift Coefficient $C_L$")
    ax4.grid(True)
    ax4.legend(loc="upper left", framealpha=0.8, facecolor=card_bg,
               edgecolor="#1F2B37", fontsize=7.5)

    plt.tight_layout(rect=[0, 0.02, 1, 0.96])
    fig.savefig(chart_path, dpi=200, bbox_inches="tight")
    plt.close(fig)

    print(f"[Plotting] Generated multi-Re aerodynamic graphic saved to {chart_path}")
    return chart_path

import pandas as pd
import numpy as np

df = pd.read_csv('datasets/naca0012_multi_re_polars.csv')
print('=== Stall AoA (CL peak) per Reynolds number ===')
for re in sorted(df.reynolds_number.unique()):
    sub = df[df.reynolds_number == re].sort_values('angle_of_attack')
    stall_idx = sub['cl'].idxmax()
    aoa_stall = sub.loc[stall_idx, 'angle_of_attack']
    cl_max_val = sub.loc[stall_idx, 'cl']
    peak_eff_aoa = (sub['cl'] / sub['cd']).idxmax()
    peak_eff_val = (sub['cl'] / sub['cd']).max()
    peak_eff_aoa_val = sub.loc[peak_eff_aoa, 'angle_of_attack']
    print(f"Re={re/1e6:.1f}M: stall={aoa_stall}deg  CL_max={cl_max_val:.3f}  peak_eff_aoa={peak_eff_aoa_val}deg  peak_L/D={peak_eff_val:.1f}")

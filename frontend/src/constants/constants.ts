import * as THREE from "three";

// Constants used for airfoil simulation and visualization

export const MIN_AOA = -5;  // Minimum angle of attack in degrees, used to define the lower limit for aerodynamic calculations.
export const MAX_AOA = 20;  // Maximum angle of attack in degrees, used to define the upper limit for aerodynamic calculations.
export const STEP_AOA = 0.1;  // Step size for angle of attack in degrees, used to incrementally calculate aerodynamic properties across a range of angles.
export const DEFAULT_AOA = 4;
export const DEFAULT_PIVOT = { x: 150, y: 100 };

export const MIN_VELOCITY = 50;     // km/h
export const MAX_VELOCITY = 350;    // km/h
export const STEP_VELOCITY = 1;     // km/h
export const DEFAULT_VELOCITY = 120;// km/h
export const DEFAULT_CHORD_M = 0.30;// m
export const KINEMATIC_VISCOSITY = 1.46e-5; // m^2/s

const CDN_BASE = (import.meta.env.VITE_CLOUDFRONT_URL || "").replace(/\/$/, "");
export const MODEL_PATH = CDN_BASE
  ? `${CDN_BASE}/models/porsche_gt3rs_spoiler.glb`
  : "/models/porsche_gt3rs_spoiler.glb";
export const MODEL_SCALE_FACTOR = 0.85;

export const STREAMLINE_COUNT = 80;  // Number of streamlines to be generated in the flow visualization, affecting the density and clarity of the flow representation.
export const POINTS_PER_LINE = 40;  // Number of points per streamline, determining the resolution of each streamline and the smoothness of the flow visualization.
export const TOTAL_STREAMLINE_VERTICES = STREAMLINE_COUNT * (POINTS_PER_LINE - 1) * 2; // Total number of vertices for all streamlines, calculated based on the number of streamlines and points per line, used for buffer allocation in rendering.
export const PARTICLE_COUNT = 500;  // Number of particles to be used in the particle system for flow visualization, affecting the visual density and dynamics of the flow representation.

export const BASE_FLOW_VELOCITY = 0.65;  // Base flow velocity in the simulation, used to define the initial speed of the airflow in the aerodynamic model.
export const STREAMLINE_START_Z = -0.55;  // Starting Z position for streamlines in the flow visualization, defining where the streamlines originate in the 3D space of the simulation.
export const STREAMLINE_END_Z = 0.55;  // Ending Z position for streamlines in the flow visualization, defining where the streamlines terminate in the 3D space of the simulation.

export const CAD_INITIAL_PITCH_OFFSET_DEG = 12.5;  // Initial pitch offset in degrees for the CAD model, used to set the initial orientation of the model in the simulation environment.

export const CFD_COLOR_BLUE = new THREE.Color("#0033FF");
export const CFD_COLOR_CYAN = new THREE.Color("#00E5FF");
export const CFD_COLOR_GREEN = new THREE.Color("#00FF66");
export const CFD_COLOR_YELLOW = new THREE.Color("#FFDD00");
export const CFD_COLOR_RED = new THREE.Color("#FF1100");

export const STATUS_STALLED = {
  label: "STALLED",
  sub: "Boundary layer separated",
  color: "#D9584F",
  glow: "rgba(217,88,79,0.35)",
};

export const STATUS_NEAR_STALL = {
  label: "NEAR STALL",
  sub: "Approaching critical AoA",
  color: "#E0982E",
  glow: "rgba(224,152,46,0.3)",
};

export const STATUS_PEAK_EFFICIENCY = {
  label: "PEAK EFFICIENCY",
  sub: "Optimal CL / CD ratio",
  color: "#C9A15F",
  glow: "rgba(201,161,95,0.35)",
};

export const STATUS_LINEAR_REGION = {
  label: "LINEAR REGION",
  sub: "Attached flow",
  color: "#7FA6B3",
  glow: "rgba(127,166,179,0.25)",
};

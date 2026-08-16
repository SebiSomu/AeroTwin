import * as THREE from "three";

export const MIN_AOA = -5;
export const MAX_AOA = 20;
export const STEP_AOA = 0.5;
export const DEFAULT_AOA = 4;
export const DEFAULT_PIVOT = { x: 150, y: 100 };

export const MODEL_PATH = "/models/porsche_gt3rs_spoiler.glb";
export const MODEL_SCALE_FACTOR = 0.85;

export const STREAMLINE_COUNT = 80;
export const POINTS_PER_LINE = 40;
export const TOTAL_STREAMLINE_VERTICES =
  STREAMLINE_COUNT * (POINTS_PER_LINE - 1) * 2;
export const PARTICLE_COUNT = 500;

export const BASE_FLOW_VELOCITY = 0.65;
export const STREAMLINE_START_Z = -0.55;
export const STREAMLINE_END_Z = 0.55;

export const CAD_INITIAL_PITCH_OFFSET_DEG = 12.5;

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

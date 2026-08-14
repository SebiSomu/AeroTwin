<script lang="ts">
  import AeroBackground from "./components/AeroBackground.svelte";
  import CornerDecorations from "./components/CornerDecorations.svelte";
  import TitleBlock from "./components/TitleBlock.svelte";
  import AirfoilDisplay from "./components/AirfoilDisplay.svelte";
  import AngleSlider from "./components/AngleSlider.svelte";
  import BottomLabel from "./components/BottomLabel.svelte";
  import SpoilerViewer from "./components/SpoilerViewer.svelte";
  import type { Status, Pivot } from "./types/types";

  let angle = $state<number>(4);
  const min: number = -5;
  const max: number = 20;
  const step: number = 0.5;

  let percent = $derived<number>(((angle - min) / (max - min)) * 100);

  let status = $derived<Status>((() => {
    if (angle >= 15) {
      return {
        label: "STALLED",
        sub: "Boundary layer separated",
        color: "#D9584F",
        glow: "rgba(217,88,79,0.35)",
      };
    }
    if (angle >= 12) {
      return {
        label: "NEAR STALL",
        sub: "Approaching critical AoA",
        color: "#E0982E",
        glow: "rgba(224,152,46,0.3)",
      };
    }
    if (angle >= 3 && angle <= 5) {
      return {
        label: "PEAK EFFICIENCY",
        sub: "Optimal CL / CD ratio",
        color: "#C9A15F",
        glow: "rgba(201,161,95,0.35)",
      };
    }
    return {
      label: "LINEAR REGION",
      sub: "Attached flow",
      color: "#7FA6B3",
      glow: "rgba(127,166,179,0.25)",
    };
  })());

  const pivot: Pivot = { x: 150, y: 100 };
</script>

<div class="relative flex min-h-screen w-full flex-col items-center justify-center overflow-hidden bg-aero-bg font-mono text-aero-text">
  <AeroBackground />
  <CornerDecorations />

  <TitleBlock
    primary="AeroTwin&nbsp;Cloud"
    secondary="Surrogate CFD · v1.0.0"
    position="left"
  />

  <TitleBlock
    primary="NACA&nbsp;0012 · GT3&nbsp;Rear&nbsp;Wing"
    secondary="Profile Rev. 01"
    position="right"
  />

  <!-- ── Main layout ───────────────────────────────────────────────── -->
  <div class="z-2 flex flex-col items-center gap-3 px-4">

    <!-- Row 1: 3D viewer centred; angle panel absolutely floated right -->
    <div class="relative flex justify-center">
      <SpoilerViewer />

      <!-- Angle panel — absolute so it never pushes the viewer off-centre -->
      <div class="
        absolute -right-44 top-1/2 -translate-y-1/2
        flex w-40 flex-col items-start gap-1
        border-l border-aero-blue-25 pl-4
        max-[820px]:static max-[820px]:translate-y-0
        max-[820px]:border-l-0 max-[820px]:border-t max-[820px]:border-aero-blue-25
        max-[820px]:pt-3 max-[820px]:items-center max-[820px]:w-full
      ">
        <!-- Label -->
        <p class="font-mono text-[9px] uppercase tracking-[0.2em] text-aero-muted-4 mb-0.5">
          Angle of Attack
        </p>

        <!-- Big number -->
        <p
          class="font-display font-semibold leading-none tabular-nums transition-colors duration-250 ease-out"
          style="font-size: clamp(40px, 5vw, 60px); color: {status.color};"
        >
          {angle.toFixed(1)}°
        </p>

        <!-- Status badge -->
        <div
          class="mt-0.5 flex items-center gap-1.5 font-mono text-[9px] uppercase tracking-aero-md transition-colors duration-250 ease-out"
          style="color: {status.color};"
        >
          <span
            class="block h-[5px] w-[5px] shrink-0 rounded-full"
            style="background: {status.color}; box-shadow: 0 0 8px {status.glow};"
          ></span>
          {status.label}
        </div>

        <!-- Sub-label -->
        <p
          class="font-mono text-[8px] uppercase tracking-[0.12em] opacity-60 transition-colors duration-250 ease-out"
          style="color: {status.color};"
        >
          {status.sub}
        </p>

        <!-- Mini airfoil — scaled down, clipped -->
        <div class="mt-2 overflow-hidden" style="width:186px; height:124px; transform:scale(0.62); transform-origin:left top;">
          <AirfoilDisplay {angle} {status} {pivot} />
        </div>
      </div>
    </div>

    <!-- Row 2: slider, aligned to viewer width -->
    <div class="w-[min(520px,82vw)] px-0.5">
      <AngleSlider bind:angle {min} {max} {step} {percent} {status} />
    </div>
  </div>

  <BottomLabel text="AoA Control · Module 01" />
</div>

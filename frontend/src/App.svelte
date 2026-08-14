<script lang="ts">
  import AeroBackground from "./components/AeroBackground.svelte";
  import CornerDecorations from "./components/CornerDecorations.svelte";
  import TitleBlock from "./components/TitleBlock.svelte";
  import AirfoilDisplay from "./components/AirfoilDisplay.svelte";
  import AngleSlider from "./components/AngleSlider.svelte";
  import BottomLabel from "./components/BottomLabel.svelte";
  import SpoilerViewer from "./components/SpoilerViewer.svelte";
  import type { Status, Pivot } from "./types/types";
  import {
    MIN_AOA,
    MAX_AOA,
    STEP_AOA,
    DEFAULT_AOA,
    DEFAULT_PIVOT,
    STATUS_STALLED,
    STATUS_NEAR_STALL,
    STATUS_PEAK_EFFICIENCY,
    STATUS_LINEAR_REGION,
  } from "./constants/constants";

  let angle = $state<number>(DEFAULT_AOA);
  let velocityKmh = $state<number>(120);
  
  // ML Prediction State
  let mlEfficiency = $state<number | null>(null);
  let mlCl = $state<number | null>(null);
  let mlCd = $state<number | null>(null);
  let mlDownforceN = $state<number | null>(null);
  let mlDragN = $state<number | null>(null);
  let isApiOnline = $state<boolean>(false);

  const min: number = MIN_AOA;
  const max: number = MAX_AOA;
  const step: number = STEP_AOA;

  let percent = $derived<number>(((angle - min) / (max - min)) * 100);

  let status = $derived<Status>((() => {
    if (angle >= 15) return STATUS_STALLED;
    if (angle >= 12) return STATUS_NEAR_STALL;
    if (angle >= 3 && angle <= 5) return STATUS_PEAK_EFFICIENCY;
    return STATUS_LINEAR_REGION;
  })());

  const pivot: Pivot = DEFAULT_PIVOT;

  // Reactively fetch ML efficiency prediction whenever angle changes
  $effect(() => {
    const currentAoA = angle;
    const currentVel = velocityKmh;
    
    fetch("http://localhost:5000/api/v1/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        angle_of_attack: currentAoA,
        velocity_kmh: currentVel,
      }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (data && typeof data.efficiency === "number") {
          mlEfficiency = data.efficiency;
          mlCl = data.cl;
          mlCd = data.cd;
          mlDownforceN = data.downforce_n;
          mlDragN = data.drag_n;
          isApiOnline = true;
        }
      })
      .catch((_err) => {
        isApiOnline = false;
      });
  });
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
      <SpoilerViewer {angle} />

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

        <!-- ML Efficiency & Telemetry Box -->
        <div class="mt-2.5 flex flex-col gap-1 border-t border-aero-blue-25 pt-2 w-full">
          <div class="flex items-center justify-between text-[9px] uppercase tracking-[0.15em] text-aero-muted-4">
            <span>Efficiency (L/D)</span>
            <span class="font-bold text-aero-text">{mlEfficiency !== null ? mlEfficiency.toFixed(1) : '30.4'}</span>
          </div>
          <div class="flex items-center justify-between text-[9px] uppercase tracking-[0.15em] text-aero-muted-4">
            <span>Downforce</span>
            <span class="font-bold text-aero-text">{mlDownforceN !== null ? mlDownforceN.toFixed(0) + ' N' : '164 N'}</span>
          </div>
          <div class="mt-1 flex items-center gap-1.5 text-[8px] uppercase tracking-[0.14em]">
            <span class="h-1.5 w-1.5 rounded-full {isApiOnline ? 'bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.6)]' : 'bg-red-400'}"></span>
            <span class="{isApiOnline ? 'text-emerald-700 font-semibold' : 'text-aero-muted-4'}">{isApiOnline ? 'SERVER RUNNING' : 'SERVER OFFLINE'}</span>
          </div>
        </div>

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

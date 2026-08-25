<script lang="ts">
  import AeroBackground from "./components/AeroBackground.svelte";
  import CornerDecorations from "./components/CornerDecorations.svelte";
  import TitleBlock from "./components/TitleBlock.svelte";
  import AirfoilDisplay from "./components/AirfoilDisplay.svelte";
  import AngleSlider from "./components/AngleSlider.svelte";
  import VelocitySlider from "./components/VelocitySlider.svelte";

  import SpoilerViewer from "./components/SpoilerViewer.svelte";
  import type { Status, Pivot } from "./types/types";
  import {
    MIN_AOA,
    MAX_AOA,
    STEP_AOA,
    DEFAULT_AOA,
    DEFAULT_PIVOT,
    MIN_VELOCITY,
    MAX_VELOCITY,
    STEP_VELOCITY,
    DEFAULT_VELOCITY,
  } from "./constants/constants";
  import { onMount } from "svelte";

  let angle = $state<number>(DEFAULT_AOA);
  let velocityKmh = $state<number>(DEFAULT_VELOCITY);

  // ML Prediction State
  let mlEfficiency = $state<number | null>(null);
  let mlCl = $state<number | null>(null);
  let mlCd = $state<number | null>(null);
  let mlDownforceN = $state<number | null>(null);
  let mlDragN = $state<number | null>(null);
  let mlRe = $state<number | null>(null);
  let isApiOnline = $state<boolean>(false);
  let showForceVectors = $state<boolean>(false);
  let showChartModal = $state<boolean>(false);

  // Status from server (label, sub, color, glow)
  const FALLBACK_STATUS: Status = {
    label: "—",
    sub: "Awaiting server",
    color: "#7FA6B3",
    glow: "rgba(127,166,179,0.25)",
  };
  let mlStatus = $state<Status>(FALLBACK_STATUS);

  const min: number = MIN_AOA;
  const max: number = MAX_AOA;
  const step: number = STEP_AOA;

  let percent = $derived<number>(((angle - min) / (max - min)) * 100);

  const pivot: Pivot = DEFAULT_PIVOT;

  // Health check
  onMount(() => {
    const checkHealth = () => {
      fetch("/api/v1/health")
        .then((res) => {
          if (!res.ok) throw new Error("Server error");
          return res.json();
        })
        .then((data) => {
          if (data && data.status === "server running") {
            isApiOnline = true;
          } else {
            setOffline();
          }
        })
        .catch(() => {
          setOffline();
        });
    };

    function setOffline() {
      isApiOnline = false;
      mlEfficiency = null;
      mlCl = null;
      mlCd = null;
      mlDownforceN = null;
      mlDragN = null;
      mlRe = null;
    }

    checkHealth();
    const interval = setInterval(checkHealth, 3000);

    return () => clearInterval(interval);
  });

  // Reactively fetch ML efficiency prediction whenever angle or velocity changes
  $effect(() => {
    const currentAoA = angle;
    const currentVel = velocityKmh;

    fetch("/api/v1/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        angle_of_attack: currentAoA,
        velocity_kmh: currentVel,
      }),
    })
      .then((res) => {
        if (!res.ok) {
          return res.text().then((text) => {
            console.error(`[PREDICT] HTTP ${res.status}: ${text}`);
            throw new Error(`Predict failed: ${res.status}`);
          });
        }
        return res.json();
      })
      .then((data) => {
        if (data && typeof data.efficiency === "number") {
          mlEfficiency = data.efficiency;
          mlCl = data.cl;
          mlCd = data.cd;
          mlDownforceN = data.downforce_n;
          mlDragN = data.drag_n;
          mlRe = data.reynolds_number ?? Math.round((currentVel / 3.6) * 0.30 / 1.46e-5);
          isApiOnline = true;
          // Use server-provided status if available, else derive from AoA
          if (data.status && data.status.label) {
            mlStatus = data.status as Status;
          } else {
            // Fallback: derive status client-side while server restarts
            const aoa = data.angle_of_attack ?? angle;
            if (aoa >= 14.5) mlStatus = { label: "STALLED", sub: "Boundary layer separated", color: "#D9584F", glow: "rgba(217,88,79,0.35)" };
            else if (aoa >= 12) mlStatus = { label: "NEAR STALL", sub: "Approaching critical AoA", color: "#E0982E", glow: "rgba(224,152,46,0.3)" };
            else if (aoa >= 3 && aoa <= 5.5) mlStatus = { label: "PEAK EFFICIENCY", sub: "Optimal CL / CD ratio", color: "#C9A15F", glow: "rgba(201,161,95,0.35)" };
            else mlStatus = { label: "LINEAR REGION", sub: "Attached flow", color: "#7FA6B3", glow: "rgba(127,166,179,0.25)" };
          }
        } else {
          console.warn("[PREDICT] Unexpected response shape:", data);
        }
      })
      .catch((err) => {
        console.error("[PREDICT] Fetch failed:", err.message);
        isApiOnline = false;
        mlEfficiency = null;
        mlCl = null;
        mlCd = null;
        mlDownforceN = null;
        mlDragN = null;
        mlRe = null;
        mlStatus = FALLBACK_STATUS;
      });
  });
</script>

<div
  class="relative flex min-h-screen w-full flex-col items-center justify-center overflow-hidden bg-aero-bg font-mono text-aero-text py-4"
>
  <AeroBackground />
  <CornerDecorations />

  <TitleBlock
    primary="AeroTwin&nbsp;Cloud"
    secondary="Multi-Re Surrogate CFD · v2.0"
    position="left"
  />

  <TitleBlock
    primary="NACA&nbsp;0012 · Aerodynamic&nbsp;Polar"
    secondary="Re = 200k – 2M · Multi-Param"
    position="right"
  />

  <!-- ── Main layout ───────────────────────────────────────────────── -->
  <div class="z-2 flex flex-col items-center gap-2 px-4 max-w-6xl w-full">
    <!-- Row 1: 3D viewer centred; angle panel absolutely floated right -->
    <div class="relative flex justify-center">
      <SpoilerViewer
        {angle}
        {showForceVectors}
        downforceN={mlDownforceN}
        dragN={mlDragN}
      />

      <!-- Angle panel — absolute so it never pushes the viewer off-centre -->
      <div
        class="
        absolute -right-44 top-16
        flex w-40 flex-col items-start gap-1
        border-l border-aero-blue-25 pl-4
        max-[820px]:static
        max-[820px]:border-l-0 max-[820px]:border-t max-[820px]:border-aero-blue-25
        max-[820px]:pt-3 max-[820px]:items-center max-[820px]:w-full
      "
      >
        <!-- Label -->
        <p
          class="font-mono text-[9px] uppercase tracking-[0.2em] text-aero-muted-4 mb-0.5"
        >
          Angle of Attack
        </p>

        <!-- Big number -->
        <p
          class="font-display font-semibold leading-none tabular-nums transition-colors duration-250 ease-out"
          style="font-size: clamp(38px, 4.5vw, 56px); color: {mlStatus.color};"
        >
          {angle.toFixed(1)}°
        </p>

        <!-- Status badge -->
        <div
          class="mt-0.5 flex items-center gap-1.5 font-mono text-[9px] uppercase tracking-aero-md transition-colors duration-250 ease-out"
          style="color: {mlStatus.color};"
        >
          <span
            class="block h-[5px] w-[5px] shrink-0 rounded-full"
            style="background: {mlStatus.color}; box-shadow: 0 0 8px {mlStatus.glow};"
          ></span>
          {mlStatus.label}
        </div>

        <!-- Sub-label -->
        <p
          class="font-mono text-[8px] uppercase tracking-[0.12em] opacity-60 transition-colors duration-250 ease-out"
          style="color: {mlStatus.color};"
        >
          {mlStatus.sub}
        </p>

        <!-- ML Efficiency & Telemetry Box -->
        <div
          class="mt-2 flex flex-col gap-1 border-t border-aero-blue-25 pt-2 w-full"
        >
          <div
            class="flex items-center justify-between text-[9px] uppercase tracking-[0.15em] text-aero-muted-4"
          >
            <span>Reynolds (Re)</span>
            <span class="font-bold text-[#00E5FF]"
              >{mlRe !== null ? (mlRe >= 1000000 ? (mlRe / 1000000).toFixed(2) + 'M' : Math.round(mlRe / 1000) + 'k') : "685k"}</span
            >
          </div>
          <div
            class="flex items-center justify-between text-[9px] uppercase tracking-[0.15em] text-aero-muted-4"
          >
            <span>Airspeed</span>
            <span class="font-bold text-aero-text">{velocityKmh.toFixed(0)} km/h</span>
          </div>
          <div
            class="flex items-center justify-between text-[9px] uppercase tracking-[0.15em] text-aero-muted-4"
          >
            <span>Efficiency (L/D)</span>
            <span class="font-bold text-aero-text"
              >{mlEfficiency !== null ? mlEfficiency.toFixed(1) : "—"}</span
            >
          </div>
          <div
            class="flex items-center justify-between text-[9px] uppercase tracking-[0.15em] text-aero-muted-4"
          >
            <span>Downforce / Drag</span>
            <span class="font-bold text-aero-text"
              >{mlDownforceN !== null ? mlDownforceN.toFixed(0) : "—"}N / {mlDragN !== null ? mlDragN.toFixed(0) : "—"}N</span
            >
          </div>
          <div
            class="flex items-center justify-between text-[9px] uppercase tracking-[0.15em] text-aero-muted-4"
          >
            <span>CL / CD Coeff</span>
            <span class="font-bold text-aero-text"
              >{mlCl !== null ? mlCl.toFixed(2) : "—"} / {mlCd !== null ? mlCd.toFixed(3) : "—"}</span
            >
          </div>
          <div
            class="mt-1 flex items-center gap-1.5 text-[8px] uppercase tracking-[0.14em]"
          >
            <span
              class="h-1.5 w-1.5 rounded-full {isApiOnline
                ? 'bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.6)]'
                : 'bg-red-400'}"
            ></span>
            <span
              class={isApiOnline
                ? "text-emerald-700 font-semibold"
                : "text-aero-muted-4"}
              >{isApiOnline ? "SURROGATE ONLINE" : "SERVER OFFLINE"}</span
            >
          </div>

          <!-- Optional 3D Aero Force Vectors Toggle -->
          <div
            class="mt-1 flex flex-col gap-1 w-full border-t border-aero-blue-25 pt-1"
          >
            <label
              class="flex items-center gap-1.5 cursor-pointer select-none text-[8px] uppercase tracking-[0.14em] text-aero-muted-4 hover:text-aero-text transition-colors"
            >
              <input
                type="checkbox"
                bind:checked={showForceVectors}
                class="accent-[#00E5FF] cursor-pointer h-3 w-3 rounded border border-aero-blue-25"
              />
              <span class="font-medium">3D Force Vectors</span>
            </label>

            {#if showForceVectors}
              <div
                class="mt-0.5 flex flex-col gap-1 pl-4 font-mono text-[7.5px] uppercase tracking-[0.12em] text-aero-muted-4 transition-opacity duration-200"
              >
                <div class="flex items-center gap-1.5">
                  <span
                    class="h-1.5 w-1.5 rounded-full bg-[#00E5FF] shadow-[0_0_4px_#00E5FF]"
                  ></span>
                  <span class="text-aero-text">Downforce (FL)</span>
                </div>
                <div class="flex items-center gap-1.5">
                  <span
                    class="h-1.5 w-1.5 rounded-full bg-[#D9584F] shadow-[0_0_4px_#D9584F]"
                  ></span>
                  <span class="text-aero-text">Drag (FD)</span>
                </div>
                <div class="flex items-center gap-1.5">
                  <span
                    class="h-1.5 w-1.5 rounded-full bg-[#00FF66] shadow-[0_0_4px_#00FF66]"
                  ></span>
                  <span class="text-aero-text">Net Resultant</span>
                </div>
              </div>
            {/if}
          </div>

          <!-- Matplotlib Aerodynamic Diagnostic Plot Trigger Button -->
          <button
            onclick={() => (showChartModal = true)}
            class="mt-1.5 flex items-center justify-center gap-1.5 w-full py-1 px-2 border border-[#00E5FF]/40 rounded bg-[#00E5FF]/10 text-[8px] font-mono uppercase tracking-[0.14em] text-[#00E5FF] hover:bg-[#00E5FF]/20 hover:border-[#00E5FF] transition-all cursor-pointer select-none"
          >
            <span>Multi-Re Polar Telemetry</span>
          </button>
        </div>

        <!-- Mini airfoil — scaled down, clipped -->
        <div
          class="mt-1 overflow-hidden"
          style="width:186px; height:124px; transform:scale(0.62); transform-origin:left top;"
        >
          <AirfoilDisplay {angle} status={mlStatus} {pivot} />
        </div>
      </div>
    </div>

    <!-- Controls Row: Dual Sliders for AoA & Velocity/Re -->
    <div class="flex flex-col gap-2 w-[min(520px,82vw)] px-0.5 mt-3">
      <!-- AoA Slider -->
      <div>
        <div class="flex items-center justify-between text-[9px] font-mono uppercase tracking-[0.15em] text-aero-muted-4 mb-1">
          <span>Angle of Attack (α)</span>
          <span class="font-bold" style="color: {mlStatus.color};">{angle.toFixed(1)}°</span>
        </div>
        <AngleSlider bind:angle {min} {max} {step} {percent} status={mlStatus} />
      </div>

      <!-- Velocity / Reynolds Slider -->
      <div class="mt-1">
        <div class="flex items-center justify-between text-[9px] font-mono uppercase tracking-[0.15em] text-aero-muted-4 mb-1">
          <span>Airspeed &amp; Reynolds (V / Re)</span>
          <span class="font-bold text-[#00E5FF]">{velocityKmh.toFixed(0)} km/h <span class="text-aero-muted-4 text-[8px]">({mlRe ? (mlRe >= 1000000 ? (mlRe / 1000000).toFixed(2) + 'M' : Math.round(mlRe / 1000) + 'k') : '—'})</span></span>
        </div>
        <VelocitySlider bind:velocity={velocityKmh} />
      </div>
    </div>
  </div>



  <!-- Matplotlib Chart Modal Overlay -->
  {#if showChartModal}
    <div
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4"
    >
      <div
        class="relative flex flex-col items-center max-w-5xl w-full max-h-[90vh] bg-[#0B0F14] border border-[#1F2B37] rounded-lg p-4 shadow-2xl overflow-auto"
      >
        <div class="flex items-center justify-between w-full mb-3 border-b border-[#1F2B37] pb-2">
          <div class="flex items-center gap-2">
            <span class="h-2 w-2 rounded-full bg-[#00E5FF] shadow-[0_0_8px_#00E5FF]"></span>
            <h3 class="font-mono text-xs uppercase tracking-widest text-[#00E5FF] font-bold">
              Multi-Reynolds Polar Telemetry &amp; Surrogate Validation
            </h3>
          </div>
          <button
            onclick={() => (showChartModal = false)}
            class="px-2 py-0.5 rounded border border-red-500/40 bg-red-500/10 text-red-400 hover:bg-red-500/30 text-xs font-mono tracking-wider cursor-pointer transition-colors"
          >
            x
          </button>
        </div>

        <div class="relative w-full flex justify-center bg-[#0B0F14] rounded overflow-hidden">
          <img
            src="/api/v1/chart?t={Date.now()}"
            alt="Matplotlib Aerodynamic Telemetry Chart"
            class="max-w-full h-auto object-contain rounded border border-[#1F2B37]"
          />
        </div>
      </div>
    </div>
  {/if}
</div>

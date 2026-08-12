<script lang="ts">
  import AeroBackground from "./components/AeroBackground.svelte";
  import CornerDecorations from "./components/CornerDecorations.svelte";
  import TitleBlock from "./components/TitleBlock.svelte";
  import AirfoilDisplay from "./components/AirfoilDisplay.svelte";
  import AngleGauge from "./components/AngleGauge.svelte";
  import AngleSlider from "./components/AngleSlider.svelte";
  import BottomLabel from "./components/BottomLabel.svelte";
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
    primary="AeroTwin\u00A0Cloud"
    secondary="Surrogate CFD · v1.0.0"
    position="left"
  />

  <TitleBlock
    primary="NACA\u00A00012 · GT3\u00A0Rear\u00A0Wing"
    secondary="Profile Rev. 01"
    position="right"
  />

  <div class="z-2 flex flex-col items-center gap-2">
    <AirfoilDisplay {angle} {status} {pivot} />
    <AngleGauge {angle} {status} />
    <AngleSlider bind:angle {min} {max} {step} {percent} {status} />
  </div>

  <BottomLabel text="AoA Control · Module 01" />
</div>

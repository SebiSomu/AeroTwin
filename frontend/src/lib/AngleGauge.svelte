<script lang="ts">
  import type { Status } from "./types";

  export let angle: number = 0;
  export let status: Status = { label: "", sub: "", color: "#7FA6B3", glow: "rgba(127,166,179,0.25)" };
</script>

<div style="font-size: 11px; letter-spacing: 0.28em; text-transform: uppercase; color: rgba(199,210,218,0.45);">
  Angle of Attack
</div>
<div
  class="value-readout"
  style="font-family: 'Space Grotesk', sans-serif; font-weight: 600; font-size: clamp(56px, 9vw, 88px); line-height: 1; color: {status.color}; transition: color 0.25s ease; font-variant-numeric: tabular-nums;"
>
  {angle.toFixed(1)}°
</div>
<div style="font-size: 11px; letter-spacing: 0.18em; text-transform: uppercase; color: {status.color}; margin-top: 2px; margin-bottom: 28px; transition: color 0.25s ease; display: flex; align-items: center; gap: 8px;">
  <span style="width: 5px; height: 5px; border-radius: 50%; background: {status.color}; box-shadow: 0 0 8px {status.glow};"></span>
  {status.label}
  <span style="color: rgba(199,210,218,0.35);">· {status.sub}</span>
</div>

<style>
  @media (max-width: 560px) {
    .value-readout {
      font-size: clamp(48px, 16vw, 72px) !important;
    }
  }
</style>

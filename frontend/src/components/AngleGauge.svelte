<script lang="ts">
  import type { Status } from "../types/types";

  export let angle: number = 0;
  export let status: Status = { label: "", sub: "", color: "#7FA6B3", glow: "rgba(127,166,179,0.25)" };
</script>

<div class="text-[11px] uppercase tracking-aero-lg text-aero-muted-45">
  Angle of Attack
</div>
<div
  class="value-readout font-display font-semibold leading-none tabular-nums transition-colors duration-250 ease-out"
  style="font-size: clamp(56px, 9vw, 88px); color: {status.color};"
>
  {angle.toFixed(1)}°
</div>
<div
  class="mt-[2px] mb-7 flex items-center gap-2 text-[11px] uppercase tracking-aero-md transition-colors duration-250 ease-out"
  style="color: {status.color};"
>
  <span
    class="h-[5px] w-[5px] rounded-full"
    style="background: {status.color}; box-shadow: 0 0 8px {status.glow};"
  ></span>
  {status.label}
  <span class="text-aero-muted-35">· {status.sub}</span>
</div>

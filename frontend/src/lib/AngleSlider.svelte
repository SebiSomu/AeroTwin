<script lang="ts">
  import type { Status } from "./types";

  export let angle: number = 4;
  export let min: number = -5;
  export let max: number = 20;
  export let step: number = 0.5;
  export let percent: number = 0;
  export let status: Status = { label: "", sub: "", color: "#7FA6B3", glow: "rgba(127,166,179,0.25)" };

  const majorTicks: readonly number[] = [-5, 0, 5, 10, 15, 20];

  const minorTicks: number[] = [];
  for (let t: number = min; t <= max; t += 1) {
    minorTicks.push(t);
  }
</script>

<div class="relative h-11 w-[min(520px,82vw)]">
  {#each minorTicks as t}
    {@const isMajor = majorTicks.includes(t)}
    {@const left = ((t - min) / (max - min)) * 100}
    <div
      class="absolute top-[14px] w-px"
      style="left: {left}%; height: {isMajor ? 10 : 5}px; background: {isMajor ? 'rgba(127,166,179,0.5)' : 'rgba(127,166,179,0.22)'}; transform: translateX(-0.5px);"
    ></div>
  {/each}

  {#each majorTicks as t}
    {@const left = ((t - min) / (max - min)) * 100}
    <div
      class="absolute top-[26px] -translate-x-1/2 text-[10px] text-aero-muted-4 tracking-aero-xs"
      style="left: {left}%;"
    >
      {t}°
    </div>
  {/each}

  <div class="absolute left-0 right-0 top-2 h-px bg-aero-blue-25"></div>
  <div
    class="fill-bar absolute left-0 top-2 h-px"
    style="width: {percent}%; background: {status.color};"
  ></div>

  <input
    class="aero-slider"
    type="range"
    {min}
    {max}
    {step}
    bind:value={angle}
    aria-label="Angle of attack, degrees"
    style="top: -6px; height: 20px; --thumb-color: {status.color}; --thumb-glow: {status.glow};"
  />
</div>

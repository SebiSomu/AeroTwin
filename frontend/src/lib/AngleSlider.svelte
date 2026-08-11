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

<div style="position: relative; width: min(520px, 82vw); height: 44px;">
  {#each minorTicks as t}
    {@const isMajor = majorTicks.includes(t)}
    {@const left = ((t - min) / (max - min)) * 100}
    <div
      style="position: absolute; left: {left}%; top: 14px; width: 1px; height: {isMajor ? 10 : 5}px; background: {isMajor ? 'rgba(127,166,179,0.5)' : 'rgba(127,166,179,0.22)'}; transform: translateX(-0.5px);"
    ></div>
  {/each}

  {#each majorTicks as t}
    {@const left = ((t - min) / (max - min)) * 100}
    <div style="position: absolute; left: {left}%; top: 26px; transform: translateX(-50%); font-size: 10px; color: rgba(199,210,218,0.4); letter-spacing: 0.02em;">
      {t}°
    </div>
  {/each}

  <div style="position: absolute; left: 0; right: 0; top: 8px; height: 1px; background: rgba(127,166,179,0.25);"></div>
  <div
    class="fill-bar"
    style="position: absolute; left: 0; top: 8px; height: 1px; width: {percent}%; background: {status.color}; transition: width 0.05s linear, background 0.25s ease;"
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

<style>
  .aero-slider {
    -webkit-appearance: none;
    appearance: none;
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    background: transparent;
    margin: 0;
    cursor: pointer;
  }
  .aero-slider:focus-visible {
    outline: 2px solid #C9A15F;
    outline-offset: 6px;
    border-radius: 3px;
  }
  .aero-slider::-webkit-slider-runnable-track {
    background: transparent;
    height: 100%;
  }
  .aero-slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 15px;
    height: 15px;
    margin-top: 0;
    background: var(--thumb-color, #C9A15F);
    border: 2px solid #0A0D11;
    box-shadow:
      0 0 0 3px rgba(255, 255, 255, 0.07),
      0 0 14px var(--thumb-glow, transparent);
    transform: translateY(3px) rotate(45deg);
    transition:
      background 0.2s ease,
      box-shadow 0.2s ease;
  }
  .aero-slider::-moz-range-track {
    background: transparent;
    height: 100%;
  }
  .aero-slider::-moz-range-thumb {
    width: 15px;
    height: 15px;
    border-radius: 0;
    background: var(--thumb-color, #C9A15F);
    border: 2px solid #0A0D11;
    box-shadow:
      0 0 0 3px rgba(255, 255, 255, 0.07),
      0 0 14px var(--thumb-glow, transparent);
    transform: rotate(45deg);
    transition:
      background 0.2s ease,
      box-shadow 0.2s ease;
  }
  @media (prefers-reduced-motion: reduce) {
    .fill-bar,
    .aero-slider::-webkit-slider-thumb,
    .aero-slider::-moz-range-thumb {
      transition: none !important;
    }
  }
</style>

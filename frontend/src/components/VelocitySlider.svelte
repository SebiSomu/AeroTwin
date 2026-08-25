<script lang="ts">
  import { MIN_VELOCITY, MAX_VELOCITY, STEP_VELOCITY } from "../constants/constants";

  interface Props {
    velocity: number;
    min?: number;
    max?: number;
    step?: number;
  }

  let {
    velocity = $bindable(120),
    min = MIN_VELOCITY,
    max = MAX_VELOCITY,
    step = STEP_VELOCITY,
  }: Props = $props();

  let percent = $derived(((velocity - min) / (max - min)) * 100);

  const majorTicks: readonly number[] = [50, 100, 150, 200, 250, 300, 350];

  let minorTicks = $derived.by(() => {
    const ticks: number[] = [];
    for (let t = min; t <= max; t += 25) {
      ticks.push(t);
    }
    return ticks;
  });
</script>

<div class="relative h-11 w-[min(520px,82vw)]">
  {#each minorTicks as t}
    {@const isMajor = majorTicks.includes(t)}
    {@const left = ((t - min) / (max - min)) * 100}
    <div
      class="absolute top-[14px] w-px"
      style="left: {left}%; height: {isMajor ? 10 : 5}px; background: {isMajor ? 'rgba(0,229,255,0.45)' : 'rgba(0,229,255,0.18)'}; transform: translateX(-0.5px);"
    ></div>
  {/each}

  {#each majorTicks as t}
    {@const left = ((t - min) / (max - min)) * 100}
    <div
      class="absolute top-[26px] -translate-x-1/2 text-[9.5px] font-mono text-aero-muted-4 tracking-aero-xs"
      style="left: {left}%;"
    >
      {t}
    </div>
  {/each}

  <div class="absolute left-0 right-0 top-2 h-px bg-aero-blue-25"></div>
  <div
    class="fill-bar absolute left-0 top-2 h-px"
    style="width: {percent}%; background: #00E5FF;"
  ></div>

  <input
    class="aero-slider"
    type="range"
    {min}
    {max}
    {step}
    bind:value={velocity}
    aria-label="Velocity, km/h"
    style="top: -6px; height: 20px; --thumb-color: #00E5FF; --thumb-glow: rgba(0,229,255,0.4);"
  />
</div>

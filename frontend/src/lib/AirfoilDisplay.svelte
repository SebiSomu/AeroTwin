<script lang="ts">
  import type { Status, Pivot } from "./types";

  export let angle: number = 0;
  export let status: Status = { label: "", sub: "", color: "#7FA6B3", glow: "rgba(127,166,179,0.25)" };
  export let pivot: Pivot = { x: 150, y: 100 };
</script>

<svg width="300" height="200" viewBox="0 0 300 200" style="overflow: visible; margin-bottom: 4px;">
  <line
    x1="10"
    y1={pivot.y}
    x2="280"
    y2={pivot.y}
    stroke="rgba(127,166,179,0.4)"
    stroke-width="1"
    stroke-dasharray="2 5"
  />
  <path
    d="M 280,{pivot.y} L 271,{pivot.y - 4} L 271,{pivot.y + 4} Z"
    fill="rgba(127,166,179,0.55)"
  />
  <text
    x="16"
    y={pivot.y - 10}
    font-size="9"
    letter-spacing="0.1em"
    fill="rgba(127,166,179,0.55)"
    font-family="'IBM Plex Mono', monospace"
  >
    V∞
  </text>
  <g
    class="wing-group"
    transform="translate({pivot.x} {pivot.y}) rotate({angle})"
  >
    <line
      x1="-40"
      y1="0"
      x2="100"
      y2="0"
      stroke="rgba(199,210,218,0.25)"
      stroke-width="1"
      stroke-dasharray="1 4"
    />
    <path
      d="M -40,0 C -35,-14 -10,-20 20,-14 C 55,-9 85,-4 100,0 C 85,4 40,10 -5,10 C -25,10 -38,6 -40,0 Z"
      fill="none"
      stroke={status.color}
      stroke-width="1.6"
      style="transition: stroke 0.25s ease;"
    />
  </g>
  <circle cx={pivot.x} cy={pivot.y} r="2.5" fill="#C7D2DA" />
</svg>

<style>
  .wing-group {
    transition: transform 0.12s ease-out;
  }
  @media (prefers-reduced-motion: reduce) {
    .wing-group {
      transition: none !important;
    }
  }
</style>

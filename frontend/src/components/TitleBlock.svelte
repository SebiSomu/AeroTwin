<script lang="ts">
  export let primary: string = "";
  export let secondary: string = "";
  export let position: "left" | "right" = "left";
</script>

<div
  class="title-block absolute top-10 text-[11px] uppercase leading-relaxed tracking-aero-md text-aero-muted-55 {position === 'left' ? 'left-10 text-left' : 'right-10 text-right'}"
>
  {primary}
  <br />
  <span class="text-aero-muted-3">{secondary}</span>
</div>

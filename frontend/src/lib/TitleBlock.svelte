<script lang="ts">
  export let primary: string = "";
  export let secondary: string = "";
  export let position: "left" | "right" = "left";
</script>

<div
  class="title-block"
  style="position: absolute; top: 40px; {position === 'left' ? 'left: 40px;' : 'right: 40px; text-align: right;'} font-size: 11px; letter-spacing: 0.18em; text-transform: uppercase; color: rgba(199,210,218,0.55); line-height: 1.6;"
>
  {primary}
  <br />
  <span style="color: rgba(199,210,218,0.3);">{secondary}</span>
</div>

<style>
  @media (max-width: 560px) {
    .title-block {
      font-size: 9px !important;
      letter-spacing: 0.12em !important;
    }
  }
</style>

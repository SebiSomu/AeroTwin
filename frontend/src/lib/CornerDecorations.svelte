<script lang="ts"></script>

<div class="corner tl"></div>
<div class="corner tr"></div>
<div class="corner bl"></div>
<div class="corner br"></div>

<style>
  .corner {
    position: absolute;
    width: 22px;
    height: 22px;
    border: 1px solid rgba(127, 166, 179, 0.35);
  }
  .corner.tl { top: 22px; left: 22px; border-right: none; border-bottom: none; }
  .corner.tr { top: 22px; right: 22px; border-left: none; border-bottom: none; }
  .corner.bl { bottom: 22px; left: 22px; border-right: none; border-top: none; }
  .corner.br { bottom: 22px; right: 22px; border-left: none; border-top: none; }
</style>

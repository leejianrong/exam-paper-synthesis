<script lang="ts">
  // A locked question's badge beside its number (EXA-161): an icon, a tooltip, and the word
  // for screen readers, so the state is never only a picture.
  import Icon from '../Icon.svelte'
</script>

<span class="lockbadge" title="Locked: kept when you regenerate"
  ><Icon name="lock" size={12} /><span class="sr-only">locked</span></span
>

<style>
  .lockbadge {
    display: inline-grid;
    place-items: center;
    width: 20px;
    height: 20px;
    border: 1px solid var(--line);
    border-radius: 4px;
    background: var(--wash);
    color: var(--ink-soft);
  }
  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0 0 0 0);
    white-space: nowrap;
  }
</style>

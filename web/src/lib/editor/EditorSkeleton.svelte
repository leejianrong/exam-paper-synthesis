<script lang="ts">
  // The editor's first load (EXA-165): the header and an A4 page in grey bars, where the real
  // ones will be, instead of a blank screen. The bars (app.css `.skel`) hold still with reduced
  // motion.
  const lines = [92, 78, 85, 40, 0, 88, 70, 0, 94, 82, 60]
</script>

<div class="skeleton" role="status" data-testid="editor-skeleton">
  <span class="visually-hidden">Opening the paper…</span>
  <div class="sk-head" aria-hidden="true">
    <span class="skel" style:width="32px" style:height="24px"></span>
    <span class="skel" style:width="220px" style:height="16px"></span>
    <span class="gap"></span>
    <span class="skel" style:width="84px" style:height="28px"></span>
    <span class="skel" style:width="84px" style:height="28px"></span>
  </div>
  <div class="sk-desk" aria-hidden="true">
    <div class="sk-page">
      <span class="skel" style:width="55%" style:height="22px"></span>
      <span class="skel meta" style:width="35%"></span>
      {#each lines as w, i (i)}
        {#if w}<span class="skel" style:width="{w}%"></span>{:else}<span class="gap-line"></span>{/if}
      {/each}
    </div>
  </div>
</div>

<style>
  .sk-head {
    display: flex;
    align-items: center;
    gap: var(--s3);
    height: 88px;
    padding: 0 var(--s4);
    box-sizing: border-box;
    background: var(--page);
    border-bottom: 1px solid var(--line);
  }
  .gap {
    flex: 1;
  }
  .sk-desk {
    min-height: 100vh;
    background: var(--desk);
    padding: var(--s6) var(--s4);
  }
  .sk-page {
    display: grid;
    gap: 14px;
    width: 210mm;
    max-width: 100%;
    min-height: 120mm;
    margin: 0 auto;
    padding: 18mm 20mm;
    box-sizing: border-box;
    background: var(--page);
    box-shadow: var(--shadow);
  }
  .meta {
    margin-bottom: var(--s4);
  }
  .gap-line {
    height: var(--s3);
  }
</style>

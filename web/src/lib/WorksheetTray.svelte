<script lang="ts">
  import { worksheet, totalMarks } from './worksheet'
  import type { Question } from './types'

  // A short, human-readable label for a worksheet row: the first part's text
  // (truncated), falling back to the blueprint code when there is no text yet.
  function label(q: Question): string {
    const text = q.question.parts[0]?.text?.trim()
    if (!text) return q.blueprint_code
    return text.length > 70 ? `${text.slice(0, 70)}…` : text
  }
</script>

<aside class="tray" aria-label="worksheet">
  <label class="title">
    <span class="title-label">Worksheet title</span>
    <input
      type="text"
      value={$worksheet.title}
      on:input={(e) => worksheet.setTitle(e.currentTarget.value)}
    />
  </label>

  {#if $worksheet.items.length === 0}
    <p class="empty">No questions yet. Approve a question to add it here.</p>
  {:else}
    <ol class="items">
      {#each $worksheet.items as item, i (item.id)}
        <li class="item">
          <span class="index">{i + 1}.</span>
          <span class="label">{label(item)}</span>
          <span class="marks">[{item.question.total_marks}]</span>
          <span class="actions">
            <button
              class="reorder"
              title="Move up"
              aria-label="Move up"
              on:click={() => worksheet.move(item.id, 'up')}
              disabled={i === 0}
            >
              ↑
            </button>
            <button
              class="reorder"
              title="Move down"
              aria-label="Move down"
              on:click={() => worksheet.move(item.id, 'down')}
              disabled={i === $worksheet.items.length - 1}
            >
              ↓
            </button>
            <button
              class="remove"
              title="Remove"
              aria-label="Remove"
              on:click={() => worksheet.remove(item.id)}
            >
              ✕
            </button>
          </span>
        </li>
      {/each}
    </ol>

    <p class="total">Total marks <b>[{$totalMarks}]</b></p>
  {/if}
</aside>

<style>
  .tray {
    background: var(--card);
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 1rem 1.15rem;
    box-shadow: 0 1px 2px rgba(20, 30, 60, 0.04);
  }
  .title {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
    margin-bottom: 0.9rem;
  }
  .title-label {
    color: var(--muted);
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
  .title input {
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 0.45rem 0.6rem;
    font-size: 1rem;
    font-weight: 600;
    color: var(--ink);
    background: var(--bg, #fff);
  }
  .empty { color: var(--muted); margin: 0; }
  .items {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
  }
  .item {
    display: flex;
    align-items: baseline;
    gap: 0.5rem;
    font-size: 0.9rem;
    line-height: 1.4;
  }
  .index { color: var(--muted); flex: 0 0 auto; }
  .label { flex: 1 1 auto; }
  .marks { color: var(--muted); flex: 0 0 auto; font-size: 0.82rem; }
  .actions {
    display: flex;
    gap: 0.25rem;
    flex: 0 0 auto;
  }
  .reorder,
  .remove {
    background: transparent;
    border: 1px solid var(--line);
    border-radius: 6px;
    padding: 0.1rem 0.4rem;
    font-size: 0.8rem;
    line-height: 1.2;
    cursor: pointer;
    color: var(--accent);
  }
  .remove { color: var(--muted); }
  .reorder:disabled { opacity: 0.4; cursor: default; }
  .total {
    margin: 0.9rem 0 0;
    padding-top: 0.6rem;
    border-top: 1px solid var(--line);
    font-size: 0.9rem;
  }
</style>

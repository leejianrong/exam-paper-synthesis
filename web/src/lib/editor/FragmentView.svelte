<script lang="ts">
  // A question drawn by the engine's own renderer (the print markup), inside a shadow root
  // so its stylesheet cannot leak into — or be changed by — the app. Used for bank
  // questions: any shape the schema holds (MCQ options, tables, grids, constructions…)
  // draws correctly with no TypeScript mirror to drift from the PDF.
  import { onDestroy } from 'svelte'
  import type { Question } from '../types'
  import { loadFragmentAssets, renderQuestion, typeset } from './fragments'

  export let question: Question
  export let mode: 'student' | 'key' = 'student'
  export let number: number | null = null

  let host: HTMLDivElement | undefined
  let mountPoint: HTMLDivElement | null = null
  let error = ''
  let latest = 0
  let alive = true
  onDestroy(() => (alive = false))

  async function draw(q: Question, m: 'student' | 'key', n: number | null) {
    const ticket = ++latest
    try {
      const [html, assets] = await Promise.all([renderQuestion(q, m, n), loadFragmentAssets()])
      if (!alive || ticket !== latest || !host) return // superseded or gone
      if (!mountPoint) {
        const root = host.attachShadow({ mode: 'open' })
        assets.applyTo(root)
        mountPoint = document.createElement('div')
        root.appendChild(mountPoint)
      }
      // `html` is the engine's own escaped print markup (same as the PDF), not user HTML.
      mountPoint.innerHTML = html
      typeset(mountPoint)
      error = ''
    } catch (e) {
      if (alive && ticket === latest) error = e instanceof Error ? e.message : String(e)
    }
  }

  $: if (host) void draw(question, mode, number)
</script>

<div class="fragment" bind:this={host} data-testid="fragment"></div>
{#if error}
  <p class="error" role="alert">{error}</p>
{/if}

<style>
  .error {
    color: var(--mark);
    font-size: 12.5px;
    margin: 0.3rem 0 0;
  }
</style>

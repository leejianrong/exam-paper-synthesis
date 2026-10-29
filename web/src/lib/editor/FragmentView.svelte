<script lang="ts">
  // A question drawn by the engine's own renderer (the print markup), inside a shadow root
  // so its stylesheet cannot leak into — or be changed by — the app. Used for bank
  // questions: any shape the schema holds (MCQ options, tables, grids, constructions…)
  // draws correctly with no TypeScript mirror to drift from the PDF.
  import { onDestroy } from 'svelte'
  import type { Question } from '../types'
  import { loadFragmentAssets, renderQuestion, typeset } from './fragments'
  import type { KeyOptions, MarksPlacement } from './layout'

  export let question: Question
  export let mode: 'student' | 'key' = 'student'
  export let number: number | null = null
  /** Print the way a paper does (marks per the setting), the editor drawing the answer area. */
  /** Answer-key options (P5), mirrored by CSS in the shadow root; the engine's PDF is authoritative. */
  export let keyOptions: KeyOptions | undefined = undefined
  export let paper: { placement: MarksPlacement; answerArea: boolean } | undefined = undefined

  const KEY_CSS =
    '.hide-q .question-stem,.hide-q .part-text,.hide-q .options,.hide-q .content-table,' +
    '.hide-q figure.diagram:not(.answer-diagram){display:none}.hide-scheme .marking-scheme{display:none}'

  let host: HTMLDivElement | undefined
  let mountPoint: HTMLDivElement | null = null
  let error = ''
  let latest = 0
  let alive = true
  onDestroy(() => (alive = false))

  async function draw(
    q: Question,
    m: 'student' | 'key',
    n: number | null,
    pp: typeof paper,
  ) {
    const ticket = ++latest
    try {
      const [html, assets] = await Promise.all([renderQuestion(q, m, n, pp), loadFragmentAssets()])
      if (!alive || ticket !== latest || !host) return // superseded or gone
      if (!mountPoint) {
        const root = host.attachShadow({ mode: 'open' })
        assets.applyTo(root)
        mountPoint = document.createElement('div')
        const style = document.createElement('style')
        style.textContent = KEY_CSS
        root.append(style, mountPoint)
      }
      applyKey(keyOptions)
      // `html` is the engine's own escaped print markup (same as the PDF), not user HTML.
      mountPoint.innerHTML = html
      typeset(mountPoint)
      error = ''
    } catch (e) {
      if (alive && ticket === latest) error = e instanceof Error ? e.message : String(e)
    }
  }

  $: if (host) void draw(question, mode, number, paper)

  // Option changes re-class the live fragment; no re-render is needed.
  function applyKey(ko: typeof keyOptions) {
    mountPoint?.classList.toggle('hide-q', ko?.show_question === false)
    mountPoint?.classList.toggle('hide-scheme', ko?.show_scheme === false)
  }
  $: applyKey(keyOptions)
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

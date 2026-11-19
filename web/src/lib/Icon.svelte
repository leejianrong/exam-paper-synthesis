<script lang="ts" module>
  // One stroke set for the app chrome (EXA-160): 16 px, 1.5 stroke, no fill. Decorative: the
  // control that holds an icon carries the accessible name.
  const P16: Record<string, string[]> = {
    back: ['M10 3 5 8l5 5'],
    check: ['m3.5 8.5 3 3 6-7'],
    down: ['m4 6 4 4 4-4'],
    eye: ['M1.5 8S4 3.5 8 3.5 14.5 8 14.5 8 12 12.5 8 12.5 1.5 8 1.5 8z', 'M10 8a2 2 0 1 1-4 0 2 2 0 0 1 4 0z'],
    export: ['M8 2.5v8', 'M4.5 7 8 10.5 11.5 7', 'M3 13.5h10'],
    plus: ['M8 3v10', 'M3 8h10'],
    undo: ['M5 4 2.5 6.5 5 9', 'M2.5 6.5H10a3.5 3.5 0 0 1 0 7H7'],
    redo: ['M11 4l2.5 2.5L11 9', 'M13.5 6.5H6a3.5 3.5 0 0 0 0 7h3'],
    bullets: ['M6.5 4h7', 'M6.5 8h7', 'M6.5 12h7', 'M3 4h.01', 'M3 8h.01', 'M3 12h.01'],
    numbers: ['M6.5 4h7', 'M6.5 8h7', 'M6.5 12h7', 'M2.5 3l1-.5V6', 'M2.3 9.3c.3-.5 1.7-.6 1.7.3 0 .8-1.7 1.4-1.7 2.4H4'],
    sigma: ['M12 3H4l4.5 5L4 13h8'],
    image: ['M4 3h8a1.5 1.5 0 0 1 1.5 1.5v7A1.5 1.5 0 0 1 12 13H4a1.5 1.5 0 0 1-1.5-1.5v-7A1.5 1.5 0 0 1 4 3z', 'M7.2 6.5a1.2 1.2 0 1 1-2.4 0 1.2 1.2 0 0 1 2.4 0z', 'm3 12 3.5-3.5L9 11l2-2 2.5 2.5'],
    swap: ['M13 6.5A5 5 0 0 0 4 4.3L2.5 6', 'M2.5 2.5V6H6', 'M3 9.5A5 5 0 0 0 12 11.7l1.5-1.7', 'M13.5 13.5V10H10'],
    alert: ['M8 2.5 14 13H2z', 'M8 6.5v3', 'M8 11.3v.01'],
    cover: ['M4 2.5h8a.5.5 0 0 1 .5.5v10a.5.5 0 0 1-.5.5H4a.5.5 0 0 1-.5-.5V3a.5.5 0 0 1 .5-.5z', 'M5.5 5h5', 'M6 7h4', 'M5.5 10h5'],
    blankpage: ['M4 2.5h6l2.5 2.5v8a.5.5 0 0 1-.5.5H4a.5.5 0 0 1-.5-.5V3a.5.5 0 0 1 .5-.5z', 'M10 2.5V5h2.5'],
    pagebreak: ['M4 2.5h8v4', 'M4 13.5h8v-4', 'M2 8h1.5', 'M5.5 8h1.5', 'M9 8h1.5', 'M12.5 8H14'],
    settings: ['M8 10a2 2 0 1 0 0-4 2 2 0 0 0 0 4z', 'M8 1.5v2M8 12.5v2M1.5 8h2M12.5 8h2M3.4 3.4l1.4 1.4M11.2 11.2l1.4 1.4M3.4 12.6l1.4-1.4M11.2 4.8l1.4-1.4'],
    download: ['M8 2.5v8', 'M4.5 7 8 10.5 11.5 7', 'M3 13.5h10'],
    signout: ['M6 2.5H3.5a1 1 0 0 0-1 1v9a1 1 0 0 0 1 1H6', 'M10.5 11 13.5 8l-3-3', 'M13.5 8H6'],
    trash: ['M3 4.5h10', 'M6.5 4.5V3h3v1.5', 'M4.5 4.5l.6 8.5h5.8l.6-8.5'],
    // the question bar and its menu (EXA-161)
    lock: ['M5 7h6a1.5 1.5 0 0 1 1.5 1.5V12A1.5 1.5 0 0 1 11 13.5H5A1.5 1.5 0 0 1 3.5 12V8.5A1.5 1.5 0 0 1 5 7z', 'M5.5 7V5a2.5 2.5 0 0 1 5 0v2'],
    unlock: ['M5 7h6a1.5 1.5 0 0 1 1.5 1.5V12A1.5 1.5 0 0 1 11 13.5H5A1.5 1.5 0 0 1 3.5 12V8.5A1.5 1.5 0 0 1 5 7z', 'M5.5 7V5a2.5 2.5 0 0 1 4.9-.7'],
    topic: ['M3 4h10', 'M3 8h6', 'M3 12h8'],
    easier: ['M8 3v10', 'M4 9l4 4 4-4'],
    harder: ['M8 13V3', 'M4 7l4-4 4 4'],
    names: ['M10.5 5.5a2.5 2.5 0 1 1-5 0 2.5 2.5 0 0 1 5 0z', 'M3 13.5a5 5 0 0 1 10 0'],
    key: ['M7.5 8a2.5 2.5 0 1 1-5 0 2.5 2.5 0 0 1 5 0z', 'M7.5 8h6', 'M11.5 8v2.5'],
    pen: ['m10.5 2.5 3 3L6 13H3v-3z'],
    text: ['M3 4V3h10v1', 'M8 3v10', 'M6 13h4'],
    part: ['M3 4h10', 'M3 8h4', 'M3 12h4', 'M11 9.5v5', 'M8.5 12h5'],
    // the editor's menus (EXA-163)
    folder: ['M2 4.5A1.5 1.5 0 0 1 3.5 3H6l1.5 1.5h5A1.5 1.5 0 0 1 14 6v5.5a1.5 1.5 0 0 1-1.5 1.5h-9A1.5 1.5 0 0 1 2 11.5z'],
    copy: ['M6.5 5.5h6a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1h-6a1 1 0 0 1-1-1v-6a1 1 0 0 1 1-1z', 'M3.5 10.5a1 1 0 0 1-1-1v-6a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1'],
    keyboard: ['M2.5 4h11a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1h-11a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1z', 'M4.5 6.5h.01', 'M7 6.5h.01', 'M9.5 6.5h.01', 'M12 6.5h.01', 'M5 9.5h6'],
    panel: ['M3 2.5h10a.5.5 0 0 1 .5.5v10a.5.5 0 0 1-.5.5H3a.5.5 0 0 1-.5-.5V3a.5.5 0 0 1 .5-.5z', 'M10 2.5v11'],
    section: ['M2.5 4h11', 'M2.5 7h7', 'M2.5 11h11'],
    info: ['M14 8A6 6 0 1 1 2 8a6 6 0 0 1 12 0z', 'M8 7.5v3.5', 'M8 5h.01'],
    // the papers list (EXA-166)
    search: ['M11.5 7a4.5 4.5 0 1 1-9 0 4.5 4.5 0 0 1 9 0z', 'm10.5 10.5 3 3'],
    open: ['M9.5 2.5h4v4', 'M13.5 2.5 8 8', 'M11.5 9.5v3a1 1 0 0 1-1 1h-7a1 1 0 0 1-1-1v-7a1 1 0 0 1 1-1h3'],
  }
  /** Drawn filled (dots), not stroked. */
  const DOTS: Record<string, Array<[number, number]>> = {
    more: [[3.5, 8], [8, 8], [12.5, 8]],
    grip: [[6, 4], [10, 4], [6, 8], [10, 8], [6, 12], [10, 12]],
  }
  export type IconName = keyof typeof P16 | keyof typeof DOTS
</script>

<script lang="ts">
  let { name, size = 16 }: { name: IconName; size?: number } = $props()
</script>

<svg
  class="icon"
  viewBox="0 0 16 16"
  width={size}
  height={size}
  fill="none"
  stroke="currentColor"
  stroke-width="1.5"
  stroke-linecap="round"
  stroke-linejoin="round"
  aria-hidden="true"
  focusable="false"
>
  {#if DOTS[name]}
    {#each DOTS[name] as [cx, cy] (`${cx},${cy}`)}<circle {cx} {cy} r="1" fill="currentColor" stroke="none" />{/each}
  {:else}
    {#each P16[name] ?? [] as d (d)}<path {d} />{/each}
  {/if}
</svg>

<style>
  .icon {
    flex: none;
  }
</style>

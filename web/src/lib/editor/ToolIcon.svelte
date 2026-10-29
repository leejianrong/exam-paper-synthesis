<script lang="ts">
  // The small line icons of the formatting toolbar (24px grid, 1.8 stroke, no fill), in the
  // style people know from Word and Docs. Decorative: the button carries the accessible name.
  export let name: 'bullet' | 'ordered' | 'pagebreak' | 'section' | 'equation' | 'image' | 'undo' | 'redo'

  const PATHS: Record<typeof name, string[]> = {
    bullet: ['M9 6h12', 'M9 12h12', 'M9 18h12', 'M4 6h.01', 'M4 12h.01', 'M4 18h.01'],
    ordered: [
      'M10 6h11',
      'M10 12h11',
      'M10 18h11',
      'M4 5l1.5-1V9',
      'M3.5 11.5a1.6 1.6 0 1 1 2.8 1.1L3.5 15.5H6.6',
      'M3.5 17.5h2.6l-1.3 1.8a1.5 1.5 0 1 1-1.3 2.2',
    ],
    pagebreak: ['M6 3h12v7', 'M6 21h12v-7', 'M3 12h2', 'M8 12h2', 'M14 12h2', 'M19 12h2'],
    section: ['M3 7h18', 'M3 11h12', 'M3 17h18', 'M3 21h10'],
    equation: ['M18 5H6l6.2 7L6 19h12'],
    image: ['M4 5h16a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1z', 'M21 16l-5-5L8 19', 'M9 10h.01'],
    undo: ['M9 14L4 9l5-5', 'M4 9h10.5a5.5 5.5 0 0 1 0 11H11'],
    redo: ['M15 14l5-5-5-5', 'M20 9H9.5a5.5 5.5 0 0 0 0 11H13'],
  }
</script>

<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">
  {#each PATHS[name] as d (d)}<path {d} />{/each}
</svg>

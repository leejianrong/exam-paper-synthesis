<script lang="ts">
  // Question text with authored inline maths (`\( … \)`, e.g. algebra's 5n − 7 or a fraction
  // option): plain text stays text, each formula is typeset by the editor's KaTeX (math.ts).
  import { splitMath } from './mathText'
  import { typesetMath } from './editor/math'

  export let text: string
  $: pieces = splitMath(text)
</script>

<span class="mtext" use:typesetMath={text}
  >{#each pieces as p, i (i)}{#if p.math}<span class="math-host" data-latex={p.value}>{p.value}</span
      >{:else}{p.value}{/if}{/each}</span
>

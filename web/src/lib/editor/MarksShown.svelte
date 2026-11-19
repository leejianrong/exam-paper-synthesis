<script lang="ts">
  // "Marks shown" (EXA-164): the one control, with one set of labels, for where a question's [n]
  // prints, used by the paper (settings.marks_placement) and by each section. A section adds its
  // default ("Same as the paper", or for multiple choice and short answer the mode's own default,
  // as the engine does) and "In the section header".
  import type { SectionMode } from './doc'
  import { MARKS_SHOWN, type MarksPlacement } from './layout'
  import { sectionMarksDefault } from './sections'

  /** The stored choice; '' is a section's default. */
  export let value: string
  /** True for a section's control: it adds the default and "In the section header". */
  export let section = false
  /** The section's mode, which names its default. */
  export let mode: SectionMode | null = null
  export let describedby: string | undefined = undefined

  const PAPER_CHOICES: MarksPlacement[] = ['answer', 'question', 'both']
</script>

<select aria-describedby={describedby} {value} on:change>
  {#if section}
    <option value="">{sectionMarksDefault(mode)}</option>
  {/if}
  {#each PAPER_CHOICES as choice (choice)}
    <option value={choice}>{MARKS_SHOWN[choice]}</option>
  {/each}
  {#if section}
    <option value="none">{MARKS_SHOWN.none}</option>
  {/if}
</select>

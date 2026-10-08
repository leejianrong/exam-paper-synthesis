<script lang="ts">
  import ClassicPage from './ClassicPage.svelte'
  import DocumentList from './lib/editor/DocumentList.svelte'
  import EditorPage from './lib/editor/EditorPage.svelte'
  import { route } from './lib/router'
</script>

{#if $route.name === 'editor'}
  {#key $route.id}
    <EditorPage id={$route.id} />
  {/key}
{:else if $route.name === 'classic'}
  <ClassicPage />
{:else}
  <DocumentList />
{/if}

<script lang="ts">
  // #/classic while the setting is off (O1): say so, and offer the switch.
  import { errorText } from './errors'
  import { updateSettings } from './settings'

  let error = ''
  async function turnOn() {
    try {
      await updateSettings({ classic_generator: true })
    } catch (e) {
      error = errorText(e, "The Classic generator wasn't turned on")
    }
  }
</script>

<main>
  <h1>The Classic generator is turned off</h1>
  <p>It's hidden by default. Turn it on here or in <a href="#/settings">Settings</a>.</p>
  <p class="actions">
    <button on:click={turnOn}>Turn on the Classic generator</button>
    <a href="#/">Back to your papers</a>
  </p>
  {#if error}<p class="error" role="alert">{error}</p>{/if}
</main>

<style>
  main {
    max-width: 640px;
    margin: 4rem auto;
    padding: 0 1rem;
  }
  h1 {
    font-family: var(--serif);
  }
  .actions {
    display: flex;
    gap: 1rem;
    align-items: center;
  }
  button {
    font: inherit;
    border: 1px solid var(--verify);
    background: var(--verify);
    color: var(--paper);
    border-radius: 8px;
    padding: 0.45rem 0.9rem;
    cursor: pointer;
  }
  .error {
    color: var(--mark);
  }
</style>

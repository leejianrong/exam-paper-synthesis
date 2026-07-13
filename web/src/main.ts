import './app.css'
import { mount } from 'svelte'
import App from './App.svelte'

// Svelte 5 replaces `new App({ target })` with the `mount()` API.
const app = mount(App, { target: document.getElementById('app')! })

export default app

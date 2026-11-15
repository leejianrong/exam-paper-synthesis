import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/svelte'
import { get } from 'svelte/store'
import SettingsPage from './SettingsPage.svelte'
import ClassicOff from './ClassicOff.svelte'
import { settings } from './settings'

const fetchMock = vi.fn()

function reply(body: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(body), { status }))
}

beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
  settings.set(null)
})

describe('SettingsPage (O1)', () => {
  it('loads the account settings: the Classic generator is off by default', async () => {
    fetchMock.mockImplementation(() => reply({ classic_generator: false }))
    render(SettingsPage)
    const sw = await screen.findByRole('switch', { name: 'Show the Classic generator' })
    expect(sw).not.toBeChecked()
    expect(fetchMock.mock.calls[0][0]).toMatch(/\/settings$/)
  })

  it('turning the switch on saves it on the account', async () => {
    settings.set({ classic_generator: false })
    fetchMock.mockImplementation(() => reply({ classic_generator: true }))
    render(SettingsPage)
    await fireEvent.click(screen.getByRole('switch', { name: 'Show the Classic generator' }))
    await waitFor(() => expect(get(settings)).toEqual({ classic_generator: true }))
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toMatch(/\/settings$/)
    expect(init.method).toBe('PUT')
    expect(JSON.parse(init.body)).toEqual({ classic_generator: true })
    expect(await screen.findByRole('status')).toHaveTextContent('The Classic generator is on.')
  })

  it('a failed save says so and leaves the setting as it was', async () => {
    settings.set({ classic_generator: false })
    fetchMock.mockImplementation(() => reply({ detail: 'nope' }, 500))
    render(SettingsPage)
    await fireEvent.click(screen.getByRole('switch', { name: 'Show the Classic generator' }))
    expect(await screen.findByRole('alert')).toHaveTextContent("Couldn't save the setting (500).")
    expect(get(settings)).toEqual({ classic_generator: false })
  })
})

describe('ClassicOff', () => {
  it('offers to turn the Classic generator on', async () => {
    settings.set({ classic_generator: false })
    fetchMock.mockImplementation(() => reply({ classic_generator: true }))
    render(ClassicOff)
    await fireEvent.click(screen.getByRole('button', { name: 'Turn on the Classic generator' }))
    await waitFor(() => expect(get(settings)?.classic_generator).toBe(true))
  })
})

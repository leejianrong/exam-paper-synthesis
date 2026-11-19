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
    fetchMock.mockImplementation(() => reply({ classic_generator: false, answer_key_style: 'school' }))
    render(SettingsPage)
    const sw = await screen.findByRole('switch', { name: 'Show the Classic generator' })
    expect(sw).not.toBeChecked()
    expect(fetchMock.mock.calls[0][0]).toMatch(/\/settings$/)
  })

  it('turning the switch on saves it on the account', async () => {
    settings.set({ classic_generator: false, answer_key_style: 'school' })
    fetchMock.mockImplementation(() => reply({ classic_generator: true, answer_key_style: 'school' }))
    render(SettingsPage)
    await fireEvent.click(screen.getByRole('switch', { name: 'Show the Classic generator' }))
    await waitFor(() => expect(get(settings)).toEqual({ classic_generator: true, answer_key_style: 'school' }))
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toMatch(/\/settings$/)
    expect(init.method).toBe('PUT')
    expect(JSON.parse(init.body)).toEqual({ classic_generator: true })
    expect(await screen.findByRole('status')).toHaveTextContent('The Classic generator is on.')
  })

  it('a failed save says so and leaves the setting as it was', async () => {
    settings.set({ classic_generator: false, answer_key_style: 'school' })
    fetchMock.mockImplementation(() => reply({ detail: 'nope' }, 500))
    render(SettingsPage)
    await fireEvent.click(screen.getByRole('switch', { name: 'Show the Classic generator' }))
    expect(await screen.findByRole('alert')).toHaveTextContent("The setting wasn't saved. Something went wrong on our side.")
    expect(get(settings)).toEqual({ classic_generator: false, answer_key_style: 'school' })
  })
})

describe('SettingsPage: answer key style (EXA-159)', () => {
  it('new papers get the school key by default', async () => {
    fetchMock.mockImplementation(() => reply({ classic_generator: false, answer_key_style: 'school' }))
    render(SettingsPage)
    const group = await screen.findByRole('radiogroup', { name: 'Answer key style' })
    expect(group).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: 'School key' })).toBeChecked()
    expect(screen.getByRole('radio', { name: 'Worked solutions' })).not.toBeChecked()
  })

  it('choosing worked solutions saves it on the account', async () => {
    settings.set({ classic_generator: false, answer_key_style: 'school' })
    fetchMock.mockImplementation(() => reply({ classic_generator: false, answer_key_style: 'worked' }))
    render(SettingsPage)
    await fireEvent.click(screen.getByRole('radio', { name: 'Worked solutions' }))
    await waitFor(() => expect(get(settings)?.answer_key_style).toBe('worked'))
    const [, init] = fetchMock.mock.calls[0]
    expect(init.method).toBe('PUT')
    expect(JSON.parse(init.body)).toEqual({ answer_key_style: 'worked' })
    expect(await screen.findByRole('status')).toHaveTextContent('New papers get worked solutions.')
    expect(screen.getByRole('radio', { name: 'Worked solutions' })).toBeChecked()
  })
})

describe('ClassicOff', () => {
  it('offers to turn the Classic generator on', async () => {
    settings.set({ classic_generator: false, answer_key_style: 'school' })
    fetchMock.mockImplementation(() => reply({ classic_generator: true, answer_key_style: 'school' }))
    render(ClassicOff)
    await fireEvent.click(screen.getByRole('button', { name: 'Turn on the Classic generator' }))
    await waitFor(() => expect(get(settings)?.classic_generator).toBe(true))
  })

  it('a failed load falls back to the defaults and retries once', async () => {
    vi.useFakeTimers()
    const { loadSettings } = await import('./settings')
    fetchMock.mockImplementationOnce(() => reply({ detail: 'down' }, 500)).mockImplementation(() => reply({ classic_generator: true, answer_key_style: 'school' }))
    await loadSettings(1000)
    expect(get(settings)).toEqual({ classic_generator: false, answer_key_style: 'school' })
    await vi.advanceTimersByTimeAsync(1000)
    expect(get(settings)).toEqual({ classic_generator: true, answer_key_style: 'school' })
    vi.useRealTimers()
  })

  it('settings are forgotten when nobody is signed in', async () => {
    const { session } = await import('./session')
    settings.set({ classic_generator: true, answer_key_style: 'school' })
    session.set({ status: 'anon' })
    expect(get(settings)).toBeNull()
  })
})

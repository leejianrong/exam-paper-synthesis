import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor, within } from '@testing-library/svelte'
import { get } from 'svelte/store'
import SettingsPage from './SettingsPage.svelte'
import ClassicOff from './ClassicOff.svelte'
import { DEFAULT_SETTINGS, settings } from './settings'

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
    fetchMock.mockImplementation(() => reply({ ...DEFAULT_SETTINGS }))
    render(SettingsPage)
    const sw = await screen.findByRole('switch', { name: 'Show the Classic generator' })
    expect(sw).not.toBeChecked()
    expect(fetchMock.mock.calls[0][0]).toMatch(/\/settings$/)
  })

  it('turning the switch on saves it on the account', async () => {
    settings.set({ ...DEFAULT_SETTINGS })
    fetchMock.mockImplementation(() => reply({ ...DEFAULT_SETTINGS, classic_generator: true }))
    render(SettingsPage)
    await fireEvent.click(screen.getByRole('switch', { name: 'Show the Classic generator' }))
    await waitFor(() => expect(get(settings)).toEqual({ ...DEFAULT_SETTINGS, classic_generator: true }))
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toMatch(/\/settings$/)
    expect(init.method).toBe('PUT')
    expect(JSON.parse(init.body)).toEqual({ classic_generator: true })
    expect(await screen.findByRole('status')).toHaveTextContent('The Classic generator is on.')
  })

  it('a failed save says so and leaves the setting as it was', async () => {
    settings.set({ ...DEFAULT_SETTINGS })
    fetchMock.mockImplementation(() => reply({ detail: 'nope' }, 500))
    render(SettingsPage)
    await fireEvent.click(screen.getByRole('switch', { name: 'Show the Classic generator' }))
    expect(await screen.findByRole('alert')).toHaveTextContent("The setting wasn't saved. Something went wrong on our side.")
    expect(get(settings)).toEqual({ ...DEFAULT_SETTINGS })
  })
})

describe('SettingsPage: answer key style (EXA-159)', () => {
  it('new papers get the school key by default', async () => {
    fetchMock.mockImplementation(() => reply({ ...DEFAULT_SETTINGS }))
    render(SettingsPage)
    const group = await screen.findByRole('radiogroup', { name: 'Answer key style' })
    expect(group).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: 'School key' })).toBeChecked()
    expect(screen.getByRole('radio', { name: 'Worked solutions' })).not.toBeChecked()
  })

  it('choosing worked solutions saves it on the account', async () => {
    settings.set({ ...DEFAULT_SETTINGS })
    fetchMock.mockImplementation(() => reply({ ...DEFAULT_SETTINGS, answer_key_style: 'worked' }))
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

describe('SettingsPage: new papers (EXA-169)', () => {
  it('groups the new-paper defaults, each saying it is for papers made from now on', async () => {
    fetchMock.mockImplementation(() => reply({ ...DEFAULT_SETTINGS }))
    render(SettingsPage)
    const group = await screen.findByRole('group', { name: 'New papers' })
    const school = within(group).getByRole('textbox', { name: 'School name' })
    expect(school).toHaveValue('')
    expect(school).toHaveAccessibleDescription(/papers you make from now on/)
    expect(within(group).getByRole('radiogroup', { name: 'Level' })).toBeInTheDocument()
    expect(within(group).getByRole('radio', { name: 'Not set' })).toBeChecked()
    const marks = within(group).getByRole('combobox', { name: 'Marks shown' })
    expect(marks).toHaveValue('answer')
    expect(marks).toHaveAccessibleDescription(/papers you make from now on/)
    // the editor's "Marks shown" labels (layout.MARKS_SHOWN), the paper's three choices
    expect([...(marks as HTMLSelectElement).options].map((o) => o.text)).toEqual([
      'After the Ans: line',
      'Beside each question',
      'Both',
    ])
    expect(within(group).getByRole('radiogroup', { name: 'Answer key style' })).toBeInTheDocument()
    expect(screen.getByText('Level').closest('section')).toHaveTextContent(/papers you make from now on/)
    expect(screen.getByText('Answer key style').closest('section')).toHaveTextContent(/Papers you already have keep their own/)
  })

  it('saves the school name when the field is left, trimmed by the server', async () => {
    settings.set({ ...DEFAULT_SETTINGS })
    fetchMock.mockImplementation(() => reply({ ...DEFAULT_SETTINGS, school_name: 'Example Primary School' }))
    render(SettingsPage)
    const school = screen.getByRole('textbox', { name: 'School name' })
    await fireEvent.input(school, { target: { value: '  Example Primary School ' } })
    await fireEvent.change(school)
    await waitFor(() => expect(get(settings)?.school_name).toBe('Example Primary School'))
    const [, init] = fetchMock.mock.calls[0]
    expect(init.method).toBe('PUT')
    expect(JSON.parse(init.body)).toEqual({ school_name: 'Example Primary School' })
    expect(await screen.findByRole('status')).toHaveTextContent("New papers' covers will say Example Primary School.")
    expect(school).toHaveValue('Example Primary School')
    // leaving it again unchanged saves nothing
    await fireEvent.change(school)
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('saves the level and the marks placement', async () => {
    settings.set({ ...DEFAULT_SETTINGS })
    fetchMock.mockImplementation((_url: string, init: RequestInit) =>
      reply({ ...(get(settings) ?? DEFAULT_SETTINGS), ...JSON.parse(String(init.body)) }),
    )
    render(SettingsPage)
    await fireEvent.click(screen.getByRole('radio', { name: 'P5' }))
    await waitFor(() => expect(get(settings)?.default_level).toBe('P5'))
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ default_level: 'P5' })
    expect(await screen.findByRole('status')).toHaveTextContent('New papers are P5.')
    expect(screen.getByRole('radio', { name: 'P5' })).toBeChecked()

    await fireEvent.change(screen.getByRole('combobox', { name: 'Marks shown' }), { target: { value: 'both' } })
    await waitFor(() => expect(get(settings)?.marks_placement).toBe('both'))
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({ marks_placement: 'both' })
    expect(screen.getByRole('status')).toHaveTextContent('Marks shown on new papers: Both.')
  })
})

describe('SettingsPage: saving in order (EXA-169 review)', () => {
  /** A PUT /settings the test answers by hand. */
  function deferred() {
    let answer!: (r: Response) => void
    const promise = new Promise<Response>((r) => (answer = r))
    return { promise, answer }
  }
  const echo = (init: RequestInit) => ({ ...(get(settings) ?? DEFAULT_SETTINGS), ...JSON.parse(String(init.body)) })

  it('a level clicked while the school name is saving is kept, and saved after it', async () => {
    settings.set({ ...DEFAULT_SETTINGS })
    const first = deferred()
    fetchMock
      .mockImplementationOnce(() => first.promise)
      .mockImplementation((_u: string, init: RequestInit) => reply(echo(init)))
    render(SettingsPage)
    const school = screen.getByRole('textbox', { name: 'School name' })
    await fireEvent.input(school, { target: { value: 'Example Primary School' } })
    await fireEvent.change(school) // leaving the field saves it...
    await fireEvent.blur(school)
    const p5 = screen.getByRole('radio', { name: 'P5' })
    expect(p5).toBeEnabled() // ...and the click on P5 that left it is not swallowed
    await fireEvent.click(p5)
    expect(fetchMock).toHaveBeenCalledTimes(1) // the level waits for the school name
    first.answer(new Response(JSON.stringify({ ...DEFAULT_SETTINGS, school_name: 'Example Primary School' })))
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({ default_level: 'P5' })
    await waitFor(() =>
      expect(get(settings)).toMatchObject({ school_name: 'Example Primary School', default_level: 'P5' }),
    )
    expect(school).toHaveValue('Example Primary School')
    expect(screen.getByRole('status')).toHaveTextContent('New papers are P5.')
  })

  it('a failed school save keeps what was typed; Try again saves it and shows what was stored', async () => {
    settings.set({ ...DEFAULT_SETTINGS })
    fetchMock
      .mockImplementationOnce(() => Promise.reject(new TypeError('Failed to fetch')))
      .mockImplementation((_u: string, init: RequestInit) => reply(echo(init)))
    render(SettingsPage)
    const school = screen.getByRole('textbox', { name: 'School name' })
    await fireEvent.focus(school)
    await fireEvent.input(school, { target: { value: 'Example Primary School  ' } })
    await fireEvent.change(school)
    await fireEvent.blur(school)
    expect(await screen.findByRole('alert')).toHaveTextContent("The school name wasn't saved")
    expect(school).toHaveValue('Example Primary School  ') // not wiped
    await fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    await waitFor(() => expect(get(settings)?.school_name).toBe('Example Primary School'))
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({ school_name: 'Example Primary School' })
    await waitFor(() => expect(school).toHaveValue('Example Primary School'))
  })

  it("a later save of another setting doesn't hide that the school name wasn't saved", async () => {
    settings.set({ ...DEFAULT_SETTINGS })
    fetchMock
      .mockImplementationOnce(() => Promise.reject(new TypeError('Failed to fetch'))) // school
      .mockImplementation((_u: string, init: RequestInit) => reply(echo(init)))
    render(SettingsPage)
    const school = screen.getByRole('textbox', { name: 'School name' })
    await fireEvent.input(school, { target: { value: 'Example Primary School' } })
    await fireEvent.change(school)
    await fireEvent.blur(school)
    await fireEvent.click(screen.getByRole('radio', { name: 'P5' }))
    await waitFor(() => expect(get(settings)?.default_level).toBe('P5'))
    expect(screen.getByRole('status')).toHaveTextContent('New papers are P5.')
    // the school name is still unsaved: the alert and Try again stay
    expect(screen.getByRole('alert')).toHaveTextContent("The school name wasn't saved")
    expect(get(settings)?.school_name).toBe('')
    await fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    await waitFor(() => expect(get(settings)?.school_name).toBe('Example Primary School'))
    expect(fetchMock.mock.calls.map((c) => JSON.parse(c[1].body))).toEqual([
      { school_name: 'Example Primary School' },
      { default_level: 'P5' },
      { school_name: 'Example Primary School' },
    ])
    expect(get(settings)?.default_level).toBe('P5')
    await waitFor(() => expect(screen.queryByRole('alert')).toBeNull())
    expect(screen.getByRole('status')).toHaveTextContent("New papers' covers will say Example Primary School.")
  })

  it('Try again re-sends every unsaved change, in order, and only their own success clears them', async () => {
    settings.set({ ...DEFAULT_SETTINGS })
    fetchMock
      .mockImplementationOnce(() => Promise.reject(new TypeError('Failed to fetch'))) // level
      .mockImplementationOnce(() => Promise.reject(new TypeError('Failed to fetch'))) // marks
      .mockImplementation((_u: string, init: RequestInit) => reply(echo(init)))
    render(SettingsPage)
    await fireEvent.click(screen.getByRole('radio', { name: 'P6' }))
    await fireEvent.change(screen.getByRole('combobox', { name: 'Marks shown' }), { target: { value: 'both' } })
    const alert = await screen.findByRole('alert')
    await waitFor(() => expect(alert).toHaveTextContent("Marks shown wasn't saved"))
    expect(alert).toHaveTextContent("The level wasn't saved")
    await fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    await waitFor(() => expect(get(settings)).toMatchObject({ default_level: 'P6', marks_placement: 'both' }))
    expect(fetchMock.mock.calls.slice(2).map((c) => JSON.parse(c[1].body))).toEqual([
      { default_level: 'P6' },
      { marks_placement: 'both' },
    ])
    await waitFor(() => expect(screen.queryByRole('alert')).toBeNull())
  })

  /** Type `value` into the school field and leave it (which saves it). */
  async function typeSchool(value: string) {
    const school = screen.getByRole('textbox', { name: 'School name' })
    await fireEvent.focus(school)
    await fireEvent.input(school, { target: { value } })
    await fireEvent.change(school)
    await fireEvent.blur(school)
    return school
  }

  it('going back to the stored school name drops its failure: Try again sends nothing stale', async () => {
    settings.set({ ...DEFAULT_SETTINGS, school_name: 'Old Example School' })
    fetchMock
      .mockImplementationOnce(() => Promise.reject(new TypeError('Failed to fetch')))
      .mockImplementation((_u: string, init: RequestInit) => reply(echo(init)))
    render(SettingsPage)
    await typeSchool('Exampel School')
    expect(await screen.findByRole('alert')).toHaveTextContent("The school name wasn't saved")
    const school = await typeSchool('Old Example School') // reverted
    await waitFor(() => expect(screen.queryByRole('alert')).toBeNull())
    expect(screen.queryByRole('button', { name: 'Try again' })).toBeNull()
    expect(fetchMock).toHaveBeenCalledTimes(1) // nothing re-sent
    expect(school).toHaveValue('Old Example School')
    expect(get(settings)?.school_name).toBe('Old Example School')
  })

  it('going back to the stored school name clears a refused (422) save', async () => {
    settings.set({ ...DEFAULT_SETTINGS, school_name: 'Old Example School' })
    fetchMock.mockImplementationOnce(() => reply({ detail: "'school_name' must be one line of text" }, 422))
    render(SettingsPage)
    await typeSchool('Bad Example School')
    expect(await screen.findByRole('alert')).toHaveTextContent("The school name wasn't saved")
    expect(screen.queryByRole('button', { name: 'Try again' })).toBeNull() // not retryable
    await typeSchool('Old Example School')
    await waitFor(() => expect(screen.queryByRole('alert')).toBeNull())
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('a newer school name drops the old failure as soon as it is made, and saves', async () => {
    settings.set({ ...DEFAULT_SETTINGS })
    const second = deferred()
    fetchMock
      .mockImplementationOnce(() => Promise.reject(new TypeError('Failed to fetch')))
      .mockImplementationOnce(() => second.promise)
    render(SettingsPage)
    await typeSchool('Exampel School')
    expect(await screen.findByRole('alert')).toHaveTextContent("The school name wasn't saved")
    const school = await typeSchool('Example Primary School')
    // superseded while the new name is still on its way: no Try again that would send the old one
    expect(screen.queryByRole('alert')).toBeNull()
    expect(screen.queryByRole('button', { name: 'Try again' })).toBeNull()
    second.answer(new Response(JSON.stringify({ ...DEFAULT_SETTINGS, school_name: 'Example Primary School' })))
    await waitFor(() => expect(get(settings)?.school_name).toBe('Example Primary School'))
    await waitFor(() => expect(screen.queryByRole('alert')).toBeNull())
    expect(fetchMock.mock.calls.map((c) => JSON.parse(c[1].body))).toEqual([
      { school_name: 'Exampel School' },
      { school_name: 'Example Primary School' },
    ])
    expect(school).toHaveValue('Example Primary School')
  })

  it('an older edit that fails after a newer one was made leaves no failure behind', async () => {
    settings.set({ ...DEFAULT_SETTINGS })
    let fail!: (e: Error) => void
    fetchMock
      .mockImplementationOnce(() => new Promise((_r, reject) => (fail = reject)))
      .mockImplementation((_u: string, init: RequestInit) => reply(echo(init)))
    render(SettingsPage)
    await typeSchool('Exampel School') // in flight
    await typeSchool('Example Primary School') // queued behind it
    fail(new TypeError('Failed to fetch'))
    await waitFor(() => expect(get(settings)?.school_name).toBe('Example Primary School'))
    expect(screen.queryByRole('alert')).toBeNull()
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('fills the school name when a failed first load is retried', async () => {
    vi.useFakeTimers()
    try {
      fetchMock
        .mockImplementationOnce(() => reply({ detail: 'down' }, 500))
        .mockImplementation(() => reply({ ...DEFAULT_SETTINGS, school_name: 'Example Primary School' }))
      render(SettingsPage)
      await vi.advanceTimersByTimeAsync(0)
      const school = screen.getByRole('textbox', { name: 'School name' })
      expect(school).toHaveValue('') // the defaults, while the load is retried
      await vi.advanceTimersByTimeAsync(4000)
      expect(school).toHaveValue('Example Primary School')
    } finally {
      vi.useRealTimers()
    }
  })

  it("Marks shown repeats the paper panel's caveat about section headers", async () => {
    settings.set({ ...DEFAULT_SETTINGS })
    render(SettingsPage)
    expect(screen.getByRole('combobox', { name: 'Marks shown' })).toHaveAccessibleDescription(
      /multiple-choice and short-answer sections show marks in the section header/,
    )
  })
})

describe('ClassicOff', () => {
  it('offers to turn the Classic generator on', async () => {
    settings.set({ ...DEFAULT_SETTINGS })
    fetchMock.mockImplementation(() => reply({ ...DEFAULT_SETTINGS, classic_generator: true }))
    render(ClassicOff)
    await fireEvent.click(screen.getByRole('button', { name: 'Turn on the Classic generator' }))
    await waitFor(() => expect(get(settings)?.classic_generator).toBe(true))
  })

  it('a failed load falls back to the defaults and retries once', async () => {
    vi.useFakeTimers()
    const { loadSettings } = await import('./settings')
    fetchMock.mockImplementationOnce(() => reply({ detail: 'down' }, 500)).mockImplementation(() => reply({ ...DEFAULT_SETTINGS, classic_generator: true }))
    await loadSettings(1000)
    expect(get(settings)).toEqual({ ...DEFAULT_SETTINGS })
    await vi.advanceTimersByTimeAsync(1000)
    expect(get(settings)).toEqual({ ...DEFAULT_SETTINGS, classic_generator: true })
    vi.useRealTimers()
  })

  it('settings are forgotten when nobody is signed in', async () => {
    const { session } = await import('./session')
    settings.set({ ...DEFAULT_SETTINGS, classic_generator: true })
    session.set({ status: 'anon' })
    expect(get(settings)).toBeNull()
  })
})

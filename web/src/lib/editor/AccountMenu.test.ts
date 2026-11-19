import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/svelte'
import { get } from 'svelte/store'
import AccountMenu from './AccountMenu.svelte'
import { session } from '../session'

const fetchMock = vi.fn()
beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
  session.set({ status: 'user', user: { id: 'u1', email: 'ann@example.com', name: 'Ann Lim', dev: false } })
})
afterEach(() => vi.unstubAllGlobals())

const openMenu = async () => {
  await fireEvent.click(screen.getByRole('button', { name: 'Account: Ann Lim' }))
  return screen.getByRole('menu')
}

describe('AccountMenu', () => {
  it('is an avatar with initials that opens a menu naming who is signed in', async () => {
    render(AccountMenu)
    const avatar = screen.getByRole('button', { name: 'Account: Ann Lim' })
    expect(avatar).toHaveTextContent('AL')
    expect(avatar).toHaveAttribute('aria-haspopup', 'menu')
    await openMenu()
    expect(screen.getByText('ann@example.com')).toBeInTheDocument()
    const names = screen.getAllByRole('menuitem').map((m) => m.textContent?.trim())
    expect(names).toEqual(['Settings', 'Download my data', 'Sign out', 'Delete my account…'])
  })

  it('offers only Settings to the development stub', async () => {
    session.set({ status: 'user', user: { id: 'local', email: null, name: 'Local', dev: true } })
    render(AccountMenu)
    await fireEvent.click(screen.getByRole('button', { name: 'Account: Local' }))
    expect(screen.getAllByRole('menuitem').map((m) => m.textContent?.trim())).toEqual(['Settings'])
  })

  it('downloads the data zip from the API', async () => {
    const click = vi.fn()
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(click)
    URL.createObjectURL = vi.fn(() => 'blob:x')
    URL.revokeObjectURL = vi.fn()
    fetchMock.mockResolvedValue({ ok: true, status: 200, blob: async () => new Blob(['zip']) })
    render(AccountMenu)
    await openMenu()
    await fireEvent.click(screen.getByRole('menuitem', { name: 'Download my data' }))
    expect(fetchMock).toHaveBeenCalledWith(expect.stringMatching(/\/account\/export$/), expect.anything())
    await vi.waitFor(() => expect(click).toHaveBeenCalled())
  })

  it('ignores a second download while one is being prepared, and says it is working', async () => {
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    URL.createObjectURL = vi.fn(() => 'blob:x')
    URL.revokeObjectURL = vi.fn()
    let finish: (v: unknown) => void = () => {}
    fetchMock.mockReturnValue(new Promise((r) => (finish = r)))
    render(AccountMenu)
    await openMenu()
    await fireEvent.click(screen.getByRole('menuitem', { name: 'Download my data' }))
    await openMenu()
    const item = screen.getByRole('menuitem', { name: 'Preparing download…' })
    expect(item).toHaveAttribute('aria-disabled', 'true')
    await fireEvent.click(item)
    expect(fetchMock).toHaveBeenCalledTimes(1)
    finish({ ok: true, status: 200, blob: async () => new Blob(['zip']) })
    // the menu is still open: the item comes back once the zip is ready
    await vi.waitFor(() =>
      expect(screen.getByRole('menuitem', { name: 'Download my data' })).not.toHaveAttribute('aria-disabled'),
    )
  })

  it('deletes only after DELETE is typed, then drops the session', async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 204 })
    render(AccountMenu)
    await openMenu()
    await fireEvent.click(screen.getByRole('menuitem', { name: /Delete my account/ }))
    expect(screen.getByRole('alertdialog', { name: 'Delete your account?' })).toBeInTheDocument()
    const confirm = screen.getByRole('button', { name: 'Delete everything' })
    expect(confirm).toBeDisabled()
    await fireEvent.input(screen.getByLabelText(/to confirm/), { target: { value: 'delete' } })
    expect(confirm).toBeDisabled()
    await fireEvent.input(screen.getByLabelText(/to confirm/), { target: { value: 'DELETE' } })
    await fireEvent.click(confirm)
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toMatch(/\/account$/)
    expect(init.method).toBe('DELETE')
    expect(JSON.parse(init.body)).toEqual({ confirm: 'DELETE' })
    expect(get(session).status).toBe('anon')
  })

  it('keeps the session and says so when deletion fails', async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 500 })
    render(AccountMenu)
    await openMenu()
    await fireEvent.click(screen.getByRole('menuitem', { name: /Delete my account/ }))
    await fireEvent.input(screen.getByLabelText(/to confirm/), { target: { value: 'DELETE' } })
    await fireEvent.click(screen.getByRole('button', { name: 'Delete everything' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Nothing was changed')
    expect(get(session).status).toBe('user')
  })

  it('cancelling the confirmation closes it without calling the API', async () => {
    render(AccountMenu)
    await openMenu()
    await fireEvent.click(screen.getByRole('menuitem', { name: /Delete my account/ }))
    await fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(screen.queryByRole('alertdialog')).toBeNull()
    expect(fetchMock).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Account: Ann Lim' })).toHaveFocus()
  })

  it('the delete dialog is modal: focus starts in the field, Tab stays inside, Esc backs out', async () => {
    render(AccountMenu)
    await openMenu()
    await fireEvent.click(screen.getByRole('menuitem', { name: /Delete my account/ }))
    const dialog = screen.getByRole('alertdialog', { name: 'Delete your account?' })
    const field = screen.getByLabelText(/to confirm/)
    expect(field).toHaveFocus()
    // the confirm button is disabled until DELETE is typed, so Tab goes field -> Cancel -> field
    await fireEvent.keyDown(dialog, { key: 'Tab' })
    expect(screen.getByRole('button', { name: 'Cancel' })).toHaveFocus()
    await fireEvent.keyDown(dialog, { key: 'Tab' })
    expect(field).toHaveFocus()
    await fireEvent.input(field, { target: { value: 'DELETE' } })
    await fireEvent.keyDown(dialog, { key: 'Tab', shiftKey: true })
    expect(screen.getByRole('button', { name: 'Cancel' })).toHaveFocus()
    await fireEvent.keyDown(dialog, { key: 'Tab', shiftKey: true })
    expect(screen.getByRole('button', { name: 'Delete everything' })).toHaveFocus()
    await fireEvent.keyDown(dialog, { key: 'Escape' })
    expect(screen.queryByRole('alertdialog')).toBeNull()
    expect(screen.getByRole('button', { name: 'Account: Ann Lim' })).toHaveFocus()
    expect(fetchMock).not.toHaveBeenCalled()
  })
})

import { describe, it, expect, beforeEach } from 'vitest'
import { fireEvent, render, screen, within } from '@testing-library/svelte'
import AppHeader from './AppHeader.svelte'
import { session } from './session'
import { DEFAULT_SETTINGS, settings } from './settings'

beforeEach(() => {
  session.set({ status: 'user', user: { id: 'u1', email: 'ann@example.com', name: 'Ann Tan', dev: false } })
  settings.set({ ...DEFAULT_SETTINGS })
  globalThis.location.hash = '#/'
})

const nav = () => screen.getByRole('navigation', { name: 'Main' })
const tabs = () => within(nav()).getAllByRole('link').map((a) => a.textContent)
const go = async (hash: string) => {
  globalThis.location.hash = hash
  await fireEvent(window, new HashChangeEvent('hashchange'))
}

describe('AppHeader (EXA-167)', () => {
  it('names the product and links Papers and the Question bank', () => {
    render(AppHeader)
    expect(screen.getByRole('banner')).toHaveTextContent('Exam papers')
    expect(tabs()).toEqual(['Papers', 'Question bank'])
    expect(within(nav()).getByRole('link', { name: 'Papers' })).toHaveAttribute('href', '#/')
    expect(within(nav()).getByRole('link', { name: 'Question bank' })).toHaveAttribute('href', '#/bank')
  })

  it('marks the current place with aria-current, following the route', async () => {
    render(AppHeader)
    expect(within(nav()).getByRole('link', { name: 'Papers' })).toHaveAttribute('aria-current', 'page')
    expect(within(nav()).getByRole('link', { name: 'Question bank' })).not.toHaveAttribute('aria-current')
    await go('#/bank')
    expect(within(nav()).getByRole('link', { name: 'Question bank' })).toHaveAttribute('aria-current', 'page')
    expect(within(nav()).getByRole('link', { name: 'Papers' })).not.toHaveAttribute('aria-current')
    // Settings lives in the avatar menu, not a tab: nothing is current there
    await go('#/settings')
    expect(nav().querySelector('[aria-current]')).toBeNull()
  })

  it('shows the Classic tab only while that setting is on', async () => {
    render(AppHeader)
    expect(tabs()).not.toContain('Classic')
    settings.set({ ...DEFAULT_SETTINGS, classic_generator: true })
    expect(await within(nav()).findByRole('link', { name: 'Classic' })).toHaveAttribute('href', '#/classic')
    await go('#/classic')
    expect(within(nav()).getByRole('link', { name: 'Classic' })).toHaveAttribute('aria-current', 'page')
    settings.set({ ...DEFAULT_SETTINGS, classic_generator: false })
    await Promise.resolve()
    expect(tabs()).toEqual(['Papers', 'Question bank'])
  })

  it('has the avatar menu with Settings and Sign out', async () => {
    render(AppHeader)
    await fireEvent.click(screen.getByRole('button', { name: 'Account: Ann Tan' }))
    expect(screen.getByRole('menuitem', { name: 'Sign out' })).toBeInTheDocument()
    await fireEvent.click(screen.getByRole('menuitem', { name: 'Settings' }))
    expect(globalThis.location.hash).toBe('#/settings')
  })
})

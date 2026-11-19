import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/svelte'
import EditorPage from './EditorPage.svelte'
import { makeQuestion } from './fixtures'
import { questionNode } from './templatedQuestion'
import { closeMathEditor } from './mathEditor'

// EXA-163: the Paper / Insert / View / Help menus, the command palette, the shortcut sheet,
// the global shortcuts and the side panel toggle, driven through the real docsApi with fetch
// stubbed per URL.

type Reply = { status?: number; body?: unknown }
let routes: Array<[RegExp, string, (init: RequestInit) => Reply | Promise<Reply>]> = []
const fetchMock = vi.fn(async (url: string, init: RequestInit = {}) => {
  const method = init.method ?? 'GET'
  const hit = routes.find(([re, m]) => re.test(url) && m === method)
  const reply = hit ? await hit[2](init) : { status: 404, body: { detail: 'not found' } }
  const status = reply.status ?? 200
  return { ok: status < 400, status, json: async () => reply.body, text: async () => (typeof reply.body === 'string' ? reply.body : ''), blob: async () => new Blob(['%PDF']) }
})

const record = (content: unknown[], over: object = {}) => ({
  id: 'd1',
  title: 'Ratio Review',
  total_marks: 3,
  version: 4,
  created_at: '2026-10-08T00:00:00Z',
  updated_at: '2026-10-08T00:00:00Z',
  folder_id: null,
  document: { schema_version: '1.0.0', title: 'Ratio Review', content: { type: 'doc', content } },
  ...over,
})

function serve(content: unknown[] = [{ type: 'paragraph', content: [{ type: 'text', text: 'Hello' }] }], over = {}) {
  routes = [
    [/\/documents\/d1$/, 'GET', () => ({ body: record(content, over) })],
    [/\/documents\/d1$/, 'PUT', () => ({ body: record(content, { version: 5 }) })],
    [/\/folders$/, 'GET', () => ({ body: { folders: [{ id: 'f1', name: 'P6 Prelims' }, { id: 'f2', name: 'P5 SA2' }] } })],
  ]
}

function setPlatform(platform: string) {
  Object.defineProperty(window.navigator, 'platform', { value: platform, configurable: true })
}

beforeEach(() => {
  fetchMock.mockClear()
  vi.stubGlobal('fetch', fetchMock)
  localStorage.clear()
  setPlatform('Win32')
  location.hash = '#/docs/d1'
})
afterEach(() => {
  closeMathEditor() // a store: it would outlive the page
  vi.unstubAllGlobals()
})

async function open() {
  render(EditorPage, { props: { id: 'd1' } })
  await waitFor(() => expect(document.querySelector('.page .ProseMirror')).not.toBeNull())
  return document.querySelector('.page .ProseMirror') as HTMLElement
}

const bar = () => screen.getByRole('menubar', { name: 'Paper menus' })
async function openMenu(name: string) {
  await fireEvent.click(within(bar()).getByRole('menuitem', { name }))
  return screen.getByRole('menu', { name })
}
const labels = (menu: HTMLElement) =>
  Array.from(menu.querySelectorAll('[role^="menuitem"]')).map((r) => r.querySelector('.label')?.textContent)

const key = (init: KeyboardEventInit, target: Element = document.body) =>
  fireEvent.keyDown(target, { bubbles: true, cancelable: true, ...init })

describe('the menu row (EXA-163)', () => {
  it('has Paper, Insert, View and Help with the rows in the proposal', async () => {
    serve()
    await open()
    expect(within(bar()).getAllByRole('menuitem').map((b) => b.textContent)).toEqual(['Paper', 'Insert', 'View', 'Help'])
    expect(labels(await openMenu('Paper'))).toEqual([
      'Paper settings…',
      'Cover page…',
      'Regenerate unlocked questions…',
      'Rename',
      'Move to folder…',
      'Make a copy',
      'Delete paper…',
    ])
    await key({ key: 'Escape' }, screen.getByRole('menu', { name: 'Paper' }))
    expect(labels(await openMenu('Insert'))).toEqual([
      'Question…',
      'Section',
      'Cover page',
      'Blank or rough-work page',
      'Page break',
      'Image…',
      'Equation',
    ])
    await key({ key: 'Escape' }, screen.getByRole('menu', { name: 'Insert' }))
    expect(labels(await openMenu('View'))).toEqual(['Paper', 'Answer key', 'Preview pages', 'Show side panel'])
    await key({ key: 'Escape' }, screen.getByRole('menu', { name: 'View' }))
    expect(labels(await openMenu('Help'))).toEqual(['Keyboard shortcuts', 'What “verified” means'])
  })

  it('shows each shortcut in its row with aria-keyshortcuts', async () => {
    serve()
    await open()
    const insert = await openMenu('Insert')
    const q = within(insert).getByRole('menuitem', { name: /Question…/ })
    expect(q).toHaveTextContent('Ctrl+Enter')
    expect(q).toHaveAttribute('aria-keyshortcuts', 'Control+Enter')
    await key({ key: 'Escape' }, insert)
    const view = await openMenu('View')
    // Paper and Answer key say which view is on (EXA-162)
    expect(within(view).getByRole('menuitemcheckbox', { name: 'Paper' })).toHaveAttribute('aria-checked', 'true')
    const answerKey = within(view).getByRole('menuitemcheckbox', { name: /Answer key/ })
    expect(answerKey).toHaveAttribute('aria-keyshortcuts', 'Control+Alt+K')
    expect(answerKey).toHaveAttribute('aria-checked', 'false')
    const panel = within(view).getByRole('menuitemcheckbox', { name: /Show side panel/ })
    expect(panel).toHaveAttribute('aria-checked', 'true')
    expect(panel).toHaveTextContent('Ctrl+\\')
  })

  it('is a menubar: one Tab stop, ←/→ move between names, and between open menus', async () => {
    serve()
    await open()
    const names = within(bar()).getAllByRole('menuitem')
    expect(names.map((n) => n.getAttribute('tabindex'))).toEqual(['0', '-1', '-1', '-1'])
    names[0].focus()
    await key({ key: 'ArrowRight' }, names[0])
    expect(document.activeElement).toBe(names[1])
    await key({ key: 'ArrowLeft' }, names[1])
    await key({ key: 'ArrowLeft' }, names[0])
    expect(document.activeElement).toBe(names[3]) // wraps to Help
    // open Insert, then → opens View with its first row focused
    await fireEvent.click(names[1])
    const insert = screen.getByRole('menu', { name: 'Insert' })
    await key({ key: 'ArrowRight' }, insert)
    await waitFor(() => expect(screen.getByRole('menu', { name: 'View' })).toBeInTheDocument())
    expect(screen.queryByRole('menu', { name: 'Insert' })).toBeNull()
    expect(document.activeElement).toHaveTextContent('Paper')
    expect(names[2]).toHaveAttribute('tabindex', '0')
    await key({ key: 'Escape' }, screen.getByRole('menu', { name: 'View' }))
    expect(document.activeElement).toBe(names[2])
  })

  it('Home and End go to the first and last menu name', async () => {
    serve()
    await open()
    const names = within(bar()).getAllByRole('menuitem')
    names[1].focus()
    await key({ key: 'End' }, names[1])
    expect(document.activeElement).toBe(names[3])
    expect(names[3]).toHaveAttribute('tabindex', '0')
    await key({ key: 'Home' }, names[3])
    expect(document.activeElement).toBe(names[0])
    expect(names.map((n) => n.getAttribute('tabindex'))).toEqual(['0', '-1', '-1', '-1'])
  })

  it('folds into one Menu button on a narrow window', async () => {
    const was = window.innerWidth
    window.innerWidth = 800
    try {
      serve()
      await open()
      expect(screen.queryByRole('menubar')).toBeNull()
      await fireEvent.click(screen.getByRole('button', { name: 'Menu' }))
      const all = labels(screen.getByRole('menu', { name: 'Menu' }))
      expect(all).toContain('Delete paper…')
      expect(all).toContain('Page break')
      expect(all).toContain('Keyboard shortcuts')
    } finally {
      window.innerWidth = was
    }
  })

  it('Insert puts a page break, a blank page and a section in the paper', async () => {
    serve()
    const page = await open()
    page.focus()
    for (const row of ['Page break', 'Blank or rough-work page', 'Section']) {
      await fireEvent.click(within(await openMenu('Insert')).getByRole('menuitem', { name: row }))
    }
    expect(document.querySelector('.page-break-marker')).not.toBeNull()
    expect(document.querySelector('.blank-block')).not.toBeNull()
    expect(document.querySelector('.section-block')).not.toBeNull()
  })

  it('Paper > Cover page… adds a cover and puts the caret in its first field', async () => {
    serve()
    await open()
    await fireEvent.click(within(await openMenu('Paper')).getByRole('menuitem', { name: 'Cover page…' }))
    await waitFor(() => expect(document.querySelector('.cover-block')).not.toBeNull())
    await waitFor(() => expect(document.activeElement?.closest('.cover-block')).not.toBeNull())
  })
})

describe('paper actions', () => {
  it('Delete paper… confirms, deletes and goes back to the list', async () => {
    serve()
    routes.push([/\/documents\/d1$/, 'DELETE', () => ({ status: 204 })])
    await open()
    await fireEvent.click(within(await openMenu('Paper')).getByRole('menuitem', { name: 'Delete paper…' }))
    const dialog = screen.getByRole('alertdialog')
    expect(dialog).toHaveTextContent('“Ratio Review” and its answer key are deleted')
    expect(fetchMock.mock.calls.some(([, i]) => i?.method === 'DELETE')).toBe(false)
    await fireEvent.click(within(dialog).getByRole('button', { name: 'Delete paper' }))
    await waitFor(() => expect(location.hash).toBe('#/'))
    expect(fetchMock.mock.calls.some(([u, i]) => /\/documents\/d1$/.test(u) && i?.method === 'DELETE')).toBe(true)
  })

  it('Delete paper… can be cancelled', async () => {
    serve()
    await open()
    await fireEvent.click(within(await openMenu('Paper')).getByRole('menuitem', { name: 'Delete paper…' }))
    await fireEvent.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Cancel' }))
    expect(screen.queryByRole('alertdialog')).toBeNull()
    expect(location.hash).toBe('#/docs/d1')
  })

  it('Make a copy creates a paper in the same folder with this content and opens it', async () => {
    serve(undefined, { folder_id: 'f1' })
    let created: Record<string, unknown> = {}
    let saved: { document: { title: string; content: { content: Array<{ type: string }> } }; base_version: number } | null = null
    routes.push(
      [/\/documents$/, 'POST', (init) => {
        created = JSON.parse(String(init.body))
        return { status: 201, body: record([], { id: 'd2', version: 1 }) }
      }],
      [/\/documents\/d2$/, 'PUT', (init) => {
        saved = JSON.parse(String(init.body))
        return { body: record([], { id: 'd2', version: 2 }) }
      }],
    )
    const page = await open()
    page.focus()
    // an edit the autosave has not sent yet goes into the copy too
    await fireEvent.click(within(await openMenu('Insert')).getByRole('menuitem', { name: 'Page break' }))
    expect(fetchMock.mock.calls.some(([u, i]) => /\/documents\/d1$/.test(u) && i?.method === 'PUT')).toBe(false)
    await fireEvent.click(within(await openMenu('Paper')).getByRole('menuitem', { name: 'Make a copy' }))
    await waitFor(() => expect(location.hash).toBe('#/docs/d2'))
    expect(created).toMatchObject({ title: 'Copy of Ratio Review', folder_id: 'f1' })
    expect(saved!.base_version).toBe(1)
    expect(saved!.document.title).toBe('Copy of Ratio Review')
    const types = saved!.document.content.content.map((n) => n.type)
    expect(types).toContain('paragraph')
    expect(types).toContain('pageBreak')
  })

  it('Make a copy takes the empty copy away again when its content could not be saved', async () => {
    serve()
    const deleted: string[] = []
    routes.push(
      [/\/documents$/, 'POST', () => ({ status: 201, body: record([], { id: 'd2', version: 1 }) })],
      [/\/documents\/d2$/, 'PUT', () => ({ status: 500, body: { detail: 'Disk full' } })],
      [/\/documents\/d2$/, 'DELETE', () => {
        deleted.push('d2')
        return { status: 204 }
      }],
    )
    await open()
    await fireEvent.click(within(await openMenu('Paper')).getByRole('menuitem', { name: 'Make a copy' }))
    await waitFor(() => expect(deleted).toEqual(['d2']))
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent("Couldn't make a copy. Something went wrong on our side.")
    expect(location.hash).toBe('#/docs/d1')
  })

  it("a copy whose reply was lost offers no Try again (it may exist) and says to check Your papers", async () => {
    serve()
    let posts = 0
    routes.push([/\/documents$/, 'POST', () => {
      posts += 1
      return { status: 502, body: { detail: 'Bad Gateway' } }
    }])
    await open()
    await fireEvent.click(within(await openMenu('Paper')).getByRole('menuitem', { name: 'Make a copy' }))
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent("Couldn't make a copy. Something went wrong on our side. Check Your papers before trying again.")
    expect(within(alert).queryByRole('button', { name: 'Try again' })).toBeNull()
    expect(posts).toBe(1)
  })

  it('Move to folder… and Delete paper… wait while an export runs', async () => {
    serve()
    let finish: (r: Reply) => void = () => {}
    routes.push(
      [/\/documents\/d1\/export\/student$/, 'POST', () => new Promise<Reply>((r) => (finish = r))],
      [/\/auth\/quota$/, 'GET', () => ({ body: { per_day: 30, left_day: 4 } })],
    )
    vi.stubGlobal('URL', Object.assign(URL, { createObjectURL: () => 'blob:x', revokeObjectURL: () => {} }))
    await open()
    await fireEvent.click(screen.getByRole('button', { name: /Export/ }))
    await fireEvent.click(await screen.findByRole('menuitem', { name: 'Student paper (PDF)' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([u]) => /\/export\/student$/.test(u))).toBe(true))
    const paper = await openMenu('Paper')
    for (const row of ['Move to folder…', 'Delete paper…']) {
      const item = within(paper).getByRole('menuitem', { name: row })
      expect(item).toHaveAttribute('aria-disabled', 'true')
      await fireEvent.click(item)
    }
    expect(screen.queryByRole('dialog', { name: 'Move to folder' })).toBeNull()
    expect(screen.queryByRole('alertdialog')).toBeNull()
    finish({ status: 200 })
    await waitFor(async () => {
      const again = screen.queryByRole('menu', { name: 'Paper' }) ?? (await openMenu('Paper'))
      expect(within(again).getByRole('menuitem', { name: 'Delete paper…' })).not.toHaveAttribute('aria-disabled')
    })
  })

  it('Move to folder… files the paper and the header shows the folder', async () => {
    serve()
    let moved: unknown = null
    routes.push([/\/documents\/d1$/, 'PATCH', (init) => {
      moved = JSON.parse(String(init.body))
      return { body: { id: 'd1', folder_id: 'f2' } }
    }])
    await open()
    await fireEvent.click(within(await openMenu('Paper')).getByRole('menuitem', { name: 'Move to folder…' }))
    const dialog = await screen.findByRole('dialog', { name: 'Move to folder' })
    expect(within(dialog).getByLabelText('Unfiled')).toBeChecked()
    await fireEvent.click(within(dialog).getByLabelText('P5 SA2'))
    await fireEvent.click(within(dialog).getByRole('button', { name: 'Move' }))
    await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Move to folder' })).toBeNull())
    expect(moved).toEqual({ folder_id: 'f2' })
    expect(screen.getByText('P5 SA2 /')).toBeInTheDocument()
  })
})

describe('global shortcuts', () => {
  it('Ctrl+Enter opens the question picker, also from the paper text', async () => {
    serve()
    const page = await open()
    await key({ key: 'Enter', ctrlKey: true }, page)
    expect(await screen.findByRole('dialog', { name: 'Add question' })).toBeInTheDocument()
  })

  it('never fires an insert from a form field, and leaves plain typing keys alone', async () => {
    serve()
    await open()
    const title = screen.getByLabelText('Paper title')
    const ev = new KeyboardEvent('keydown', { key: 'Enter', ctrlKey: true, bubbles: true, cancelable: true })
    title.dispatchEvent(ev)
    expect(ev.defaultPrevented).toBe(false)
    expect(screen.queryByRole('dialog', { name: 'Add question' })).toBeNull()
    for (const k of ['b', 'i', 'u', 'z', 'y', 'r', 'l', 't', 'w']) {
      const e = new KeyboardEvent('keydown', { key: k, ctrlKey: true, bubbles: true, cancelable: true })
      document.body.dispatchEvent(e)
      expect(e.defaultPrevented).toBe(false)
    }
  })

  it('Ctrl+/ opens the shortcut sheet, grouped; Esc closes it and focus comes back', async () => {
    serve()
    const page = await open()
    page.focus()
    await key({ key: '/', ctrlKey: true }, page)
    const sheet = screen.getByRole('dialog', { name: 'Keyboard shortcuts' })
    expect(within(sheet).getAllByRole('heading', { level: 3 }).map((h) => h.textContent)).toEqual(['Paper', 'Questions', 'Text'])
    expect(sheet).toHaveTextContent(/Find a command\s*Ctrl\+K/)
    expect(sheet).toHaveTextContent(/Make harder\s*\]/)
    await key({ key: 'Escape' }, document.activeElement!)
    expect(screen.queryByRole('dialog', { name: 'Keyboard shortcuts' })).toBeNull()
    expect(document.activeElement).toBe(page)
  })

  it('shows ⌘ labels and takes Cmd on a Mac (Ctrl does nothing there)', async () => {
    setPlatform('MacIntel')
    serve()
    const page = await open()
    const ctrl = new KeyboardEvent('keydown', { key: '/', ctrlKey: true, bubbles: true, cancelable: true })
    page.dispatchEvent(ctrl)
    expect(screen.queryByRole('dialog', { name: 'Keyboard shortcuts' })).toBeNull()
    await key({ key: '/', metaKey: true }, page)
    const sheet = screen.getByRole('dialog', { name: 'Keyboard shortcuts' })
    expect(sheet).toHaveTextContent(/Find a command\s*⌘K/)
    expect(sheet).toHaveTextContent(/Switch to the answer key and back\s*⌥⌘K/)
    await key({ key: 'Escape' }, document.activeElement!)
    const view = await openMenu('View')
    const k = within(view).getByRole('menuitemcheckbox', { name: /Answer key/ })
    expect(k).toHaveTextContent('⌥⌘K')
    expect(k).toHaveAttribute('aria-keyshortcuts', 'Meta+Alt+K')
  })

  it('Ctrl+P previews the paper instead of printing the screen', async () => {
    serve()
    routes.push([/\/preview\/full$/, 'GET', () => ({ body: '' })])
    const page = await open()
    const ev = new KeyboardEvent('keydown', { key: 'p', ctrlKey: true, bubbles: true, cancelable: true })
    page.dispatchEvent(ev)
    expect(ev.defaultPrevented).toBe(true)
    await waitFor(() => expect(fetchMock.mock.calls.some(([u]) => /\/preview\/full$/.test(u))).toBe(true))
  })

  it('Ctrl+Alt+K shows the answer key in place of the paper, and again goes back (EXA-162)', async () => {
    serve()
    routes.push([/\/preview\/key$/, 'GET', () => ({ body: '<p>KEY</p>' })])
    const page = await open()
    page.focus()
    await key({ key: 'k', code: 'KeyK', ctrlKey: true, altKey: true }, page)
    const keyView = screen.getByRole('region', { name: 'Answer key' })
    await waitFor(() => expect(document.activeElement).toBe(keyView))
    expect(screen.getByRole('button', { name: 'Answer key' })).toHaveAttribute('aria-pressed', 'true')
    expect(page.closest('.page')).toHaveClass('hidden')
    await key({ key: 'k', code: 'KeyK', ctrlKey: true, altKey: true }, keyView)
    await waitFor(() => expect(page.contains(document.activeElement)).toBe(true))
    expect(page.closest('.page')).not.toHaveClass('hidden')
    expect(keyView.parentElement).toHaveClass('hidden')
  })

  it('adding from the key view shows the paper first: + Question, + Section, Ctrl+Enter (review of #242)', async () => {
    serve()
    routes.push([/\/preview\/key$/, 'GET', () => ({ body: '<p>KEY</p>' })])
    const page = await open()
    const toKey = async () => {
      await fireEvent.click(screen.getByRole('button', { name: 'Answer key' }))
      await waitFor(() => expect(page.closest('.page')).toHaveClass('hidden'))
    }
    await toKey()
    await fireEvent.click(screen.getByRole('button', { name: 'Question' }))
    await waitFor(() => expect(page.closest('.page')).not.toHaveClass('hidden'))
    expect(screen.getByRole('button', { name: 'Paper' })).toHaveAttribute('aria-pressed', 'true')
    expect(await screen.findByRole('dialog', { name: 'Add question' })).toBeInTheDocument()
    await key({ key: 'Escape' }, screen.getByRole('dialog', { name: 'Add question' }))
    await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Add question' })).toBeNull())

    await toKey()
    await key({ key: 'Enter', ctrlKey: true }, screen.getByRole('region', { name: 'Answer key' }))
    await waitFor(() => expect(page.closest('.page')).not.toHaveClass('hidden'))
    expect(await screen.findByRole('dialog', { name: 'Add question' })).toBeInTheDocument()
    await key({ key: 'Escape' }, screen.getByRole('dialog', { name: 'Add question' }))
    await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Add question' })).toBeNull())

    await toKey()
    await fireEvent.click(screen.getByRole('button', { name: 'Section' }))
    await waitFor(() => expect(page.closest('.page')).not.toHaveClass('hidden'))
    await waitFor(() => expect(page.querySelector('.section-block')).not.toBeNull())
  })

  it('a press inside the printed key closes an open menu, as anywhere else on the page (review of #242)', async () => {
    serve([
      { type: 'freeformQuestion', attrs: { block_id: 'ff1', marks: 1 }, content: [{ type: 'paragraph', content: [{ type: 'text', text: 'Q' }] }] },
    ])
    routes.push([/\/preview\/key$/, 'GET', () => ({ body: '<p>KEY</p>' })])
    await open()
    await fireEvent.click(screen.getByRole('button', { name: 'Answer key' }))
    const frame = await waitFor(() => {
      const f = document.querySelector<HTMLIFrameElement>('.keyview iframe.ready')
      expect(f).not.toBeNull()
      return f!
    })
    await openMenu('Insert')
    frame.contentDocument!.body.dispatchEvent(new Event('pointerdown', { bubbles: true }))
    await waitFor(() => expect(screen.queryByRole('menu', { name: 'Insert' })).toBeNull())
  })

  it('Ctrl+M opens the equation editor only with the caret in text', async () => {
    serve()
    const page = await open()
    page.focus()
    await key({ key: 'm', ctrlKey: true }, page)
    const eq = await screen.findByRole('dialog', { name: 'Equation' })
    await fireEvent.click(within(eq).getByRole('button', { name: 'Cancel' }))
  })
})

describe('the side panel toggle', () => {
  it('Ctrl+\\ hides the panel, the page takes the full width, and the choice is remembered', async () => {
    serve()
    const page = await open()
    expect(screen.getByRole('complementary', { name: 'Side panel' })).toBeInTheDocument()
    await key({ key: '\\', ctrlKey: true }, page)
    expect(screen.queryByRole('complementary', { name: 'Side panel' })).toBeNull()
    expect(document.querySelector('.desk')).toHaveClass('nopanel')
    expect(localStorage.getItem('exam.editor.sidePanel')).toBe('hidden')
    const view = await openMenu('View')
    expect(within(view).getByRole('menuitemcheckbox', { name: /Show side panel/ })).toHaveAttribute('aria-checked', 'false')
  })

  it('opens hidden when the viewer hid it last time, and shows again from the menu', async () => {
    localStorage.setItem('exam.editor.sidePanel', 'hidden')
    serve()
    await open()
    expect(screen.queryByRole('complementary', { name: 'Side panel' })).toBeNull()
    await fireEvent.click(within(await openMenu('View')).getByRole('menuitemcheckbox', { name: /Show side panel/ }))
    expect(screen.getByRole('complementary', { name: 'Side panel' })).toBeInTheDocument()
    expect(localStorage.getItem('exam.editor.sidePanel')).toBe('shown')
  })

  it('works when storage is blocked', async () => {
    const get = vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    const set = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    try {
      serve()
      const page = await open()
      expect(screen.getByRole('complementary', { name: 'Side panel' })).toBeInTheDocument()
      await key({ key: '\\', ctrlKey: true }, page)
      expect(screen.queryByRole('complementary', { name: 'Side panel' })).toBeNull()
    } finally {
      get.mockRestore()
      set.mockRestore()
    }
  })

  it('Paper settings… shows a hidden panel on its Paper tab', async () => {
    localStorage.setItem('exam.editor.sidePanel', 'hidden')
    serve()
    await open()
    await fireEvent.click(within(await openMenu('Paper')).getByRole('menuitem', { name: 'Paper settings…' }))
    await waitFor(() => expect(document.activeElement).toBe(screen.getByRole('tab', { name: 'Paper' })))
  })
})

describe('the command palette (Ctrl+K)', () => {
  it('keeps Tab on controls you can see: the hidden × is not a stop', async () => {
    serve()
    const page = await open()
    page.focus()
    await key({ key: 'k', ctrlKey: true }, page)
    const box = screen.getByRole('combobox', { name: 'Find a command' })
    const dialog = box.closest('[role="dialog"]') as HTMLElement
    for (const shiftKey of [false, true]) {
      box.focus()
      const ev = new KeyboardEvent('keydown', { key: 'Tab', shiftKey, bubbles: true, cancelable: true })
      box.dispatchEvent(ev)
      // the only visible stop is the field itself: Tab wraps back to it
      expect(ev.defaultPrevented).toBe(true)
      expect(document.activeElement).toBe(box)
    }
    expect(within(dialog).queryByRole('button', { name: 'Close', hidden: true })).toBeNull()
  })

  it('lists the menu rows with their shortcuts, filters as you type and runs on Enter', async () => {
    serve()
    const page = await open()
    page.focus()
    await key({ key: 'k', ctrlKey: true }, page)
    const box = screen.getByRole('combobox', { name: 'Find a command' })
    expect(document.activeElement).toBe(box)
    const list = screen.getByRole('listbox', { name: 'Commands' })
    const all = within(list).getAllByRole('option')
    expect(all.some((o) => /Keyboard shortcuts.*Ctrl\+\//.test(o.textContent ?? ''))).toBe(true)
    // a disabled row (no generated questions to regenerate) is left out
    expect(all.some((o) => /Regenerate/.test(o.textContent ?? ''))).toBe(false)
    await fireEvent.input(box, { target: { value: 'short' } })
    const opts = within(list).getAllByRole('option')
    expect(opts[0]).toHaveTextContent('Keyboard shortcuts')
    expect(box).toHaveAttribute('aria-activedescendant', opts[0].id)
    expect(opts[0]).toHaveAttribute('aria-selected', 'true')
    await key({ key: 'Enter' }, box)
    expect(await screen.findByRole('dialog', { name: 'Keyboard shortcuts' })).toBeInTheDocument()
    expect(screen.queryByRole('combobox', { name: 'Find a command' })).toBeNull()
  })

  it('moves with the arrows, says when nothing matches and gives focus back on Esc', async () => {
    serve()
    const page = await open()
    page.focus()
    await key({ key: 'k', ctrlKey: true }, page)
    const box = screen.getByRole('combobox', { name: 'Find a command' })
    await fireEvent.input(box, { target: { value: 'page' } })
    const opts = within(screen.getByRole('listbox')).getAllByRole('option')
    expect(opts.length).toBeGreaterThan(1)
    await key({ key: 'ArrowDown' }, box)
    expect(box).toHaveAttribute('aria-activedescendant', opts[1].id)
    await key({ key: 'ArrowUp' }, box)
    await key({ key: 'ArrowUp' }, box)
    expect(box).toHaveAttribute('aria-activedescendant', opts[opts.length - 1].id)
    await fireEvent.input(box, { target: { value: 'zzzz' } })
    expect(screen.getByText('No command matches “zzzz”.')).toBeInTheDocument()
    await key({ key: 'Escape' }, box)
    expect(screen.queryByRole('combobox', { name: 'Find a command' })).toBeNull()
    expect(document.activeElement).toBe(page)
  })

  it("lists the selected question's actions by name and runs them", async () => {
    serve([questionNode(makeQuestion({ id: 'a' }, 'Share the sweets.'))])
    routes.push([/\/edit\/make-harder$/, 'POST', () => ({ body: { question: makeQuestion({ id: 'h', blueprint_code: 'ratio_hard' }, 'A harder one.') } })])
    await open()
    const block = (await screen.findByText('Share the sweets.')).closest('.qblock') as HTMLElement
    await fireEvent.click(block)
    block.focus()
    await key({ key: 'k', ctrlKey: true }, block)
    const box = screen.getByRole('combobox', { name: 'Find a command' })
    await fireEvent.input(box, { target: { value: 'harder' } })
    const opts = within(screen.getByRole('listbox')).getAllByRole('option')
    expect(opts).toHaveLength(1)
    expect(opts[0]).toHaveTextContent('Make harder Question 1 ]')
    await key({ key: 'Enter' }, box)
    await waitFor(() => expect(fetchMock.mock.calls.some(([u]) => /\/edit\/make-harder$/.test(u))).toBe(true))
    expect(await screen.findByText('A harder one.')).toBeInTheDocument()
  })

  it('hides the question actions when no question is selected', async () => {
    serve([questionNode(makeQuestion({ id: 'a' }, 'Share the sweets.'))])
    const page = await open()
    await key({ key: 'k', ctrlKey: true }, page)
    await fireEvent.input(screen.getByRole('combobox', { name: 'Find a command' }), { target: { value: 'harder' } })
    expect(within(screen.getByRole('listbox')).queryAllByRole('option')).toHaveLength(0)
  })
})

describe('leaving the editor', () => {
  it('takes its shortcuts with it: after unmount, Ctrl+K does nothing', async () => {
    serve()
    const { unmount } = render(EditorPage, { props: { id: 'd1' } })
    await waitFor(() => expect(document.querySelector('.page .ProseMirror')).not.toBeNull())
    unmount()
    const ev = new KeyboardEvent('keydown', { key: 'k', ctrlKey: true, bubbles: true, cancelable: true })
    document.body.dispatchEvent(ev)
    expect(ev.defaultPrevented).toBe(false)
    expect(screen.queryByRole('combobox', { name: 'Find a command' })).toBeNull()
  })
})

describe('Help', () => {
  it('What “verified” means explains it in plain words', async () => {
    serve()
    await open()
    await fireEvent.click(within(await openMenu('Help')).getByRole('menuitem', { name: 'What “verified” means' }))
    const d = screen.getByRole('dialog', { name: 'What “verified” means' })
    expect(d).toHaveTextContent('The answer in the key is the solution to exactly the question on the paper')
    await fireEvent.click(within(d).getByRole('button', { name: 'Close' }))
    expect(screen.queryByRole('dialog')).toBeNull()
  })
})

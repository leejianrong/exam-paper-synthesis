// EXA-164: a section is a compact header and the cover a compact card on the page; their settings
// edit in the side panel, and the paper and every section share one "Marks shown" control.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/svelte'
import { Editor } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import { NodeSelection } from '@tiptap/pm/state'
import EditorPage from './EditorPage.svelte'
import SidePanel from './SidePanel.svelte'
import MarksShown from './MarksShown.svelte'
import { Section, outline, sectionCues, sectionMarksNote, sectionNode, titlePrints } from './sections'
import { questionNode } from './templatedQuestion'
import { makeQuestion } from './fixtures'
import type { Editor as TipTap } from '@tiptap/core'
import { BlockSelectionGuard } from './blockSelection'
import { CoverPage, coverNode } from './pages'
import { selectedSettingsBlock, settingsBlockPos, settingsTransaction, type SettingsBlock } from './blockSettings'
import { freeformDocNode } from './fixtures'
import { paperSettings } from './paperSettings'
import { closeMathEditor } from './mathEditor'

const para = (text: string) => ({ type: 'paragraph', content: [{ type: 'text', text }] })
const options = (select: HTMLElement) =>
  Array.from((select as HTMLSelectElement).options).map((o) => [o.value, o.text])

describe('the section header on the page', () => {
  let editor: Editor | null = null
  afterEach(() => {
    editor?.destroy()
    editor = null
    outline.set([])
    document.body.innerHTML = ''
  })

  function make(onEdit: ((pos: number) => void) | null = null) {
    const element = document.createElement('div')
    document.body.append(element)
    editor = new Editor({
      element,
      extensions: [StarterKit, Section.configure({ onEdit }), CoverPage, BlockSelectionGuard],
      content: {
        type: 'doc',
        content: [
          para('intro'),
          sectionNode('Section A', { mode: 'mcq', marks_target: 10 }),
          sectionNode('', { mode: 'structured', instructions: 'Show your working.' }),
        ],
      },
    })
    return { element, editor }
  }

  it('shows the title, derived range and marks, and cues; no form', () => {
    const { element } = make()
    outline.set([
      { first: 1, last: 5, count: 5, marks: 8, target: 10 },
      { first: 6, last: 6, count: 1, marks: 4, target: null },
    ])
    const [a, b] = Array.from(element.querySelectorAll('.section-block'))
    expect(a.querySelectorAll('input, select, textarea')).toHaveLength(0)
    expect(a.querySelector('.section-title')).toHaveTextContent('Section A')
    expect(a.querySelector('.section-summary')).toHaveTextContent('Questions 1–5 · 8 / 10 marks')
    expect(a.querySelector('.section-summary')).toHaveAttribute('data-state', 'under')
    expect(a.querySelector('.section-cues')).toHaveTextContent('Multiple choice')
    expect(a.querySelector('.section-instructions')).toHaveProperty('hidden', true)
    expect(b.querySelector('.section-title')).toHaveTextContent('Untitled section')
    expect(b.querySelector('.section-summary')).toHaveTextContent('Question 6 · 4 marks')
    expect(b.querySelector('.section-cues')).toHaveTextContent('Structured · marking margin')
    expect(b.querySelector('.section-instructions')).toHaveTextContent('Show your working.')
  })

  it('follows attribute changes made elsewhere (the side panel)', () => {
    const { element, editor } = make()
    const pos = settingsBlockPos(editor.state.doc, { kind: 'section', index: 0, attrs: {} })!
    editor.view.dispatch(settingsTransaction(editor.state, pos, { title: 'Fractions', mode: 'short', marking: false }))
    const a = element.querySelector('.section-block')!
    expect(a.querySelector('.section-title')).toHaveTextContent('Fractions')
    expect(a.querySelector('.section-cues')).toHaveTextContent(/^Short answer$/)
  })

  it('Edit and Alt+Enter on the selected section open its settings at its position', () => {
    const opened: number[] = []
    const { element, editor } = make((pos) => opened.push(pos))
    const second = element.querySelectorAll('.section-block')[1]
    second.querySelector<HTMLButtonElement>('button[aria-label="Edit section settings"]')!.click()
    const pos = settingsBlockPos(editor.state.doc, { kind: 'section', index: 1, attrs: {} })
    expect(opened).toEqual([pos])
    editor.commands.setNodeSelection(pos!)
    const before = editor.state.doc.childCount
    editor.view.dom.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', altKey: true, bubbles: true }))
    expect(opened).toEqual([pos, pos])
    expect(editor.state.doc.childCount).toBe(before) // not the block guard's "Enter types after it"

    // Alt+Enter with text selected does nothing of the kind
    editor.commands.setTextSelection(2)
    editor.view.dom.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', altKey: true, bubbles: true }))
    expect(opened).toHaveLength(2)
  })

  it('cues: the mode and the marking margin as it will print', () => {
    expect(sectionCues({ mode: null })).toBe('')
    expect(sectionCues({ mode: null, marking: true })).toBe('marking margin')
    expect(sectionCues({ mode: 'short' })).toBe('Short answer · marking margin')
    expect(sectionCues({ title: 'Booklet B', mode: 'mcq' })).toBe('title not printed · Multiple choice')
    expect(sectionCues({ title: 'Section A2' })).toBe('')
  })

  it('a generic title shows faint, as it does not print (EXA-139)', () => {
    const element = document.createElement('div')
    document.body.append(element)
    editor = new Editor({
      element,
      extensions: [StarterKit, Section],
      content: { type: 'doc', content: [sectionNode('Section A'), sectionNode('Fractions')] },
    })
    const [generic, own] = Array.from(element.querySelectorAll('.section-title'))
    expect(generic).toHaveClass('untitled')
    expect(element.querySelector('.section-cues')).toHaveTextContent('title not printed')
    expect(own).not.toHaveClass('untitled')
    expect(titlePrints(' booklet 2 ')).toBe(false)
    expect(titlePrints('Part One')).toBe(true)
  })
})

describe('the selected section or cover (blockSettings)', () => {
  let editor: Editor
  beforeEach(() => {
    editor = new Editor({
      extensions: [StarterKit, Section, CoverPage],
      content: { type: 'doc', content: [coverNode({ school: 'Example Primary' }), sectionNode('A'), para('x'), sectionNode('B')] },
    })
  })
  afterEach(() => editor.destroy())

  it('names the cover, or the section by its place, and nothing else', () => {
    editor.commands.setNodeSelection(0)
    expect(selectedSettingsBlock(editor.state)).toMatchObject({ kind: 'cover', attrs: { school: 'Example Primary' } })
    const b = settingsBlockPos(editor.state.doc, { kind: 'section', index: 1, attrs: {} })!
    editor.commands.setNodeSelection(b)
    expect(selectedSettingsBlock(editor.state)).toMatchObject({ kind: 'section', index: 1, attrs: { title: 'B' } })
    editor.commands.setTextSelection(b - 2)
    expect(selectedSettingsBlock(editor.state)).toBeNull()
    expect(settingsBlockPos(editor.state.doc, { kind: 'section', index: 2, attrs: {} })).toBeNull()
  })

  it('a change keeps the block selected, so the panel stays on it', () => {
    const block: SettingsBlock = { kind: 'section', index: 0, attrs: {} }
    const pos = settingsBlockPos(editor.state.doc, block)!
    editor.view.dispatch(settingsTransaction(editor.state, pos, { marks_target: 20 }))
    expect(editor.state.selection).toBeInstanceOf(NodeSelection)
    expect(selectedSettingsBlock(editor.state)).toMatchObject({ kind: 'section', index: 0, attrs: { title: 'A', marks_target: 20 } })
  })
})

describe('Marks shown: one control for the paper and each section', () => {
  it('the paper has three choices', () => {
    render(MarksShown, { props: { value: 'answer' } })
    expect(options(screen.getByRole('combobox'))).toEqual([
      ['answer', 'After the Ans: line'],
      ['question', 'Beside each question'],
      ['both', 'Both'],
    ])
  })

  it('a section adds its default, which follows the paper, and the section header', async () => {
    const view = render(MarksShown, { props: { value: '', section: true, mode: 'structured' } })
    expect(options(screen.getByRole('combobox'))).toEqual([
      ['', 'Same as the paper'],
      ['answer', 'After the Ans: line'],
      ['question', 'Beside each question'],
      ['both', 'Both'],
      ['none', 'In the section header'],
    ])
    expect(screen.getByRole('combobox')).toHaveValue('')
    await view.rerender({ value: 'question', section: true, mode: 'mcq' })
    expect(options(screen.getByRole('combobox'))[0]).toEqual(['', 'Multiple choice default'])
    expect(screen.getByRole('combobox')).toHaveValue('question')
  })

  it("the section's note says what its choice comes to, against the paper's", () => {
    expect(sectionMarksNote({ mode: 'structured' }, 'both')).toBe('Follows the paper: both.')
    expect(sectionMarksNote({ mode: 'short' }, 'answer')).toBe('Short answer keeps marks in the section header unless you choose.')
    expect(sectionMarksNote({ mode: 'mcq', marks_placement: 'answer' }, 'question')).toBe(
      "Chosen for this section. The paper's: beside each question.",
    )
  })
})

describe('SidePanel: Paper / Question / Section / Cover', () => {
  const section = (attrs: Record<string, unknown> = {}, index = 1): SettingsBlock => ({
    kind: 'section',
    index,
    attrs: { title: 'Section B', instructions: null, mode: null, marks_target: 40, marking: null, marks_placement: null, ...attrs },
  })
  afterEach(() => {
    paperSettings.set({})
    outline.set([])
  })

  it('a selected section brings its tab forward, named by its title, with its figures', async () => {
    outline.set([
      { first: 1, last: 15, count: 15, marks: 20, target: 20 },
      { first: 16, last: 30, count: 15, marks: 40, target: 40 },
    ])
    const view = render(SidePanel, { props: { blocks: [freeformDocNode({ id: 'ff_1', marks: 2 })], context: null } })
    expect(screen.getByRole('tab', { name: 'Paper' })).toHaveAttribute('aria-selected', 'true')
    await view.rerender({ context: section() })
    expect(screen.getByRole('tab', { name: 'Section B' })).toHaveAttribute('aria-selected', 'true')
    const panel = screen.getByRole('tabpanel', { name: 'Section B' })
    expect(panel).toHaveTextContent('Questions 16–30 · 40 / 40 marks')
    expect(within(panel).getByLabelText('Title')).toHaveValue('Section B')
    expect(within(panel).getByLabelText('Marks target')).toHaveValue(40)
    // an untitled section is named by its place
    await view.rerender({ context: section({ title: '' }) })
    expect(screen.getByRole('tab', { name: 'Section 2' })).toBeInTheDocument()
    // then the cover, then back to a question
    await view.rerender({ context: { kind: 'cover', attrs: { school: 'Example Primary' } } })
    expect(screen.getByRole('tab', { name: 'Cover page' })).toHaveAttribute('aria-selected', 'true')
    expect(within(screen.getByRole('tabpanel', { name: 'Cover page' })).getByLabelText('School')).toHaveValue('Example Primary')
    await view.rerender({ context: null, selectedId: 'ff_1' })
    expect(screen.getByRole('tab', { name: 'Question 1' })).toHaveAttribute('aria-selected', 'true')
  })

  it('every section field goes back as the attrs to set', async () => {
    paperSettings.set({ marks_placement: 'question' })
    const seen: Array<Record<string, unknown>> = []
    render(SidePanel, { props: { context: section() }, events: { blockattrs: (e: CustomEvent) => seen.push(e.detail) } })
    const panel = screen.getByRole('tabpanel', { name: 'Section B' })
    await fireEvent.input(within(panel).getByLabelText('Title'), { target: { value: 'Booklet B' } })
    await fireEvent.input(within(panel).getByLabelText('Instructions'), { target: { value: 'Show your working.' } })
    await fireEvent.change(within(panel).getByLabelText('Mode'), { target: { value: 'short' } })
    await fireEvent.change(within(panel).getByLabelText('Mode'), { target: { value: '' } })
    await fireEvent.input(within(panel).getByLabelText('Marks target'), { target: { value: '999' } })
    await fireEvent.input(within(panel).getByLabelText('Marks target'), { target: { value: '' } })
    const shown = within(panel).getByLabelText('Marks shown')
    expect(options(shown)[0]).toEqual(['', 'Same as the paper'])
    expect(shown).toHaveAccessibleDescription('Follows the paper: beside each question.')
    await fireEvent.change(shown, { target: { value: 'none' } })
    await fireEvent.change(shown, { target: { value: '' } })
    const margin = within(panel).getByLabelText('Marking margin') as HTMLInputElement
    expect(margin.checked).toBe(false) // no mode: off unless chosen
    await fireEvent.click(margin)
    expect(seen).toEqual([
      { title: 'Booklet B' },
      { instructions: 'Show your working.' },
      { mode: 'short' },
      { mode: null },
      { marks_target: 500 },
      { marks_target: null },
      { marks_placement: 'none' },
      { marks_placement: null },
      { marking: true },
    ])
  })

  it('every cover field goes back as the attrs to set', async () => {
    const seen: Array<Record<string, unknown>> = []
    render(SidePanel, {
      props: { context: { kind: 'cover', attrs: { subject: 'Mathematics', even_pages: true } } },
      events: { blockattrs: (e: CustomEvent) => seen.push(e.detail) },
    })
    const panel = screen.getByRole('tabpanel', { name: 'Cover page' })
    for (const [label, value] of [['School', 'Example Primary'], ['Exam', 'Prelim'], ['Level', 'Primary 6'], ['Subject', 'Maths'], ['Paper', 'Paper 1'], ['Date', '']]) {
      await fireEvent.input(within(panel).getByLabelText(label), { target: { value } })
    }
    await fireEvent.input(within(panel).getByLabelText('Instructions'), { target: { value: 'Answer all.' } })
    const table = within(panel).getByLabelText("For examiner's use table") as HTMLInputElement
    expect(table.checked).toBe(true)
    await fireEvent.click(table)
    expect(within(panel).getByLabelText('Pad to an even number of pages')).toBeChecked()
    await fireEvent.click(within(panel).getByLabelText("Parent's signature line"))
    expect(seen).toEqual([
      { school: 'Example Primary' },
      { exam: 'Prelim' },
      { level: 'Primary 6' },
      { subject: 'Maths' },
      { paper: 'Paper 1' },
      { date: null },
      { instructions: 'Answer all.' },
      { examiner_table: false },
      { parent_signature: true },
    ])
  })

  it('only a new selection brings the tab forward, not the section moving to another place', async () => {
    const view = render(SidePanel, { props: { context: null, pick: 0 } })
    await view.rerender({ context: section(), pick: 1 })
    expect(screen.getByRole('tab', { name: 'Section B' })).toHaveAttribute('aria-selected', 'true')
    await fireEvent.click(screen.getByRole('tab', { name: 'Paper' }))
    // a section inserted above (or removed, or undone) shifts its place: same selection
    await view.rerender({ context: section({}, 2), pick: 1 })
    await view.rerender({ context: section({}, 0), pick: 1 })
    expect(screen.getByRole('tab', { name: 'Paper' })).toHaveAttribute('aria-selected', 'true')
    // selecting it again does
    await view.rerender({ context: section({}, 0), pick: 2 })
    expect(screen.getByRole('tab', { name: 'Section B' })).toHaveAttribute('aria-selected', 'true')
  })

  it('while a swap or regenerate runs, the settings are disabled', async () => {
    const view = render(SidePanel, { props: { context: section(), pick: 1, locked: true } })
    expect(screen.getByRole('group')).toBeDisabled()
    expect(screen.getByLabelText('Title')).toBeDisabled()
    await view.rerender({ context: { kind: 'cover', attrs: {} }, pick: 2, locked: true })
    expect(screen.getByLabelText('School')).toBeDisabled()
    await view.rerender({ locked: false })
    expect(screen.getByLabelText('School')).toBeEnabled()
  })

  it('the paper says sections follow it, but multiple choice and short answer use the header', () => {
    render(SidePanel, { props: {} })
    expect(screen.getByRole('tabpanel', { name: 'Paper' })).toHaveTextContent(
      'Sections follow this unless they set their own; multiple-choice and short-answer sections show marks in the section header.',
    )
  })

  it('Escape in the settings hands back to the page', async () => {
    const done = vi.fn()
    render(SidePanel, { props: { context: section() }, events: { done } })
    await fireEvent.keyDown(screen.getByLabelText('Title'), { key: 'Escape' })
    expect(done).toHaveBeenCalledOnce()
  })
})

describe('in the editor', () => {
  const fetchMock = vi.fn()
  const content = [
    coverNode({ school: 'Example Primary', exam: 'Prelim' }),
    sectionNode('Section A', { marks_target: 2 }),
    freeformDocNode({ id: 'ff_1', marks: 2 }),
  ]
  const record = {
    id: 'd1',
    title: 'Ratio Review',
    total_marks: 2,
    version: 4,
    created_at: '2026-10-08T00:00:00Z',
    updated_at: '2026-10-08T00:00:00Z',
    folder_id: null,
    document: { schema_version: '1.10.0', title: 'Ratio Review', content: { type: 'doc', content } },
  }
  beforeEach(() => {
    localStorage.clear()
    fetchMock.mockReset()
    fetchMock.mockImplementation(async (url: string, init: RequestInit = {}) => ({
      ok: true,
      status: 200,
      json: async () => (init.method === 'PUT' ? { ...record, version: 5 } : /\/folders$/.test(url) ? { folders: [] } : record),
      text: async () => '',
    }))
    vi.stubGlobal('fetch', fetchMock)
  })
  afterEach(() => {
    closeMathEditor()
    vi.unstubAllGlobals()
    vi.useRealTimers()
  })

  async function open() {
    render(EditorPage, { props: { id: 'd1' } })
    await waitFor(() => expect(document.querySelector('.section-block .section-summary')).toHaveTextContent('Question 1 · 2 / 2 marks'))
  }

  it("a section's Edit opens its settings; a change shows on the header and is saved", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    await open()
    await fireEvent.click(screen.getByRole('button', { name: 'Edit section settings' }))
    const panel = screen.getByRole('tabpanel', { name: 'Section A' })
    const title = within(panel).getByLabelText('Title')
    await waitFor(() => expect(title).toHaveFocus())
    expect(document.querySelector('.section-block')).toHaveClass('ProseMirror-selectednode')

    await fireEvent.input(title, { target: { value: 'Booklet B' } })
    await fireEvent.input(within(panel).getByLabelText('Marks target'), { target: { value: '5' } })
    await waitFor(() => expect(document.querySelector('.section-title')).toHaveTextContent('Booklet B'))
    expect(document.querySelector('.section-summary')).toHaveTextContent('Question 1 · 2 / 5 marks')
    // the tab follows the new title, and focus stays in the field being typed in
    expect(screen.getByRole('tab', { name: 'Booklet B' })).toHaveAttribute('aria-selected', 'true')
    expect(title).toHaveFocus()

    await vi.advanceTimersByTimeAsync(1500)
    const put = fetchMock.mock.calls.filter((c) => c[1]?.method === 'PUT').at(-1)
    const saved = JSON.parse(put![1].body).document.content.content[1]
    expect(saved).toEqual({ type: 'section', attrs: { title: 'Booklet B', marks_target: 5 } })
  })

  it('a section inserted above the selected one leaves the panel on the Paper tab', async () => {
    await open()
    await fireEvent.click(screen.getByRole('button', { name: 'Edit section settings' }))
    await waitFor(() => expect(screen.getByRole('tab', { name: 'Section A' })).toHaveAttribute('aria-selected', 'true'))
    await fireEvent.click(screen.getByRole('tab', { name: 'Paper' }))
    const ed = (document.querySelector('.page .ProseMirror') as HTMLElement & { editor: TipTap }).editor
    const at = ed.state.doc.child(0).nodeSize // after the cover, above Section A
    ed.view.dispatch(ed.state.tr.insert(at, ed.schema.nodeFromJSON(sectionNode('New'))))
    await waitFor(() => expect(document.querySelectorAll('.section-block')).toHaveLength(2))
    expect(screen.getByRole('tab', { name: 'Paper' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('tab', { name: 'Section A' })).toBeInTheDocument() // still Section A
    ed.commands.undo()
    await waitFor(() => expect(document.querySelectorAll('.section-block')).toHaveLength(1))
    expect(screen.getByRole('tab', { name: 'Paper' })).toHaveAttribute('aria-selected', 'true')
  })

  it('while Regenerate runs, the section settings are disabled and an edit is not applied', async () => {
    let finish: () => void = () => {}
    const withQ = [...content, questionNode(makeQuestion())]
    const rec = { ...record, document: { ...record.document, content: { type: 'doc', content: withQ } } }
    fetchMock.mockImplementation(async (url: string, init: RequestInit = {}) => {
      if (/\/regenerate$/.test(url)) {
        await new Promise<void>((r) => (finish = r))
        return { ok: false, status: 409, json: async () => ({ detail: 'stale' }), text: async () => '' }
      }
      return { ok: true, status: 200, json: async () => (init.method === 'PUT' ? { ...rec, version: 5 } : /\/folders$/.test(url) ? { folders: [] } : rec), text: async () => '' }
    })
    render(EditorPage, { props: { id: 'd1' } })
    await waitFor(() => expect(document.querySelector('.section-block')).not.toBeNull())
    await fireEvent.click(screen.getByRole('button', { name: 'Edit section settings' }))
    const title = await screen.findByLabelText('Title')
    await fireEvent.click(screen.getByRole('tab', { name: 'Paper' }))
    await fireEvent.click(screen.getByRole('button', { name: /^Regenerate 1 unlocked/ }))
    await fireEvent.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Regenerate' }))
    await waitFor(() => expect(fetchMock.mock.calls.some(([u]) => /\/regenerate$/.test(String(u)))).toBe(true))
    await fireEvent.click(screen.getByRole('tab', { name: 'Section A' }))
    expect(title).toBeDisabled()
    await fireEvent.input(title, { target: { value: 'Lost' } }) // a script or a stale event
    expect(document.querySelector('.section-title')).toHaveTextContent('Section A')
    finish()
    await waitFor(() => expect(title).toBeEnabled())
  })

  it('the cover card edits in the panel; a hidden panel is shown for it', async () => {

    localStorage.setItem('exam.editor.sidePanel', 'hidden')
    await open()
    expect(screen.queryByRole('complementary', { name: 'Side panel' })).toBeNull()
    expect(document.querySelector('.cover-block')).toHaveTextContent('Example Primary')
    await fireEvent.click(screen.getByRole('button', { name: 'Edit cover page' }))
    const panel = await screen.findByRole('tabpanel', { name: 'Cover page' })
    await waitFor(() => expect(within(panel).getByLabelText('School')).toHaveFocus())
    await fireEvent.input(within(panel).getByLabelText('Level'), { target: { value: 'Primary 6' } })
    await waitFor(() => expect(document.querySelector('.cover-block')).toHaveTextContent('Primary 6 · Mathematics'))
    // Escape goes back to the page with the cover still selected
    await fireEvent.keyDown(within(panel).getByLabelText('Level'), { key: 'Escape' })
    await waitFor(() => expect(document.activeElement).toBe(document.querySelector('.page .ProseMirror')))
    expect(document.querySelector('.cover-block')).toHaveClass('ProseMirror-selectednode')
  })
})

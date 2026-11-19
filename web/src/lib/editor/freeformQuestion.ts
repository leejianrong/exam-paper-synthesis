// The `freeformQuestion` TipTap node (W2a, ADR-0021): a question the teacher types straight
// onto the page. Unlike the templated atom its body is editable content (paragraphs and
// lists); `marks` and the written `answer` live in node attributes — the answer is edited in
// the Edit answer dialog (its ⋯ menu, or its row in the answer key view), not on the page. Its
// controls (marks, parts, move, delete) are the shared question bar (EXA-161), which never
// prints; `[n]` shows on the page as it prints.

import { Node } from '@tiptap/core'
import { Plugin } from '@tiptap/pm/state'
import type { NodeViewRendererProps } from '@tiptap/core'
import { EMPTY_ANSWER } from './doc'
import { locateBlock, moveBlock } from './templatedQuestion'
import { closeHistory } from '@tiptap/pm/history'
import { FreeformPart, MAX_PARTS, PART_NODE, jsonAttr, partLetter } from './freeformPart'
import { hasContent } from './paperReport'
import { mount, unmount } from 'svelte'
import { writable } from 'svelte/store'
import FreeformArea from './FreeformArea.svelte'
import { layoutOf, marksBeside } from './layout'
import { trackPlacement } from './sections'
import type { SwapMode } from './docsApi'
import FreeformBar from './FreeformBar.svelte'
import LockBadge from './LockBadge.svelte'
import { NOWHERE, trackPlace } from './blockPlace'
import { blockLabel, type QuestionAction, type QuestionFacts } from './questionMenu'

export interface FreeformQuestionOptions {
  onAddBelow: (afterPos: number) => void
  /** P8d: fill a generated placeholder with a question (the page saves first). */
  onSwap: (blockId: string, mode: SwapMode) => Promise<void>
  /** The question was deleted from its menu or with Del (EXA-161: the page offers Undo). */
  onDeleted: () => void
  /** Its menu's "Edit answer…": the page opens the answer for the key (EXA-162). */
  onEditAnswer: (blockId: string) => void
}

function el<K extends keyof HTMLElementTagNameMap>(tag: K, cls: string, text?: string) {
  const e = document.createElement(tag)
  e.className = cls
  if (text !== undefined) e.textContent = text
  return e
}

export const FreeformQuestion = Node.create<FreeformQuestionOptions>({
  name: 'freeformQuestion',
  // Its own group (not `block`) so a free-form question can only sit at the top level.
  group: 'question',
  // The body, then optionally the lettered parts (P3).
  content: '(paragraph | bulletList | orderedList | image)+ freeformPart*',
  isolating: true,
  defining: true,
  draggable: false,

  // The lettered parts are part of this node's vocabulary: anything that registers a
  // free-form question gets them.
  addExtensions() {
    return [FreeformPart]
  },

  addOptions() {
    return { onAddBelow: () => {}, onSwap: async () => {}, onDeleted: () => {}, onEditAnswer: () => {} }
  },

  addAttributes() {
    return {
      block_id: { default: null },
      marks: jsonAttr<number | null>('data-marks', null),
      answer: jsonAttr('data-answer', EMPTY_ANSWER),
      remark: { default: null }, // the author's private note (inspector); never printed
      space_mm: jsonAttr<number | null>('data-space_mm', null), // blank working space (mm)
      in_key: jsonAttr<boolean>('data-in_key', true), // false leaves it out of the answer key (P5)
      ans_unit: jsonAttr<string | null>('data-ans_unit', null), // unit printed after Ans:
      slot: jsonAttr<Record<string, unknown> | null>('data-slot', null), // generator slot (P8a)
      locked: jsonAttr<boolean>('data-locked', false), // P8d: kept by "Regenerate unlocked"
    }
  },

  parseHTML() {
    return [{ tag: 'div[data-freeform-question]' }]
  },

  renderHTML({ HTMLAttributes }) {
    return ['div', { 'data-freeform-question': '', ...HTMLAttributes }, 0]
  },

  addProseMirrorPlugins() {
    // A pasted question with more than MAX_PARTS parts would save fine in the editor and be
    // refused by the server; refuse it here instead.
    return [
      new Plugin({
        filterTransaction: (tr) => {
          if (!tr.docChanged) return true
          let ok = true
          tr.doc.forEach((n) => {
            if (n.type.name !== this.name) return
            let parts = 0
            n.forEach((c) => {
              if (c.type.name === PART_NODE) parts++
            })
            if (parts > MAX_PARTS) ok = false
          })
          return ok
        },
      }),
    ]
  },

  addKeyboardShortcuts() {
    return {
      // Leave the block: a new paragraph after it, caret in it.
      'Mod-Enter': ({ editor }) => {
        const { $from } = editor.state.selection
        for (let d = $from.depth; d > 0; d--) {
          if ($from.node(d).type.name === this.name) {
            const after = $from.after(d)
            return editor
              .chain()
              .insertContentAt(after, { type: 'paragraph' })
              .setTextSelection(after + 1)
              .run()
          }
        }
        return false
      },
    }
  },

  addNodeView() {
    const options = this.options
    return ({ node, getPos, editor }: NodeViewRendererProps) => {
      let current = node
      /** The block's position now; null once it has gone (then a control does nothing). */
      const pos = (): number | null => locateBlock(editor, getPos, current)?.pos ?? null

      const dom = el('div', 'qblock ffblock')
      dom.setAttribute('data-block-id', String(node.attrs.block_id))
      // One group per question (EXA-161). Not focusable itself: the caret in its text selects it
      // (a tabindex here would take focus away from the editor while typing).
      dom.setAttribute('role', 'group')
      const num = el('div', 'ff-num')
      num.setAttribute('contenteditable', 'false')
      const badgeHost = el('span', 'ff-badge')
      num.append(badgeHost)
      const badge = mount(LockBadge, { target: badgeHost })

      const main = el('div', 'ff-main')
      const row = el('div', 'ff-row')
      const contentDOM = el('div', 'ff-body')
      const marksEl = el('span', 'ff-marks')
      marksEl.setAttribute('contenteditable', 'false')
      row.append(contentDOM, marksEl)

      // A generated paper's placeholder (P8a): says what to write until the body has text.
      const hint = el('p', 'ff-placeholder-hint')
      hint.setAttribute('contenteditable', 'false')

      // The block's controls (QuestionBar): nothing at rest, a pill when selected.
      const barHost = el('div', 'qbar-host')
      barHost.setAttribute('contenteditable', 'false')

      const parts = () => {
        const out: Array<{ marks: number }> = []
        current.forEach((c) => {
          if (c.type.name === PART_NODE) out.push({ marks: (c.attrs.marks as number | null) ?? 0 })
        })
        return out
      }
      // Adding the first part moves the marks onto the parts: one undoable step.
      function addPart() {
        const from = pos()
        if (from === null || parts().length >= MAX_PARTS) return
        const { tr, schema } = editor.state
        const at = from + current.nodeSize - 1 // the end of the question's content
        // The first part takes over the question's marks and written answer (nothing is lost);
        // later parts start at one mark.
        const first = parts().length === 0
        const part = schema.nodes[PART_NODE].create(
          first
            ? { marks: current.attrs.marks ?? 1, answer: current.attrs.answer }
            : { marks: 1 },
          [schema.nodes.paragraph.create()],
        )
        tr.insert(at, part)
        if (first) {
          tr.setNodeMarkup(from, undefined, { ...current.attrs, marks: null, answer: EMPTY_ANSWER })
        }
        editor.view.dispatch(tr)
        // Caret into the new part, focused *now*: TipTap's focus() waits a frame, and keys typed
        // meanwhile went to this button (a space "clicked" it again, adding stray parts).
        editor.chain().setTextSelection(at + 2).scrollIntoView().run()
        editor.view.focus()
      }

      const areaHost = el('div', 'ff-area')
      areaHost.setAttribute('contenteditable', 'false')
      main.append(hint, row, areaHost)
      dom.append(num, main, barHost)

      const setLayout = (patch: Record<string, unknown>) => {
        const from = pos()
        if (from === null) return
        const { tr } = editor.state
        tr.setNodeMarkup(from, undefined, { ...current.attrs, ...patch })
        editor.view.dispatch(tr)
      }
      // The [n] follow the section the question sits in (EXA-152); live as sections change.
      let ready = false
      const tracker = trackPlacement(editor, getPos, () => {
        if (!ready) return
        sync()
        areaState.set(areaProps())
      })
      const areaState = writable(areaProps())
      const area = mount(FreeformArea, {
        target: areaHost,
        props: {
          state: { subscribe: areaState.subscribe },
          onSpace: (mm: number | null) => setLayout({ space_mm: mm }),
          onUnit: (u: string) => setLayout({ ans_unit: u }),
        },
      })
      const place = { current: NOWHERE }
      let swapping = false // a fill is out: the block's controls wait for it
      const barState = writable(barProps())
      const bar = mount(FreeformBar, {
        target: barHost,
        props: {
          host: dom,
          state: { subscribe: barState.subscribe },
          onAction: (a: QuestionAction) => act(a),
          onMarks: (marks: number | null) => setLayout({ marks }),
        },
      })
      const stopPlace = trackPlace(editor, getPos, (p) => {
        place.current = p
        if (ready) sync()
      })

      function slotOf() {
        return current.attrs.slot as { kind?: string; placeholder?: boolean } | null
      }
      function waiting() {
        // Same rule as the "to write" count: anything in the stem or a part means it's written.
        return !!slotOf()?.placeholder && !hasContent(current.toJSON().content)
      }
      function facts(): QuestionFacts {
        const locked = current.attrs.locked === true && waiting()
        return {
          kind: waiting() ? 'placeholder' : 'own',
          locked,
          // Only an empty placeholder is refilled by "Regenerate unlocked"; once written in it is
          // yours and kept anyway, so a lock means nothing there.
          lockable: waiting(),
          inKey: current.attrs.in_key !== false,
          ops: [],
          canEditNames: false,
          // a structured placeholder is written as lettered parts, so it can take them too
          canAddPart: parts().length < MAX_PARTS,
          canMoveUp: place.current.canMoveUp,
          canMoveDown: place.current.canMoveDown,
        }
      }
      function barProps() {
        const ps = parts()
        const multi = ps.length > 0
        return {
          facts: facts(),
          number: place.current.number,
          selected: place.current.selected,
          busy: swapping,
          marks: (current.attrs.marks as number | null) ?? null,
          showMarks: !multi && !waiting(),
          summary: multi
            ? `${ps.length} part${ps.length === 1 ? '' : 's'} · ${ps.reduce((n, p) => n + p.marks, 0)} marks`
            : '',
        }
      }
      function swap(mode: SwapMode) {
        if (swapping) return
        swapping = true
        barState.set(barProps())
        void options.onSwap(String(current.attrs.block_id), mode).finally(() => {
          swapping = false
          barState.set(barProps())
        })
      }
      function act(action: QuestionAction) {
        const from = pos()
        if (from === null) return
        switch (action) {
          case 'fill':
          case 'like':
            return swap('like')
          case 'topic':
            return swap('topic')
          case 'addPart':
            return addPart()
          case 'lock':
            return setLayout({ locked: current.attrs.locked !== true })
          case 'key':
            return setLayout({ in_key: current.attrs.in_key === false })
          case 'answer':
            return options.onEditAnswer(String(current.attrs.block_id))
          case 'up':
          case 'down':
            moveBlock(editor, from, current.nodeSize, action === 'up' ? -1 : 1)
            return
          case 'addBelow':
            return options.onAddBelow(from + current.nodeSize)
          case 'delete':
            // its own undo step: the toast's Undo brings back just this question
            editor
              .chain()
              .focus()
              .command(({ tr }) => {
                closeHistory(tr)
                return true
              })
              .deleteRange({ from, to: from + current.nodeSize })
              .run()
            return options.onDeleted()
        }
      }

      function areaProps() {
        const l = layoutOf(current.attrs)
        return {
          marks: (current.attrs.marks as number | null) ?? null,
          spaceMm: l.space_mm,
          unit: l.ans_unit,
          placement: tracker.current(),
        }
      }

      const sync = () => {
        const ps = parts()
        const multi = ps.length > 0
        const slot = slotOf()
        const isWaiting = waiting()
        hint.hidden = !isWaiting
        const locked = current.attrs.locked === true
        badgeHost.hidden = !(locked && isWaiting)
        dom.classList.toggle('placeholder-slot', isWaiting)
        if (isWaiting) {
          const kind = slot?.kind === 'mcq' ? 'multiple-choice' : slot?.kind === 'structured' ? 'structured' : 'short-answer'
          const marks = multi ? ps.reduce((n, p) => n + p.marks, 0) : (current.attrs.marks as number | null)
          hint.textContent = `Placeholder: write a ${marks ? `${marks}-mark ` : ''}${kind} question here, or delete it and add one.`
        }
        dom.classList.toggle('multipart', multi)
        // With parts the marks are the parts' sum and the question has no answer area of its own.
        areaHost.hidden = multi
        marksEl.hidden = multi
        const total = multi ? ps.reduce((n, p) => n + p.marks, 0) : ((current.attrs.marks as number | null) ?? null)
        const f = facts()
        dom.setAttribute('aria-label', blockLabel(place.current.number, total, f))
        barState.set(barProps())
        // Parts are lettered by position: relabel after any change to the siblings.
        // (After ProseMirror has patched the parts' DOM, which happens once update() returns.)
        queueMicrotask(() =>
          dom.querySelectorAll('.ffp-label').forEach((n, i) => (n.textContent = `(${partLetter(i)})`)),
        )
        const marks = current.attrs.marks as number | null
        marksEl.textContent =
          marks === null || marks === undefined || !marksBeside(tracker.current()) ? '' : `[${marks}]`
      }
      sync()
      ready = true
      const unsubscribe = () => tracker.destroy()

      return {
        dom,
        contentDOM,
        update(updated) {
          if (updated.type !== node.type) return false
          current = updated
          dom.setAttribute('data-block-id', String(updated.attrs.block_id))
          sync()
          areaState.set(areaProps())
          tracker.refresh()
          return true
        },
        destroy() {
          unsubscribe()
          stopPlace()
          void unmount(area)
          void unmount(bar)
          void unmount(badge)
        },
        // Clicks and typing in the controls are ours; the body is ProseMirror's.
        stopEvent: (event) => barHost.contains(event.target as globalThis.Node),
        ignoreMutation: (m) => !contentDOM.contains(m.target),
      }
    }
  },
})

/** Insert a free-form block at `at` and put the caret in it. */
export function insertFreeform(editor: NodeViewRendererProps['editor'], at: number, node: object) {
  editor
    .chain()
    .insertContentAt(at, node)
    .setTextSelection(at + 2)
    .run()
  // Synchronous: the chain's `.focus()` defers a frame, and keystrokes typed in between
  // would land nowhere.
  editor.view.focus()
}

/** The document node, widened so free-form questions (group `question`) can sit in it. */
export const QuestionDocument = Node.create({
  name: 'doc',
  topNode: true,
  content: '(block | question | media)+',
})

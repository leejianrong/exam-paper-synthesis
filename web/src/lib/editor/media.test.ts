import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
import { Editor } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import { get } from 'svelte/store'
import { FreeformQuestion, QuestionDocument } from './freeformQuestion'
import { ImageBlock, ImageUpload, MathNode, insertBlock, uploadAndInsert } from './media'
import { mathRequest } from './mathEditor'

const ID = 'a'.repeat(32)
const meta = { id: ID, mime: 'image/png', width: 2, height: 3, bytes: 9 }
const para = (t?: string) => ({ type: 'paragraph', content: t ? [{ type: 'text', text: t }] : undefined })

let editor: Editor
const onError = vi.fn()
const upload = vi.fn()

function make(content: unknown) {
  editor = new Editor({
    element: document.body.appendChild(document.createElement('div')),
    extensions: [
      QuestionDocument,
      ImageBlock,
      MathNode,
      FreeformQuestion,
      ImageUpload.configure({ upload, onError }),
      StarterKit.configure({ document: false, trailingNode: false, codeBlock: false }),
    ],
    content: content as never,
  })
  return editor
}

beforeEach(() => {
  onError.mockReset()
  upload.mockReset()
  mathRequest.set(null)
})
afterEach(() => editor?.destroy())

describe('image node', () => {
  it('round-trips its attributes and draws the asset', () => {
    make({
      type: 'doc',
      content: [{ type: 'image', attrs: { asset_id: ID, alt: 'A bar model', width_pct: 40 } }],
    })
    const json = editor.getJSON().content![0]
    expect(json).toEqual({ type: 'image', attrs: { asset_id: ID, alt: 'A bar model', width_pct: 40 } })
    const img = document.querySelector('img.doc-image-img') as HTMLImageElement
    expect(img.src).toContain(`/assets/${ID}`)
    expect(img.alt).toBe('A bar model')
    expect(img.style.width).toBe('40%')
  })

  it('the width and description fields write back to the node', () => {
    make({ type: 'doc', content: [{ type: 'image', attrs: { asset_id: ID, alt: '', width_pct: 100 } }] })
    const width = document.querySelector('input.doc-image-width') as HTMLInputElement
    width.value = '5' // below the floor: clamped to 10
    width.dispatchEvent(new Event('change'))
    const alt = document.querySelector('input.doc-image-alt') as HTMLInputElement
    alt.value = 'Figure 1'
    alt.dispatchEvent(new Event('change'))
    expect(editor.getJSON().content![0].attrs).toMatchObject({ width_pct: 10, alt: 'Figure 1' })
  })

  it('Remove deletes the figure', () => {
    make({ type: 'doc', content: [para('keep'), { type: 'image', attrs: { asset_id: ID } }] })
    ;(document.querySelector('.doc-image-bar .danger') as HTMLButtonElement).click()
    expect(editor.getJSON().content!.map((n) => n.type)).toEqual(['paragraph'])
  })

  it('a foreign <img> (data: or blob: source) is dropped on paste, ours survives', () => {
    make({ type: 'doc', content: [para('x')] })
    editor.commands.insertContent(
      '<p>a</p><img src="data:image/png;base64,AAAA"><img src="blob:xyz"><img data-asset-id="' + ID + '" src="x">',
    )
    const images = editor.getJSON().content!.filter((n) => n.type === 'image')
    expect(images).toHaveLength(1)
    expect(images[0].attrs!.asset_id).toBe(ID)
  })
})

describe('insertBlock / uploadAndInsert', () => {
  it('inserts after the paragraph holding the caret', () => {
    make({ type: 'doc', content: [para('one'), para('two')] })
    editor.commands.setTextSelection(2)
    insertBlock(editor, { type: 'image', attrs: { asset_id: ID } })
    expect(editor.getJSON().content!.map((n) => n.type)).toEqual(['paragraph', 'image', 'paragraph'])
  })

  it('replaces an empty paragraph', () => {
    make({ type: 'doc', content: [para('one'), para()] })
    editor.commands.setTextSelection(editor.state.doc.content.size - 1)
    insertBlock(editor, { type: 'image', attrs: { asset_id: ID } })
    expect(editor.getJSON().content!.map((n) => n.type)).toEqual(['paragraph', 'image'])
  })

  it('goes after the list when the caret is in a list item (images never sit in items)', () => {
    make({
      type: 'doc',
      content: [{ type: 'bulletList', content: [{ type: 'listItem', content: [para('item')] }] }],
    })
    editor.commands.setTextSelection(3)
    insertBlock(editor, { type: 'image', attrs: { asset_id: ID } })
    expect(editor.getJSON().content!.map((n) => n.type)).toEqual(['bulletList', 'image'])
  })

  it('inside a free-form question the image joins its body', () => {
    make({
      type: 'doc',
      content: [
        {
          type: 'freeformQuestion',
          attrs: { block_id: 'ff_media_1', marks: 1, answer: { type: 'doc', content: [] } },
          content: [para('Look at the figure.')],
        },
      ],
    })
    editor.commands.setTextSelection(3)
    insertBlock(editor, { type: 'image', attrs: { asset_id: ID } })
    const body = editor.getJSON().content![0].content!
    expect(body.map((n) => n.type)).toEqual(['paragraph', 'image'])
  })

  it('uploads first, then inserts; a failure reports and inserts nothing', async () => {
    make({ type: 'doc', content: [para('x')] })
    upload.mockResolvedValueOnce(meta).mockRejectedValueOnce(new Error('Could not upload the image: too big'))
    const files = [new File(['a'], 'a.png'), new File(['b'], 'b.png')]
    await uploadAndInsert(editor, files, { upload, onError })
    expect(upload).toHaveBeenCalledTimes(2)
    expect(editor.getJSON().content!.filter((n) => n.type === 'image')).toHaveLength(1)
    expect(onError).toHaveBeenCalledWith('Could not upload the image: too big')
  })
})

describe('paste and drop', () => {
  const run = (name: 'handlePaste' | 'handleDrop', event: unknown) =>
    editor.view.someProp(name, (f) => (f as (v: unknown, e: unknown) => boolean)(editor.view, event))

  it('uploads a pasted image file and inserts it', async () => {
    make({ type: 'doc', content: [para('x')] })
    upload.mockResolvedValue(meta)
    const preventDefault = vi.fn()
    const file = new File(['png'], 'p.png', { type: 'image/png' })
    const handled = run('handlePaste', {
      preventDefault,
      clipboardData: { files: [file], getData: () => '' },
    })
    expect(handled).toBe(true)
    expect(preventDefault).toHaveBeenCalled()
    await vi.waitFor(() => expect(editor.getJSON().content!.some((n) => n.type === 'image')).toBe(true))
  })

  it('leaves a paste with text alone (Word sends a preview image beside the text)', () => {
    make({ type: 'doc', content: [para('x')] })
    const handled = run('handlePaste', {
      preventDefault: vi.fn(),
      clipboardData: {
        files: [new File(['png'], 'p.png', { type: 'image/png' })],
        getData: () => 'some text',
      },
    })
    expect(handled).toBeFalsy()
    expect(upload).not.toHaveBeenCalled()
  })

  it('ignores pasted GIFs and drops of non-images', () => {
    make({ type: 'doc', content: [para('x')] })
    expect(
      run('handlePaste', {
        preventDefault: vi.fn(),
        clipboardData: { files: [new File(['g'], 'g.gif', { type: 'image/gif' })], getData: () => '' },
      }),
    ).toBeFalsy()
    expect(run('handleDrop', { preventDefault: vi.fn(), dataTransfer: { files: [] } })).toBeFalsy()
    expect(upload).not.toHaveBeenCalled()
  })
})

describe('math node', () => {
  const mathDoc = (latex: string) => ({
    type: 'doc',
    content: [{ type: 'paragraph', content: [{ type: 'text', text: 'Find ' }, { type: 'math', attrs: { latex } }] }],
  })

  it('shows the formula and round-trips the LaTeX', () => {
    make(mathDoc('\\frac{3}{4}'))
    const host = document.querySelector('.math-node') as HTMLElement
    expect(host.shadowRoot!.textContent).toContain('\\frac{3}{4}') // raw source until KaTeX loads
    expect(editor.getJSON().content![0].content![1]).toEqual({ type: 'math', attrs: { latex: '\\frac{3}{4}' } })
  })

  it('clicking opens the equation editor, and Apply rewrites the node', () => {
    make(mathDoc('x'))
    ;(document.querySelector('.math-node') as HTMLElement).click()
    const req = get(mathRequest)!
    expect(req.latex).toBe('x')
    req.apply('x^{2}')
    expect(editor.getJSON().content![0].content![1]).toMatchObject({ attrs: { latex: 'x^{2}' } })
  })

  it('applying null (or blank) removes the formula', () => {
    make(mathDoc('x'))
    ;(document.querySelector('.math-node') as HTMLElement).click()
    get(mathRequest)!.apply(null)
    expect(editor.getJSON().content![0].content!.map((n) => n.type)).toEqual(['text'])
  })
})

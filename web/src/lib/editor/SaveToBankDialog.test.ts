import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/svelte'
import SaveToBankDialog from './SaveToBankDialog.svelte'
import { freeformDocNode } from './fixtures'
import type { DocNode } from './doc'

const fetchMock = vi.fn()
beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
})
afterEach(() => vi.unstubAllGlobals())

const TOPICS = { topics: [{ topic: 'Fractions', strand: 'Fractions' }, { topic: 'Ratio', strand: 'Ratio' }] }
const reply = (status: number, body: unknown) => ({ ok: status < 400, status, json: async () => body, headers: new Headers() })

/** GET /bank/topics, then each POST /bank/own answered from `saves` in turn. */
function stub(...saves: Array<[number, unknown]>) {
  fetchMock.mockImplementation(async (url: string) => {
    if (String(url).includes('/bank/topics')) return reply(200, TOPICS)
    const next = saves.shift()
    if (!next) throw new Error(`unexpected ${url}`)
    return reply(...next)
  })
}

const sent = (n: number) => JSON.parse(fetchMock.mock.calls.filter((c) => String(c[0]).includes('/bank/own'))[n][1].body)

function open(block: DocNode = freeformDocNode({ id: 'ff_mine', marks: 2 }), level = 'P5') {
  const onSaved = vi.fn()
  const onClose = vi.fn()
  render(SaveToBankDialog, { props: { block, level, onSaved, onClose } })
  return { onSaved, onClose }
}

async function chooseTopic(topic = 'Fractions') {
  await waitFor(() => expect(screen.getByRole('option', { name: topic })).toBeInTheDocument())
  await fireEvent.change(screen.getByLabelText('Topic'), { target: { value: topic } })
}

describe('Save to your bank (EXA-90)', () => {
  it('asks for a topic, starts at the paper level and the block marks, then saves the block', async () => {
    stub([200, { status: 'saved', id: 'own-ff_mine' }])
    const { onSaved } = open()
    const save = screen.getByRole('button', { name: 'Save' })
    expect(save).toBeDisabled() // no topic yet
    expect(screen.getByLabelText('Level')).toHaveValue('P5')
    expect(screen.getByLabelText('Marks')).toHaveValue(2)
    await chooseTopic()
    await fireEvent.change(screen.getByLabelText('Difficulty'), { target: { value: 'hard' } })
    await fireEvent.click(save)
    await waitFor(() => expect(onSaved).toHaveBeenCalledWith({ status: 'saved', id: 'own-ff_mine' }))
    const body = sent(0)
    expect(body).toMatchObject({ topic: 'Fractions', level: 'P5', difficulty: 'hard', marks: 2, replace: false })
    expect(body.block.attrs.block_id).toBe('ff_mine')
  })

  it('reports a copy already in the bank and replaces it only when asked', async () => {
    stub([409, { detail: 'This question is already in your bank.' }], [200, { status: 'replaced', id: 'own-ff_mine' }])
    const { onSaved } = open()
    await chooseTopic('Ratio')
    await fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('already in your bank')
    expect(onSaved).not.toHaveBeenCalled()
    await fireEvent.click(screen.getByRole('button', { name: 'Replace it' }))
    await waitFor(() => expect(onSaved).toHaveBeenCalledWith({ status: 'replaced', id: 'own-ff_mine' }))
    expect(sent(1).replace).toBe(true)
  })

  it("a multi-part question's marks are its parts', shown and not asked", async () => {
    stub([200, { status: 'saved', id: 'own-ffm' }])
    const part = (marks: number) => ({ type: 'freeformPart', attrs: { marks }, content: [{ type: 'paragraph' }] })
    const block = { ...freeformDocNode({ id: 'ffm', marks: null }), content: [{ type: 'paragraph', content: [{ type: 'text', text: 'A tank.' }] }, part(2), part(1)] }
    open(block, '')
    expect(screen.queryByLabelText('Marks')).toBeNull()
    expect(screen.getByText('3 marks')).toBeInTheDocument()
    expect(screen.getByLabelText('Level')).toHaveValue('P6') // no level on the paper
    await chooseTopic()
    await fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await waitFor(() => expect(sent(0).marks).toBeNull())
  })

  it('shows a failed save in plain words and keeps the dialog open', async () => {
    stub([422, { detail: 'Write the question before saving it to your bank.' }])
    const { onSaved, onClose } = open()
    await chooseTopic()
    await fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Write the question before saving it')
    expect(onSaved).not.toHaveBeenCalled()
    expect(onClose).not.toHaveBeenCalled()
  })
})

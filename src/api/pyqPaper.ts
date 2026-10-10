import type { Chapter } from '../types'
import type { GeneratedPaper } from '../generator'
import { PAPER_MARKS_OPTIONS } from '../generator'

const API_BASE = import.meta.env.VITE_PYQ_API_URL ?? ''

const STALE_API_HINT =
  'Restart the PYQ API so it includes paper generation: in scripts/pyq-llm run ' +
  '$env:PYTHONPATH="."; py -m pyq_llm.main (stop any old process on port 8787 first).'

function chaptersQuery(chapters?: Chapter[]): string {
  if (!chapters?.length) return ''
  return `&chapters=${encodeURIComponent(chapters.join(','))}`
}

export async function fetchPyqApiHealth(): Promise<{
  ok: boolean
  paperApi: boolean
  llmConfigured: boolean
} | null> {
  try {
    const res = await fetch(`${API_BASE}/health`)
    if (!res.ok) return null
    const data = (await res.json()) as {
      ok?: boolean
      paper_api?: boolean
      llm_configured?: boolean
    }
    return {
      ok: Boolean(data.ok),
      paperApi: data.paper_api === true,
      llmConfigured: Boolean(data.llm_configured),
    }
  } catch {
    return null
  }
}

export interface PyqPaperRequest {
  chapters?: Chapter[]
  targetMarks: number
  aiLevel?: number
}

export type PyqPaperProgress = { step: number; total: number; message: string }

export async function fetchPyqSpread(targetMarks: number, chapters?: Chapter[]) {
  const res = await fetch(
    `${API_BASE}/api/paper/spread?target_marks=${targetMarks}${chaptersQuery(chapters)}`,
  )
  if (!res.ok) return null
  return res.json() as Promise<{
    targetMarks: number
    spread: string
    plannedSpread?: string
    corpusNotes?: string[]
    counts: Record<string, number>
  }>
}

export async function generatePyqPaper(req: PyqPaperRequest): Promise<GeneratedPaper> {
  const res = await fetch(`${API_BASE}/api/paper/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      chapters: req.chapters?.length ? req.chapters : null,
      target_marks: req.targetMarks,
      ai_level: req.aiLevel ?? 0,
    }),
  })
  if (!res.ok) {
    if (res.status === 404) {
      throw new Error(STALE_API_HINT)
    }
    const detail = await res.text()
    throw new Error(detail || `API error ${res.status}`)
  }
  const data = await res.json()
  return data as GeneratedPaper
}

export async function generatePyqPaperStream(
  req: PyqPaperRequest,
  onProgress: (p: PyqPaperProgress) => void,
): Promise<GeneratedPaper> {
  const res = await fetch(`${API_BASE}/api/paper/generate-stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      chapters: req.chapters?.length ? req.chapters : null,
      target_marks: req.targetMarks,
      ai_level: req.aiLevel ?? 0,
    }),
  })
  if (!res.ok) {
    if (res.status === 404) {
      throw new Error(STALE_API_HINT)
    }
    const detail = await res.text()
    throw new Error(detail || `API error ${res.status}`)
  }
  if (!res.body) {
    throw new Error('No response body from paper stream')
  }
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let paper: GeneratedPaper | null = null

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''
    for (const line of lines) {
      const trimmed = line.trim()
      if (!trimmed) continue
      const evt = JSON.parse(trimmed) as {
        type: string
        step?: number
        total?: number
        message?: string
        paper?: GeneratedPaper
        detail?: string
      }
      if (evt.type === 'progress' && evt.step != null && evt.total != null) {
        onProgress({
          step: evt.step,
          total: evt.total,
          message: evt.message ?? '',
        })
      } else if (evt.type === 'complete' && evt.paper) {
        paper = evt.paper
      } else if (evt.type === 'error') {
        throw new Error(evt.detail ?? 'Paper generation failed')
      }
    }
  }

  if (!paper) {
    throw new Error('Paper stream ended without a complete paper')
  }
  return paper
}

export { PAPER_MARKS_OPTIONS }

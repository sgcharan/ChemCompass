import type { Chapter, Question } from '../types'

const API_BASE = import.meta.env.VITE_PYQ_API_URL ?? ''

export interface GeneratedMcqDto {
  id: string
  chapter: string | null
  text: string
  options: string[]
  answer: string
  explanation?: string
  sourcePyqIds?: string[]
  mode?: string
  basedOnPyqId?: string
  basedOnLabel?: string
  basedOnStem?: string
  basedOnMarkingAnswer?: string
  stemMode?: 'strict' | 'creative'
}

export type PyqStemMode = 'strict' | 'creative' | 'mix'

export interface GenerateMcqRequest {
  chapter?: Chapter | null
  count?: number
  marks?: number
  query?: string
  difficulty?: string
  /** strict = same board stem; creative = new question from PYQ topic; mix = alternate */
  stemMode?: PyqStemMode
}

export async function fetchPyqChapters(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/api/chapters`)
  if (!res.ok) return []
  return res.json()
}

export async function generatePyqMcqs(req: GenerateMcqRequest): Promise<GeneratedMcqDto[]> {
  const res = await fetch(`${API_BASE}/api/mcq/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      chapter: req.chapter ?? null,
      count: req.count ?? 5,
      marks: req.marks ?? 1,
      query: req.query,
      difficulty: req.difficulty ?? 'board',
      stem_mode: req.stemMode ?? 'strict',
    }),
  })
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(detail || `API error ${res.status}`)
  }
  return res.json()
}

export function mcqDtoToQuestion(dto: GeneratedMcqDto, chapter: Chapter): Question {
  const refId = dto.basedOnPyqId ?? dto.sourcePyqIds?.[0]
  const pyqReference =
    refId && dto.basedOnLabel
      ? {
          id: refId,
          label: dto.basedOnLabel,
          stem: dto.basedOnStem ?? dto.text,
          markingAnswer: dto.basedOnMarkingAnswer,
          generationStyle: dto.stemMode,
        }
      : refId
        ? {
            id: refId,
            label: refId,
            stem: dto.basedOnStem ?? dto.text,
            markingAnswer: dto.basedOnMarkingAnswer,
            generationStyle: dto.stemMode,
          }
        : undefined

  return {
    id: dto.id,
    source: 'pyq',
    chapter: (dto.chapter as Chapter) || chapter,
    kind: 'mcq',
    marks: 1,
    text: dto.text,
    options: dto.options,
    answer: dto.answer,
    pyqReference,
    figureNote: pyqReference
      ? undefined
      : dto.sourcePyqIds?.length
        ? `Based on PYQ: ${dto.sourcePyqIds.join(', ')}`
        : undefined,
  }
}

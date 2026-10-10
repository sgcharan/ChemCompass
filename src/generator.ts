import type { Chapter, Question, SourceId } from './types'
import { QUESTIONS } from './data'

/** Sources that contain 2–5 mark subjective items (not PYQ MCQs). */
export const BANK_SOURCE_IDS: SourceId[] = [
  'qb-xii',
  'apq-2023-24-a',
  'apq-2023-24-b',
  'apq-2022-23',
  'apq-2021-22-t2',
]

export function subjectiveSourcesForPaper(selected: SourceId[]): SourceId[] {
  const bank = selected.filter((s) => s !== 'pyq')
  return bank.length ? bank : [...BANK_SOURCE_IDS]
}

/** CBSE Class XII Chemistry theory paper at 70 marks: 16×1 + 5×2 + 7×3 + 2×4 + 3×5 */
export const CBSE_70_SPREAD = { one: 16, vsa: 5, sa: 7, case: 2, la: 3 }

export type SectionCounts = typeof CBSE_70_SPREAD

export function marksFromSectionCounts(c: SectionCounts): number {
  return c.one + c.vsa * 2 + c.sa * 3 + c.case * 4 + c.la * 5
}

export function formatSectionSpread(c: SectionCounts): string {
  const parts: string[] = []
  if (c.one) parts.push(`${c.one}×1`)
  if (c.vsa) parts.push(`${c.vsa}×2`)
  if (c.sa) parts.push(`${c.sa}×3`)
  if (c.case) parts.push(`${c.case}×4`)
  if (c.la) parts.push(`${c.la}×5`)
  return parts.join(' + ')
}

/** Scale CBSE section mix to a target total (max 70 = official spread). */
export function cbseSpreadForTotal(targetMarks: number): SectionCounts {
  const target = Math.min(70, Math.max(1, Math.round(targetMarks)))
  if (target === 70) {
    return { ...CBSE_70_SPREAD }
  }

  const ratio = target / 70
  let c: SectionCounts = {
    one: Math.max(1, Math.round(CBSE_70_SPREAD.one * ratio)),
    vsa: Math.round(CBSE_70_SPREAD.vsa * ratio),
    sa: Math.round(CBSE_70_SPREAD.sa * ratio),
    case: Math.round(CBSE_70_SPREAD.case * ratio),
    la: Math.round(CBSE_70_SPREAD.la * ratio),
  }

  const steps: { key: keyof SectionCounts; cost: number }[] = [
    { key: 'one', cost: 1 },
    { key: 'vsa', cost: 2 },
    { key: 'sa', cost: 3 },
    { key: 'case', cost: 4 },
    { key: 'la', cost: 5 },
  ]

  let m = marksFromSectionCounts(c)
  let guard = 0
  while (m < target && guard++ < 200) {
    const need = target - m
    const step =
      [...steps].reverse().find((s) => s.cost <= need) ?? steps[0]
    c[step.key] += 1
    m += step.cost
  }
  guard = 0
  while (m > target && guard++ < 200) {
    const over = m - target
    const step =
      steps.find((s) => c[s.key] > 0 && s.cost <= over) ??
      [...steps].reverse().find((s) => c[s.key] > 0)
    if (!step) break
    c[step.key] -= 1
    m -= step.cost
  }

  return c
}

export const PAPER_MARKS_OPTIONS = Array.from({ length: 14 }, (_, i) => (i + 1) * 5) as number[]

export interface GeneratorOptions {
  chapters: Chapter[]
  sources: SourceId[]
  seed: number
  /** Total marks for the paper (CBSE-style section mix, up to 70). */
  targetMarks: number
  /** Extra questions (e.g. RAG-generated PYQ MCQs) merged into the pool */
  extraQuestions?: Question[]
}

export interface PaperSection {
  title: string
  instruction: string
  items: PaperItem[]
}

export interface PaperItem {
  number: number
  marks: number
  questions: Question[]
  passage?: string
  figureNote?: string
}

export interface GeneratedPaper {
  title: string
  subtitle: string
  time: string
  maxMarks: number
  targetMarks: number
  sectionSpread: string
  generatedAt: string
  seed: number
  sections: PaperSection[]
  generalInstructions: string[]
  warnings?: string[]
}

function mulberry32(seed: number) {
  return function rand() {
    let t = (seed += 0x6d2b79f5)
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

function shuffle<T>(items: T[], rand: () => number): T[] {
  const arr = [...items]
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1))
    ;[arr[i], arr[j]] = [arr[j], arr[i]]
  }
  return arr
}

function inFilter(q: Question, chapters: Chapter[], sources: SourceId[]) {
  return chapters.includes(q.chapter) && sources.includes(q.source)
}

function pick(pool: Question[], n: number, rand: () => number, used: Set<string>) {
  const available = shuffle(
    pool.filter((q) => !used.has(q.id)),
    rand,
  )
  const chosen = available.slice(0, n)
  chosen.forEach((q) => used.add(q.id))
  return chosen
}

function pickGroups(pool: Question[], n: number, rand: () => number, used: Set<string>) {
  const groups = new Map<string, Question[]>()
  for (const q of pool) {
    if (!q.groupId || used.has(q.id)) continue
    const list = groups.get(q.groupId) ?? []
    list.push(q)
    groups.set(q.groupId, list)
  }
  const ids = shuffle([...groups.keys()], rand).slice(0, n)
  const result: Question[][] = []
  for (const id of ids) {
    const qs = groups.get(id)!
    qs.forEach((q) => used.add(q.id))
    result.push(qs)
  }
  return result
}

export function generatePaper(options: GeneratorOptions): GeneratedPaper {
  const rand = mulberry32(options.seed)
  const used = new Set<string>()
  const extra = options.extraQuestions ?? []
  const oneMarkPool = [...QUESTIONS, ...extra].filter((q) =>
    inFilter(q, options.chapters, options.sources),
  )
  const subjSources = subjectiveSourcesForPaper(options.sources)
  const subjectivePool = QUESTIONS.filter((q) =>
    inFilter(q, options.chapters, subjSources),
  )

  const oneMark = oneMarkPool.filter((q) => q.kind === 'mcq' || q.kind === 'assertion-reason')
  const vsa = subjectivePool.filter((q) => q.kind === 'vsa')
  const sa = subjectivePool.filter((q) => q.kind === 'sa')
  const cases = subjectivePool.filter((q) => q.kind === 'case' && q.marks === 4)
  const la = subjectivePool.filter(
    (q) => q.kind === 'la' || (q.kind === 'case' && q.marks === 5),
  )
  const caseMcq = subjectivePool.filter((q) => q.kind === 'case-mcq')

  const sections: PaperSection[] = []
  let n = 1

  const counts = cbseSpreadForTotal(options.targetMarks)
  const spreadLabel = formatSectionSpread(counts)

  const aQs = pick(oneMark, counts.one, rand, used)
  if (aQs.length) {
    sections.push({
      title: 'SECTION A',
      instruction: 'Multiple-choice / assertion–reason questions. Each question carries 1 mark.',
      items: aQs.map((q) => ({
        number: n++,
        marks: 1,
        questions: [q],
        figureNote: q.figureNote,
      })),
    })
  }

  const bQs = pick(vsa, counts.vsa, rand, used)
  if (bQs.length) {
    sections.push({
      title: 'SECTION B',
      instruction: 'Very short answer questions. Each question carries 2 marks.',
      items: bQs.map((q) => ({
        number: n++,
        marks: 2,
        questions: [q],
        figureNote: q.figureNote,
        passage: q.passage,
      })),
    })
  }

  const cQs = pick(sa, counts.sa, rand, used)
  if (cQs.length) {
    sections.push({
      title: 'SECTION C',
      instruction: 'Short answer questions. Each question carries 3 marks.',
      items: cQs.map((q) => ({
        number: n++,
        marks: 3,
        questions: [q],
        figureNote: q.figureNote,
        passage: q.passage,
      })),
    })
  }

  let dItems: PaperItem[] = pick(cases, counts.case, rand, used).map((q) => ({
    number: 0,
    marks: 4,
    questions: [q],
    passage: q.passage,
    figureNote: q.figureNote,
  }))

  if (dItems.length < counts.case) {
    const need = counts.case - dItems.length
    const groups = pickGroups(caseMcq, need, rand, used)
    dItems = dItems.concat(
      groups.map((qs) => ({
        number: 0,
        marks: qs.reduce((s, q) => s + q.marks, 0),
        questions: qs,
        passage: qs.find((q) => q.passage)?.passage,
      })),
    )
  }

  dItems.forEach((item) => {
    item.number = n++
  })

  if (dItems.length) {
    sections.push({
      title: 'SECTION D',
      instruction: 'Case-based questions. Read the passage and answer the questions that follow.',
      items: dItems,
    })
  }

  const eQs = pick(la, counts.la, rand, used)
  if (eQs.length) {
    sections.push({
      title: 'SECTION E',
      instruction: 'Long answer questions. Each question carries 5 marks. Internal choice is given where available.',
      items: eQs.map((q) => ({
        number: n++,
        marks: 5,
        questions: [q],
        passage: q.passage,
        figureNote: q.figureNote,
      })),
    })
  }

  const maxMarks = sections.reduce(
    (sum, s) => sum + s.items.reduce((a, i) => a + i.marks, 0),
    0,
  )

  const targetMarks = marksFromSectionCounts(counts)

  return {
    title: 'ChemCompass Practice Paper',
    subtitle: 'CBSE Class XII · Chemistry (043)',
    time: targetMarks >= 60 ? '3 hours' : targetMarks >= 30 ? '2 hours' : '1 hour',
    maxMarks,
    targetMarks,
    sectionSpread: spreadLabel,
    generatedAt: new Date().toISOString(),
    seed: options.seed,
    sections,
    generalInstructions: [
      `This paper is set for ${targetMarks} marks (${spreadLabel}), following the CBSE section pattern scaled from the 70-mark board paper.`,
      `There are ${n - 1} questions in this paper. Internal choice is indicated where the source paper provided it.`,
      'Section A may include PYQ-derived MCQs; Sections B–E use short/long items from the CBSE question bank and additional practice papers.',
      'Use of log tables and calculators is not allowed.',
      'Figures from the original CBSE PDFs could not always be reproduced; a note is given where a figure was present.',
      maxMarks < targetMarks
        ? `Note: only ${maxMarks} marks of questions were available in the bank for your filters; add chapters/sources or lower the marks target.`
        : '',
    ].filter(Boolean),
  }
}

export function bankStats(chapters: Chapter[], sources: SourceId[], extraQuestions: Question[] = []) {
  const oneMarkQs = [...QUESTIONS, ...extraQuestions].filter((q) =>
    inFilter(q, chapters, sources),
  )
  const subjSources = subjectiveSourcesForPaper(sources)
  const subjectiveQs = QUESTIONS.filter((q) => inFilter(q, chapters, subjSources))
  const byMarks = (qs: Question[]) =>
    qs.reduce<Record<number, number>>((acc, q) => {
      acc[q.marks] = (acc[q.marks] ?? 0) + 1
      return acc
    }, {})

  return {
    total: oneMarkQs.length,
    subjectiveTotal: subjectiveQs.length,
    byMarksOneMark: byMarks(
      oneMarkQs.filter((q) => q.kind === 'mcq' || q.kind === 'assertion-reason'),
    ),
    byMarksSubjective: byMarks(
      subjectiveQs.filter((q) => q.kind !== 'mcq' && q.kind !== 'assertion-reason'),
    ),
    byKind: oneMarkQs.reduce<Record<string, number>>((acc, q) => {
      acc[q.kind] = (acc[q.kind] ?? 0) + 1
      return acc
    }, {}),
    byChapter: oneMarkQs.reduce<Record<string, number>>((acc, q) => {
      acc[q.chapter] = (acc[q.chapter] ?? 0) + 1
      return acc
    }, {}),
  }
}

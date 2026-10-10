export const CHAPTERS = [
  'Solutions',
  'Electrochemistry',
  'Chemical Kinetics',
  'd- and f-Block Elements',
  'Coordination Compounds',
  'Haloalkanes and Haloarenes',
  'Alcohols, Phenols and Ethers',
  'Aldehydes, Ketones and Carboxylic Acids',
  'Amines',
  'Biomolecules',
] as const

export type Chapter = (typeof CHAPTERS)[number]

export type QuestionKind =
  | 'mcq'
  | 'assertion-reason'
  | 'vsa'
  | 'sa'
  | 'case-mcq'
  | 'case'
  | 'la'

export type SourceId =
  | 'qb-xii'
  | 'apq-2023-24-a'
  | 'apq-2023-24-b'
  | 'apq-2022-23'
  | 'apq-2021-22-t2'
  | 'pyq'

export interface PyqReference {
  id: string
  label: string
  stem: string
  markingAnswer?: string
  /** strict = same board wording; creative = new stem inspired by this PYQ */
  generationStyle?: 'strict' | 'creative'
}

export interface Question {
  id: string
  source: SourceId
  chapter: Chapter
  kind: QuestionKind
  marks: number
  text: string
  options?: string[]
  answer?: string
  passage?: string
  groupId?: string
  orText?: string
  figureNote?: string
  /** When MCQ is converted from a specific board PYQ */
  pyqReference?: PyqReference
}

export const SOURCE_LABEL: Record<SourceId, string> = {
  'qb-xii': 'CBSE Question Bank Class XII (Chemistry)',
  'apq-2023-24-a': 'Additional Practice Questions 2023–24 (Set 1)',
  'apq-2023-24-b': 'Additional Practice Questions 2023–24 (Set 2)',
  'apq-2022-23': 'Additional Practice Questions 2022–23',
  'apq-2021-22-t2': 'Additional Practice Questions 2021–22 (Term 2)',
  pyq: 'CBSE Previous Year Papers (PYQ-derived MCQs)',
}

export const KIND_LABEL: Record<QuestionKind, string> = {
  mcq: 'MCQ (1 mark)',
  'assertion-reason': 'Assertion–Reason (1 mark)',
  vsa: 'Very short answer (2 marks)',
  sa: 'Short answer (3 marks)',
  'case-mcq': 'Case-based MCQ',
  case: 'Case-based (4 marks)',
  la: 'Long answer (5 marks)',
}

export const AR_OPTIONS = [
  'Both A and R are true, and R is the correct explanation of A.',
  'Both A and R are true, but R is not the correct explanation of A.',
  'A is true, but R is false.',
  'A is false, but R is true.',
]

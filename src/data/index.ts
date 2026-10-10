import { questionBank } from './questionBank'
import { practiceQuestions } from './practiceQuestions'
import type { Question } from '../types'

export const QUESTIONS: Question[] = [...questionBank, ...practiceQuestions]

export const QUESTIONS_BY_ID = Object.fromEntries(QUESTIONS.map((q) => [q.id, q]))

import api from './client'
import type { QuestionDetail, QuestionFilters, QuestionListItem, QuestionStats, MetadataUpdate } from '../types/question'

export const getStats = () =>
  api.get<QuestionStats>('/questions/stats').then((r) => r.data)

export const getQuestions = (filters: QuestionFilters = {}) => {
  const params: Record<string, string | number | boolean> = {}
  if (filters.subject) params.subject = filters.subject
  if (filters.chapter) params.chapter = filters.chapter
  if (filters.difficulty) params.difficulty = filters.difficulty
  if (filters.question_type) params.question_type = filters.question_type
  if (filters.has_diagram !== undefined) params.has_diagram = filters.has_diagram
  if (filters.has_formula !== undefined) params.has_formula = filters.has_formula
  if (filters.status) params.status = filters.status
  if (filters.search) params.search = filters.search
  if (filters.skip !== undefined) params.skip = filters.skip
  if (filters.limit !== undefined) params.limit = filters.limit
  return api.get<QuestionListItem[]>('/questions', { params }).then((r) => r.data)
}

export const getQuestion = (id: string) =>
  api.get<QuestionDetail>(`/questions/${id}`).then((r) => r.data)

export const updateMetadata = (id: string, data: MetadataUpdate) =>
  api.patch<QuestionDetail>(`/questions/${id}/metadata`, data).then((r) => r.data)

export const updateStatus = (id: string, newStatus: string) =>
  api.patch<QuestionDetail>(`/questions/${id}/status`, null, { params: { new_status: newStatus } }).then((r) => r.data)

import api from './client'
import type {
  AlternativesResponse,
  Paper,
  PaperSummary,
  SyllabusQueryResponse,
} from '../types/paper'

// ── Natural language query → draft paper ──────────────────────────────────

export const syllabusQuery = (prompt: string) =>
  api
    .post<SyllabusQueryResponse>('/papers/syllabus-query', { prompt })
    .then((r) => r.data)

// ── Paper CRUD ────────────────────────────────────────────────────────────

export const getPaper = (id: string) =>
  api.get<Paper>(`/papers/${id}`).then((r) => r.data)

export const listPapers = (status?: string) =>
  api
    .get<PaperSummary[]>('/papers', { params: status ? { status } : {} })
    .then((r) => r.data)

export const approvePaper = (id: string, notes?: string) =>
  api.post<Paper>(`/papers/${id}/approve`, { notes }).then((r) => r.data)

export const exportPaper = (id: string): Promise<string> =>
  api.get<string>(`/papers/${id}/export`, { responseType: 'text' }).then((r) => r.data)

// ── Per-question actions ──────────────────────────────────────────────────

export const lockQuestion = (paperId: string, pqId: string) =>
  api.patch<Paper>(`/papers/${paperId}/questions/${pqId}/lock`).then((r) => r.data)

export const removeQuestion = (paperId: string, pqId: string) =>
  api.delete<Paper>(`/papers/${paperId}/questions/${pqId}`).then((r) => r.data)

export const swapQuestion = (
  paperId: string,
  pqId: string,
  newQuestionId: string,
) =>
  api
    .patch<Paper>(`/papers/${paperId}/questions/${pqId}`, {
      new_question_id: newQuestionId,
    })
    .then((r) => r.data)

export const getAlternatives = (paperId: string, pqId: string) =>
  api
    .get<AlternativesResponse>(`/papers/${paperId}/questions/${pqId}/alternatives`)
    .then((r) => r.data)

export const shufflePaper = (id: string) =>
  api.patch<Paper>(`/papers/${id}/shuffle`).then((r) => r.data)

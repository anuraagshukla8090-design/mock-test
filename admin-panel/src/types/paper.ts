// Types for the paper generation workflow

import type { QuestionDetail } from './question'

// ── Syllabus Query (natural language → draft paper) ────────────────────────

export interface QuestionPreview {
  id: string
  question_number: number | null
  chapter: string | null
  difficulty: string | null
  question_type: string | null
  stem_preview: string
}

export interface ResolvedBlueprint {
  exam_name: string
  subject: string
  resolved_chapters: string[]
  excluded_chapters: string[]
  chapter_filter_mode: string
  question_count: number
  difficulty: string | null
  difficulty_distribution: Record<string, number> | null
  question_type: string | null
  section_type: string | null
  has_formula: boolean | null
  has_diagram: boolean | null
  concepts: string[]
  concept_match_mode: string
  chapter_range_description: string
  resolver_warnings: string[]
}

export interface CandidateSet {
  total_available: number
  by_chapter: Record<string, number>
  by_difficulty: Record<string, number>
  by_section_type: Record<string, number>
  by_question_type: Record<string, number>
  sample_questions: QuestionPreview[]
  can_generate: boolean
  shortage: number
  resolved_blueprint: ResolvedBlueprint
}

export interface SyllabusQueryResponse {
  paper_id: string | null
  candidates: CandidateSet
  paper: PaperSummary | null
}

// ── Paper ──────────────────────────────────────────────────────────────────

export interface PaperQuestionItem {
  id: string           // PaperQuestion row ID
  paper_id: string
  question_id: string
  position: number
  paper_section: string | null
  display_number: number | null
  locked: boolean
  question: QuestionDetail
}

export interface Paper {
  id: string
  prompt: string
  blueprint: Record<string, unknown>
  status: string        // "draft" | "approved"
  notes: string | null
  questions: PaperQuestionItem[]
  created_at: string
  updated_at: string
}

export interface PaperSummary {
  id: string
  prompt: string
  status: string
  created_at: string
}

export interface AlternativesResponse {
  alternatives: QuestionDetail[]
}

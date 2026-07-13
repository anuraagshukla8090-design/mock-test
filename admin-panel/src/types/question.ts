export interface QuestionListItem {
  id: string
  question_number: number | null
  subject: string | null
  chapter: string | null
  topic: string | null
  difficulty: string | null
  question_type: string | null
  has_diagram: boolean
  has_formula: boolean
  section_type: string
  status: string
}

export interface QuestionImage {
  filename: string
  position: string
}

export interface QuestionDetail extends QuestionListItem {
  ingestion_id: string
  source_pdf: string
  source_page: number | null
  stem_md: string
  options: Record<string, string>
  answer: string | null
  images: QuestionImage[]
  section_label: string | null
  exam_name: string | null
  subtopic: string | null
  concepts: string[]
  llm_raw_response: Record<string, unknown> | null
  raw_text: string | null
  created_at: string
}

export interface QuestionStats {
  total: number
  by_subject: Record<string, number>
  by_difficulty: Record<string, number>
  by_chapter: Record<string, number>
  by_section_type: Record<string, number>
}

export interface MetadataUpdate {
  exam_name?: string
  subject?: string
  chapter?: string
  topic?: string
  subtopic?: string
  difficulty?: string
  question_type?: string
  concepts?: string[]
  has_formula?: boolean
  has_diagram?: boolean
}

export interface QuestionFilters {
  exam_name?: string
  subject?: string
  chapter?: string
  difficulty?: string
  question_type?: string
  has_diagram?: boolean
  has_formula?: boolean
  status?: string
  search?: string
  skip?: number
  limit?: number
}

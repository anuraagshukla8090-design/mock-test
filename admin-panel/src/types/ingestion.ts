export type IngestionStatus =
  | 'UPLOADED'
  | 'MINERU_COMPLETE'
  | 'QUESTIONS_BUILT'
  | 'METADATA_COMPLETE'
  | 'SAVED'
  | 'FAILED'

export interface ProcessingReport {
  questions_detected: number
  questions_stored: number
  questions_skipped: number
  answers_mapped: number
  images_linked: number
  processing_time_s: number
  warnings: string[]
  errors: string[]
  per_question?: Array<{ number: number; status: string; warnings: string[] }>
}

export interface IngestionListItem {
  id: string
  filename: string
  status: IngestionStatus
  exam_name: string | null
  subject: string | null
  layout_type: string | null
  questions_saved: number
  created_at: string
}

export interface IngestionDetail extends IngestionListItem {
  error_message: string | null
  failed_at_stage: string | null
  questions_found: number
  detected_layout: string | null
  detected_subjects: string[]
  processing_time_s: number | null
  processing_report: ProcessingReport | null
  mineru_output_dir: string | null
}

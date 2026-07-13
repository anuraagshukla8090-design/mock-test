import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { updateMetadata } from '../../api/questions'
import type { QuestionDetail, MetadataUpdate } from '../../types/question'
import Spinner from '../ui/Spinner'
import { EXAMS, SUBJECTS, subjectsForExam } from '../../constants/exams'

const DIFFICULTY_OPTIONS = ['easy', 'medium', 'hard']
const QUESTION_TYPE_OPTIONS = [
  'conceptual', 'numerical', 'assertion_reason',
  'match_the_following', 'statement_based',
]

interface Props {
  question: QuestionDetail
  onClose: () => void
}

export default function MetadataEditForm({ question, onClose }: Props) {
  const qc = useQueryClient()
  const [form, setForm] = useState<MetadataUpdate>({
    exam_name: question.exam_name ?? '',
    subject: question.subject ?? '',
    chapter: question.chapter ?? '',
    topic: question.topic ?? '',
    subtopic: question.subtopic ?? '',
    difficulty: question.difficulty ?? '',
    question_type: question.question_type ?? '',
    concepts: question.concepts ?? [],
    has_formula: question.has_formula,
    has_diagram: question.has_diagram,
  })

  const handleExamChange = (newExam: string) => {
    const validSubjects = subjectsForExam(newExam).map((s) => s.value)
    setForm((f) => ({
      ...f,
      exam_name: newExam,
      subject: f.subject && !validSubjects.includes(f.subject as never) ? '' : f.subject,
    }))
  }

  const mut = useMutation({
    mutationFn: () => updateMetadata(question.id, form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['question', question.id] })
      onClose()
    },
  })

  const field = (label: string, key: keyof MetadataUpdate, type: 'text' | 'select' | 'checkbox' = 'text', options?: string[]) => (
    <div key={key} className="flex flex-col gap-1">
      <label className="text-xs font-medium text-gray-600">{label}</label>
      {type === 'select' ? (
        <select
          value={(form[key] as string) ?? ''}
          onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
          className="border border-gray-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
        >
          <option value="">— not set —</option>
          {options?.map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
      ) : type === 'checkbox' ? (
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={Boolean(form[key])}
            onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.checked }))}
            className="h-4 w-4 text-indigo-600"
          />
          <span className="text-gray-700">{label}</span>
        </label>
      ) : (
        <input
          type="text"
          value={(form[key] as string) ?? ''}
          onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
          className="border border-gray-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
        />
      )}
    </div>
  )

  return (
    <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 space-y-3">
      <div className="grid grid-cols-2 gap-3">

        {/* Exam — standardised select */}
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-gray-600">Exam</label>
          <select
            value={(form.exam_name as string) ?? ''}
            onChange={(e) => handleExamChange(e.target.value)}
            className="border border-gray-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
          >
            <option value="">— not set —</option>
            {EXAMS.map((e) => (
              <option key={e.value} value={e.value}>{e.label}</option>
            ))}
          </select>
        </div>

        {/* Subject — cascades from exam */}
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-gray-600">Subject</label>
          <select
            value={(form.subject as string) ?? ''}
            onChange={(e) => setForm((f) => ({ ...f, subject: e.target.value }))}
            className="border border-gray-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
          >
            <option value="">— not set —</option>
            {(form.exam_name ? subjectsForExam(form.exam_name as string) : SUBJECTS).map((s) => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>
        </div>

        {field('Chapter', 'chapter')}
        {field('Topic', 'topic')}
        {field('Subtopic', 'subtopic')}
        {field('Difficulty', 'difficulty', 'select', DIFFICULTY_OPTIONS)}
        {field('Question Type', 'question_type', 'select', QUESTION_TYPE_OPTIONS)}
      </div>

      <div>
        <label className="text-xs font-medium text-gray-600">Concepts (comma-separated)</label>
        <input
          type="text"
          value={(form.concepts ?? []).join(', ')}
          onChange={(e) => setForm((f) => ({
            ...f,
            concepts: e.target.value.split(',').map((s) => s.trim()).filter(Boolean),
          }))}
          className="mt-1 w-full border border-gray-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
        />
      </div>

      <div className="flex gap-6">
        {field('Has Formula', 'has_formula', 'checkbox')}
        {field('Has Diagram', 'has_diagram', 'checkbox')}
      </div>

      {mut.isError && (
        <p className="text-red-600 text-xs">{String(mut.error)}</p>
      )}

      <div className="flex gap-2 pt-1">
        <button
          onClick={() => mut.mutate()}
          disabled={mut.isPending}
          className="flex items-center gap-2 px-4 py-1.5 bg-indigo-600 text-white text-sm rounded hover:bg-indigo-700 disabled:opacity-50"
        >
          {mut.isPending && <Spinner size="sm" />}
          Save Changes
        </button>
        <button
          onClick={onClose}
          className="px-4 py-1.5 border border-gray-200 text-sm rounded hover:bg-gray-100"
        >
          Cancel
        </button>
      </div>
    </div>
  )
}

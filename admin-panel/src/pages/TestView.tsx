import { useState, useEffect, useCallback } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ChevronLeft, ChevronRight, BookOpen, Tag, BarChart2,
  Hash, Layers, Zap, Image, FunctionSquare, CheckCircle2,
  XCircle, Circle, Bookmark, ExternalLink, Loader2, AlertCircle,
  GraduationCap, FlaskConical, Trash2,
} from 'lucide-react'
import { getQuestions, getQuestion, deleteQuestion } from '../api/questions'
import type { QuestionDetail, QuestionFilters } from '../types/question'
import RenderedContent from '../components/question/RenderedContent'

/* ────────────────────────────────────────────────────────────
   Helpers
──────────────────────────────────────────────────────────── */
const OPTION_LABELS = ['A', 'B', 'C', 'D', 'E']

const DIFFICULTY_STYLE: Record<string, string> = {
  easy:   'bg-emerald-100 text-emerald-700 border-emerald-200',
  medium: 'bg-amber-100 text-amber-700 border-amber-200',
  hard:   'bg-rose-100 text-rose-700 border-rose-200',
}

const SECTION_STYLE: Record<string, string> = {
  mcq:     'bg-indigo-100 text-indigo-700 border-indigo-200',
  integer: 'bg-violet-100 text-violet-700 border-violet-200',
}

function Badge({
  children, className = '',
}: { children: React.ReactNode; className?: string }) {
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-medium border ${className}`}>
      {children}
    </span>
  )
}

function MetaRow({ icon, label, value }: { icon: React.ReactNode; label: string; value: React.ReactNode }) {
  if (!value) return null
  return (
    <div className="flex items-start gap-2 py-2 border-b border-gray-100 last:border-0">
      <div className="text-gray-400 mt-0.5 flex-shrink-0">{icon}</div>
      <div className="min-w-0">
        <p className="text-[10px] uppercase tracking-wide text-gray-400 font-medium">{label}</p>
        <p className="text-sm text-gray-800 font-medium leading-snug mt-0.5 break-words">{value}</p>
      </div>
    </div>
  )
}

/* ────────────────────────────────────────────────────────────
   Option component — shows correct/incorrect styling
──────────────────────────────────────────────────────────── */
function Option({
  label, content, isCorrect, isSelected, revealed,
  onClick,
}: {
  label: string
  content: string
  isCorrect: boolean
  isSelected: boolean
  revealed: boolean
  onClick: () => void
}) {
  let ring = 'border-gray-200 bg-white hover:border-indigo-300 hover:bg-indigo-50/40'
  let indicator = <Circle size={18} className="text-gray-300 flex-shrink-0 mt-0.5" />

  if (revealed) {
    if (isCorrect) {
      ring = 'border-emerald-400 bg-emerald-50'
      indicator = <CheckCircle2 size={18} className="text-emerald-500 flex-shrink-0 mt-0.5" />
    } else if (isSelected && !isCorrect) {
      ring = 'border-rose-400 bg-rose-50'
      indicator = <XCircle size={18} className="text-rose-500 flex-shrink-0 mt-0.5" />
    }
  } else if (isSelected) {
    ring = 'border-indigo-400 bg-indigo-50'
    indicator = <CheckCircle2 size={18} className="text-indigo-400 flex-shrink-0 mt-0.5" />
  }

  return (
    <button
      onClick={onClick}
      className={`w-full flex items-start gap-3 p-4 rounded-xl border-2 text-left transition-all duration-150 ${ring} ${!revealed ? 'cursor-pointer' : 'cursor-default'}`}
    >
      {/* Option label bubble */}
      <span className={`
        flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-sm font-bold mt-0.5
        ${revealed && isCorrect ? 'bg-emerald-500 text-white' :
          revealed && isSelected && !isCorrect ? 'bg-rose-500 text-white' :
          isSelected ? 'bg-indigo-500 text-white' : 'bg-gray-100 text-gray-600'}
      `}>
        {label}
      </span>
      {indicator}
      <div className="flex-1 min-w-0">
        <RenderedContent content={content} />
      </div>
    </button>
  )
}

/* ────────────────────────────────────────────────────────────
   Main page
──────────────────────────────────────────────────────────── */
export default function TestView() {
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  // ── Filters from URL (same as QuestionBank so links carry over) ──
  const filters: QuestionFilters = {
    subject:       searchParams.get('subject')    ?? undefined,
    chapter:       searchParams.get('chapter')    ?? undefined,
    difficulty:    searchParams.get('difficulty') ?? undefined,
    question_type: searchParams.get('question_type') ?? undefined,
    limit: 200,
  }

  // ── Fetch the full list to support prev/next navigation ─────────
  const { data: list = [], isLoading: listLoading } = useQuery({
    queryKey: ['questions-list-for-testview', filters],
    queryFn: () => getQuestions(filters),
  })

  // ── Current index in the list ────────────────────────────────────
  const [idx, setIdx] = useState(() => {
    const n = Number(searchParams.get('idx') ?? 0)
    return isNaN(n) ? 0 : n
  })

  const currentItem = list[idx]

  // ── Fetch full question detail ───────────────────────────────────
  const { data: question, isLoading: qLoading } = useQuery({
    queryKey: ['question-detail', currentItem?.id],
    queryFn: () => getQuestion(currentItem!.id),
    enabled: !!currentItem?.id,
  })

  // ── Per-question interaction state ──────────────────────────────
  const [selected, setSelected] = useState<string | null>(null)
  const [revealed, setRevealed] = useState(false)
  const [integerInput, setIntegerInput] = useState('')

  // Reset interaction when question changes
  useEffect(() => {
    setSelected(null)
    setRevealed(false)
    setIntegerInput('')
  }, [idx])

  // Sync idx to URL
  const goTo = useCallback((newIdx: number) => {
    const clamped = Math.max(0, Math.min(list.length - 1, newIdx))
    setIdx(clamped)
    setSearchParams(prev => {
      const next = new URLSearchParams(prev)
      next.set('idx', String(clamped))
      return next
    }, { replace: true })
  }, [list.length, setSearchParams])

  // Keyboard navigation
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return
      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') goTo(idx + 1)
      if (e.key === 'ArrowLeft'  || e.key === 'ArrowUp')   goTo(idx - 1)
      if (e.key === ' ') { e.preventDefault(); setRevealed(r => !r) }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [idx, goTo])

  // Delete question mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteQuestion(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['questions-list-for-testview'] })
      queryClient.invalidateQueries({ queryKey: ['questions'] })
      // Move to next question (or previous if at end)
      const nextIdx = idx > 0 ? idx - 1 : 0
      setIdx(nextIdx)
    },
  })

  const handleDeleteQuestion = () => {
    if (!question) return
    if (!window.confirm(`Delete question Q${question.question_number ?? idx + 1}?\n\nThis is permanent and cannot be undone.`)) return
    deleteMutation.mutate(question.id)
  }

  const isMCQ = question?.section_type === 'mcq'
  const optionEntries = Object.entries(question?.options ?? {})

  /* ── Render ─────────────────────────────────────────────────────── */
  return (
    <div className="h-screen flex flex-col bg-slate-50 overflow-hidden">

      {/* ── Top bar ───────────────────────────────────────────────── */}
      <header className="flex-shrink-0 bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <GraduationCap className="text-indigo-600" size={20} />
          <span className="font-semibold text-gray-800 text-sm">Test View</span>
          {question?.exam_name && (
            <Badge className="bg-indigo-50 text-indigo-600 border-indigo-200">
              {question.exam_name}
            </Badge>
          )}
          {question?.subject && (
            <Badge className="bg-slate-100 text-slate-600 border-slate-200">
              <FlaskConical size={11} />
              {question.subject}
            </Badge>
          )}
        </div>

        <div className="flex items-center gap-3">
          {/* Jump to question */}
          <div className="flex items-center gap-1 text-sm text-gray-500">
            <span>Q</span>
            <input
              type="number"
              min={1}
              max={list.length}
              value={idx + 1}
              onChange={e => goTo(Number(e.target.value) - 1)}
              className="w-14 text-center border border-gray-300 rounded-md px-2 py-1 text-sm focus:ring-2 focus:ring-indigo-400 focus:outline-none"
            />
            <span className="text-gray-400">/ {list.length}</span>
          </div>

          {/* Prev / Next */}
          <button
            onClick={() => goTo(idx - 1)}
            disabled={idx === 0}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-gray-200 text-gray-600 text-sm disabled:opacity-40 hover:bg-gray-50 transition"
          >
            <ChevronLeft size={15} /> Prev
          </button>
          <button
            onClick={() => goTo(idx + 1)}
            disabled={idx >= list.length - 1}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-gray-200 text-gray-600 text-sm disabled:opacity-40 hover:bg-gray-50 transition"
          >
            Next <ChevronRight size={15} />
          </button>

          {/* Link to detail page */}
          {question && (
            <button
              onClick={() => navigate(`/questions/${question.id}`)}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-indigo-600 text-white text-sm hover:bg-indigo-700 transition"
              title="Open full detail"
            >
              <ExternalLink size={13} />
              Detail
            </button>
          )}
        </div>
      </header>

      {/* ── Progress bar ────────────────────────────────────────── */}
      <div className="flex-shrink-0 h-1 bg-gray-100">
        <div
          className="h-1 bg-indigo-500 transition-all duration-300"
          style={{ width: list.length ? `${((idx + 1) / list.length) * 100}%` : '0%' }}
        />
      </div>

      {/* ── Body ────────────────────────────────────────────────── */}
      <div className="flex-1 flex overflow-hidden">

        {/* ── Question area ─────────────────────────────────────── */}
        <div className="flex-1 overflow-y-auto px-8 py-6">

          {(listLoading || qLoading) && !question && (
            <div className="flex items-center justify-center h-full gap-3 text-gray-400">
              <Loader2 className="animate-spin" size={24} />
              <span>Loading question…</span>
            </div>
          )}

          {!listLoading && list.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full gap-3 text-gray-400">
              <AlertCircle size={36} />
              <p className="text-lg font-medium">No questions found</p>
              <p className="text-sm">Adjust filters in the Question Bank and return here.</p>
            </div>
          )}

          {question && (
            <div className="max-w-3xl mx-auto space-y-6">

              {/* ── Question number + type badges ──────────────── */}
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-2xl font-bold text-gray-800">
                  Q{question.question_number ?? idx + 1}.
                </span>
                {question.difficulty && (
                  <Badge className={DIFFICULTY_STYLE[question.difficulty] ?? 'bg-gray-100 text-gray-600 border-gray-200'}>
                    <BarChart2 size={10} />
                    {question.difficulty.charAt(0).toUpperCase() + question.difficulty.slice(1)}
                  </Badge>
                )}
                {question.section_type && (
                  <Badge className={SECTION_STYLE[question.section_type] ?? 'bg-gray-100 text-gray-600 border-gray-200'}>
                    <Layers size={10} />
                    {question.section_type.toUpperCase()}
                  </Badge>
                )}
                {question.question_type && (
                  <Badge className="bg-gray-100 text-gray-600 border-gray-200">
                    <Tag size={10} />
                    {question.question_type}
                  </Badge>
                )}
                {question.has_diagram && (
                  <Badge className="bg-sky-100 text-sky-600 border-sky-200">
                    <Image size={10} /> Diagram
                  </Badge>
                )}
                {question.has_formula && (
                  <Badge className="bg-purple-100 text-purple-600 border-purple-200">
                    <FunctionSquare size={10} /> Formula
                  </Badge>
                )}
              </div>

              {/* ── Stem ──────────────────────────────────────── */}
              <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
                <RenderedContent content={question.stem_md} />

                {/* Stem-level images */}
                {question.images.filter(img => img.position === 'stem').map(img => (
                  <img
                    key={img.filename}
                    src={`/api/images/${img.filename}`}
                    alt="question diagram"
                    className="mt-4 max-w-full rounded-xl border border-gray-200 shadow-sm"
                  />
                ))}
              </div>

              {/* ── Options (MCQ) ─────────────────────────────── */}
              {isMCQ && optionEntries.length > 0 && (
                <div className="space-y-3">
                  <p className="text-xs uppercase tracking-wider text-gray-400 font-semibold">Options</p>
                  {optionEntries.map(([key, value], i) => (
                    <Option
                      key={key}
                      label={OPTION_LABELS[i] ?? key}
                      content={value}
                      isCorrect={key === question.answer}
                      isSelected={selected === key}
                      revealed={revealed}
                      onClick={() => {
                        if (!revealed) setSelected(key)
                      }}
                    />
                  ))}
                </div>
              )}

              {/* ── Integer answer box ────────────────────────── */}
              {!isMCQ && (
                <div className="space-y-3">
                  <p className="text-xs uppercase tracking-wider text-gray-400 font-semibold">Your Answer</p>
                  <div className="flex items-center gap-3">
                    <input
                      type="number"
                      value={integerInput}
                      onChange={e => setIntegerInput(e.target.value)}
                      placeholder="Enter integer…"
                      className="w-48 border-2 border-gray-200 rounded-xl px-4 py-3 text-xl text-center font-mono focus:ring-2 focus:ring-indigo-400 focus:border-indigo-400 focus:outline-none"
                    />
                    {revealed && (
                      <div className={`flex items-center gap-2 px-4 py-3 rounded-xl border-2 font-mono text-xl font-bold ${
                        integerInput === String(question.answer)
                          ? 'bg-emerald-50 border-emerald-400 text-emerald-700'
                          : 'bg-rose-50 border-rose-400 text-rose-700'
                      }`}>
                        {integerInput === String(question.answer)
                          ? <CheckCircle2 size={20} />
                          : <XCircle size={20} />}
                        {question.answer}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* ── Reveal / Hide answer button ───────────────── */}
              <div className="flex items-center gap-3 pt-2">
                <button
                  onClick={() => setRevealed(r => !r)}
                  className={`px-5 py-2.5 rounded-xl text-sm font-semibold transition-all duration-150 shadow-sm ${
                    revealed
                      ? 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                      : 'bg-indigo-600 text-white hover:bg-indigo-700'
                  }`}
                >
                  {revealed ? 'Hide Answer' : 'Show Answer'}
                </button>
                <span className="text-xs text-gray-400">or press Space</span>

                {/* Inline correct answer when revealed */}
                {revealed && isMCQ && (
                  <span className="ml-2 flex items-center gap-1 text-emerald-600 font-semibold text-sm">
                    <CheckCircle2 size={15} />
                    Correct: {OPTION_LABELS[Object.keys(question.options).indexOf(question.answer ?? '')] ?? question.answer}
                  </span>
                )}
              </div>

              {/* ── Option-level images (if any) ──────────────── */}
              {question.images.filter(img => img.position === 'options').length > 0 && (
                <div className="grid grid-cols-2 gap-3">
                  {question.images.filter(img => img.position === 'options').map(img => (
                    <img
                      key={img.filename}
                      src={`/api/images/${img.filename}`}
                      alt="option diagram"
                      className="w-full rounded-xl border border-gray-200 shadow-sm"
                    />
                  ))}
                </div>
              )}

              {/* ── Bottom nav (also at bottom for long questions) */}
              <div className="flex justify-between items-center pt-4 pb-8">
                <button
                  onClick={() => goTo(idx - 1)}
                  disabled={idx === 0}
                  className="flex items-center gap-2 px-4 py-2 rounded-xl border border-gray-200 text-gray-600 text-sm disabled:opacity-30 hover:bg-gray-50 transition"
                >
                  <ChevronLeft size={16} /> Previous
                </button>
                <span className="text-sm text-gray-400">{idx + 1} of {list.length}</span>
                <button
                  onClick={() => goTo(idx + 1)}
                  disabled={idx >= list.length - 1}
                  className="flex items-center gap-2 px-4 py-2 rounded-xl border border-gray-200 text-gray-600 text-sm disabled:opacity-30 hover:bg-gray-50 transition"
                >
                  Next <ChevronRight size={16} />
                </button>
              </div>

            </div>
          )}
        </div>

        {/* ── Metadata sidebar ──────────────────────────────────── */}
        {question && (
          <aside className="w-64 flex-shrink-0 bg-white border-l border-gray-200 overflow-y-auto">
            <div className="px-4 py-4 border-b border-gray-100">
              <p className="text-xs uppercase tracking-wider text-gray-500 font-semibold flex items-center gap-1.5">
                <Bookmark size={11} /> Metadata
              </p>
            </div>

            <div className="px-4 py-2">
              <MetaRow icon={<GraduationCap size={14} />} label="Exam" value={question.exam_name} />
              <MetaRow icon={<FlaskConical size={14} />} label="Subject" value={question.subject} />
              <MetaRow icon={<BookOpen size={14} />} label="Chapter" value={question.chapter} />
              <MetaRow icon={<Tag size={14} />} label="Topic" value={question.topic} />
              <MetaRow icon={<Tag size={14} />} label="Subtopic" value={question.subtopic} />
              <MetaRow
                icon={<BarChart2 size={14} />}
                label="Difficulty"
                value={
                  question.difficulty ? (
                    <Badge className={DIFFICULTY_STYLE[question.difficulty] ?? 'bg-gray-100 text-gray-600 border-gray-200'}>
                      {question.difficulty}
                    </Badge>
                  ) : null
                }
              />
              <MetaRow
                icon={<Layers size={14} />}
                label="Section Type"
                value={
                  question.section_type ? (
                    <Badge className={SECTION_STYLE[question.section_type] ?? 'bg-gray-100 text-gray-600 border-gray-200'}>
                      {question.section_type.toUpperCase()}
                    </Badge>
                  ) : null
                }
              />
              <MetaRow icon={<Zap size={14} />} label="Question Type" value={question.question_type} />
              <MetaRow icon={<Hash size={14} />} label="Q Number" value={question.question_number} />
              <MetaRow icon={<Hash size={14} />} label="Source Page" value={question.source_page} />

              {/* Concepts */}
              {question.concepts?.length > 0 && (
                <div className="py-2 border-b border-gray-100">
                  <p className="text-[10px] uppercase tracking-wide text-gray-400 font-medium mb-1.5">Concepts</p>
                  <div className="flex flex-wrap gap-1">
                    {question.concepts.map(c => (
                      <span key={c} className="px-2 py-0.5 bg-indigo-50 text-indigo-600 text-[11px] rounded-md border border-indigo-100">
                        {c}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Flags */}
              <div className="py-3 space-y-2">
                <p className="text-[10px] uppercase tracking-wide text-gray-400 font-medium">Flags</p>
                <div className="flex flex-wrap gap-1.5">
                  {question.has_diagram && (
                    <Badge className="bg-sky-100 text-sky-600 border-sky-200">
                      <Image size={10} /> Diagram
                    </Badge>
                  )}
                  {question.has_formula && (
                    <Badge className="bg-purple-100 text-purple-600 border-purple-200">
                      <FunctionSquare size={10} /> Formula
                    </Badge>
                  )}
                  {!question.has_diagram && !question.has_formula && (
                    <span className="text-xs text-gray-400">None</span>
                  )}
                </div>
              </div>

              {/* Source PDF */}
              {question.source_pdf && (
                <div className="py-2 border-t border-gray-100">
                  <p className="text-[10px] uppercase tracking-wide text-gray-400 font-medium mb-1">Source PDF</p>
                  <p className="text-[11px] text-gray-500 break-all leading-relaxed">
                    {question.source_pdf.split('/').pop() ?? question.source_pdf}
                  </p>
                </div>
              )}
            </div>

            {/* ── Delete question button ───────────────────────── */}
            <div className="px-4 py-4 border-t border-gray-200">
              <button
                onClick={handleDeleteQuestion}
                disabled={deleteMutation.isPending}
                className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg
                  border border-red-200 text-red-500 text-xs font-medium
                  hover:bg-red-50 hover:border-red-400 hover:text-red-600
                  disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                title="Permanently delete this question"
              >
                {deleteMutation.isPending
                  ? <Loader2 size={13} className="animate-spin" />
                  : <Trash2 size={13} />}
                Delete Question
              </button>
              {deleteMutation.isError && (
                <p className="text-[11px] text-red-500 mt-1.5 text-center">Delete failed. Try again.</p>
              )}
            </div>

            {/* ── Mini question palette ────────────────────────── */}
            <div className="px-4 py-4 border-t border-gray-200 mt-2">
              <p className="text-[10px] uppercase tracking-wide text-gray-400 font-medium mb-2">
                Questions ({list.length})
              </p>
              <div className="flex flex-wrap gap-1 max-h-40 overflow-y-auto pr-1">
                {list.map((q, i) => (
                  <button
                    key={q.id}
                    onClick={() => goTo(i)}
                    title={`Q${q.question_number ?? i + 1} — ${q.chapter ?? ''}`}
                    className={`w-7 h-7 rounded text-[11px] font-semibold transition-all ${
                      i === idx
                        ? 'bg-indigo-600 text-white shadow-md scale-110'
                        : q.difficulty === 'easy'
                          ? 'bg-emerald-100 text-emerald-700 hover:bg-emerald-200'
                          : q.difficulty === 'hard'
                            ? 'bg-rose-100 text-rose-700 hover:bg-rose-200'
                            : 'bg-amber-100 text-amber-700 hover:bg-amber-200'
                    }`}
                  >
                    {i + 1}
                  </button>
                ))}
              </div>
            </div>
          </aside>
        )}

      </div>
    </div>
  )
}

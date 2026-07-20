import { useState, useEffect, useCallback } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ChevronLeft, ChevronRight, BookOpen, Tag, BarChart2,
  Hash, Layers, Zap, Image, FunctionSquare, CheckCircle2,
  XCircle, Circle, Bookmark, ExternalLink, Loader2, AlertCircle,
  GraduationCap, FlaskConical, Trash2, Sparkles, RefreshCw, X,
  GitBranch,
} from 'lucide-react'
import { getQuestions, getQuestion, deleteQuestion, regenerateQuestion, saveRegeneratedQuestion } from '../api/questions'
import type { QuestionDetail, QuestionFilters, RegenerateDraft } from '../types/question'
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

  // ── Regeneration state ───────────────────────────────────────────────────
  const [regenModalOpen, setRegenModalOpen] = useState(false)
  const [regenDraft, setRegenDraft] = useState<RegenerateDraft | null>(null)
  const [regenError, setRegenError] = useState<string | null>(null)
  // Persist last-used provider so teacher doesn't have to re-select each time
  const [regenProvider, setRegenProvider] = useState<'ollama' | 'groq'>(
    () => (localStorage.getItem('regenProvider') as 'ollama' | 'groq') || 'ollama'
  )

  const regenMutation = useMutation({
    mutationFn: ({ id, provider }: { id: string; provider: 'ollama' | 'groq' }) =>
      regenerateQuestion(id, provider),
    onSuccess: (draft) => {
      setRegenDraft(draft)
      setRegenError(null)
    },
    onError: (err: Error) => {
      setRegenError(err.message || 'LLM failed to generate. Try again.')
    },
  })

  const saveMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: { stem_md: string; options: Record<string, string>; answer: string } }) =>
      saveRegeneratedQuestion(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['questions-list-for-testview'] })
      queryClient.invalidateQueries({ queryKey: ['questions'] })
      setRegenModalOpen(false)
      setRegenDraft(null)
    },
  })

  const handleOpenRegen = () => {
    if (!question) return
    // Open blank — teacher selects provider and clicks Generate themselves
    setRegenDraft(null)
    setRegenError(null)
    setRegenModalOpen(true)
  }

  const handleGenerate = (provider: 'ollama' | 'groq' = regenProvider) => {
    if (!question) return
    setRegenError(null)
    regenMutation.mutate({ id: question.id, provider })
  }

  const handleRetryRegen = () => handleGenerate()

  const handleAcceptRegen = () => {
    if (!question || !regenDraft) return
    saveMutation.mutate({
      id: question.id,
      data: { stem_md: regenDraft.stem_md, options: regenDraft.options as Record<string, string>, answer: regenDraft.answer },
    })
  }

  const canRegenerate = question && !question.has_diagram && question.images.length === 0

  const isMCQ = question?.section_type === 'mcq'
  const optionEntries = Object.entries(question?.options ?? {})

  /* ── Render ─────────────────────────────────────────────────────── */
  return (
    <div className="h-screen flex flex-col bg-slate-50 overflow-hidden">

      {/* ── Regeneration Modal ─────────────────────────────────────── */}
      {regenModalOpen && question && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-6xl max-h-[90vh] flex flex-col overflow-hidden">
            {/* Modal header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 flex-shrink-0">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-violet-100 flex items-center justify-center">
                  <Sparkles size={16} className="text-violet-600" />
                </div>
                <div>
                  <h2 className="text-base font-semibold text-gray-800">AI Question Regeneration</h2>
                  <p className="text-xs text-gray-500">Same concept · Different values</p>
                </div>
              </div>

              {/* Provider toggle */}
              <div className="flex items-center gap-3">
                <span className="text-xs text-gray-400 font-medium">Provider</span>
                <div className="flex items-center bg-gray-100 rounded-lg p-0.5 gap-0.5">
                  {(['ollama', 'groq'] as const).map((p) => (
                    <button
                      key={p}
                      onClick={() => {
                        if (regenProvider === p) return
                        localStorage.setItem('regenProvider', p)
                        setRegenProvider(p)
                        setRegenError(null)
                        // If a draft already exists, auto-switch and re-generate
                        // If blank (nothing generated yet), just update selection
                        if (regenDraft || regenMutation.isPending) {
                          setRegenDraft(null)
                          regenMutation.mutate({ id: question.id, provider: p })
                        }
                      }}
                      disabled={regenMutation.isPending}
                      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
                        regenProvider === p
                          ? 'bg-white text-gray-800 shadow-sm'
                          : 'text-gray-500 hover:text-gray-700'
                      }`}
                    >
                      {p === 'ollama' ? '🖥 Ollama' : '⚡ Groq'}
                    </button>
                  ))}
                </div>

                <button
                  onClick={() => { setRegenModalOpen(false); setRegenDraft(null); setRegenError(null) }}
                  className="p-2 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition"
                >
                  <X size={18} />
                </button>
              </div>
            </div>

            {/* Modal body — side by side */}
            <div className="flex-1 overflow-hidden grid grid-cols-2 divide-x divide-gray-200">
              {/* Left: Original */}
              <div className="overflow-y-auto p-6 space-y-4">
                <p className="text-[10px] uppercase tracking-widest font-semibold text-gray-400 mb-3">Original Question</p>
                <div className="bg-slate-50 rounded-xl border border-gray-200 p-4">
                  <RenderedContent content={question.stem_md} />
                </div>
                {Object.entries(question.options).length > 0 && (
                  <div className="space-y-2">
                    {Object.entries(question.options).map(([key, val]) => (
                      <div key={key} className={`flex gap-3 p-3 rounded-lg border text-sm ${
                        key === question.answer
                          ? 'border-emerald-300 bg-emerald-50'
                          : 'border-gray-200 bg-white'
                      }`}>
                        <span className={`font-bold flex-shrink-0 w-5 ${
                          key === question.answer ? 'text-emerald-600' : 'text-gray-400'
                        }`}>{key}</span>
                        <RenderedContent content={val} />
                      </div>
                    ))}
                  </div>
                )}
                {question.section_type !== 'mcq' && (
                  <p className="text-sm text-gray-600">Answer: <span className="font-mono font-bold">{question.answer}</span></p>
                )}
              </div>

              {/* Right: Regenerated draft */}
              <div className="overflow-y-auto p-6 space-y-4 bg-violet-50/30">
                <p className="text-[10px] uppercase tracking-widest font-semibold text-violet-500 mb-3 flex items-center gap-1.5">
                  <Sparkles size={10} /> AI Variant
                </p>

                {/* Idle state — no generation started yet */}
                {!regenMutation.isPending && !regenDraft && !regenError && (
                  <div className="flex flex-col items-center justify-center h-48 gap-5">
                    <div className="w-14 h-14 rounded-2xl bg-violet-100 flex items-center justify-center">
                      <Sparkles size={26} className="text-violet-500" />
                    </div>
                    <div className="text-center">
                      <p className="text-sm font-semibold text-gray-700">Ready to generate</p>
                      <p className="text-xs text-gray-400 mt-1">
                        Provider: <span className="font-medium text-gray-600">{regenProvider === 'ollama' ? '🖥 Ollama (local)' : '⚡ Groq (cloud)'}</span>
                      </p>
                    </div>
                    <button
                      onClick={() => handleGenerate()}
                      className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-violet-600 text-white text-sm font-semibold
                        hover:bg-violet-700 active:scale-95 transition shadow-sm"
                    >
                      <Sparkles size={14} /> Generate Variant
                    </button>
                  </div>
                )}

                {/* Loading state */}
                {regenMutation.isPending && (
                  <div className="flex flex-col items-center justify-center h-48 gap-4">
                    <div className="relative">
                      <div className="w-12 h-12 rounded-full border-4 border-violet-200 border-t-violet-600 animate-spin" />
                      <Sparkles size={14} className="text-violet-600 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
                    </div>
                    <p className="text-sm text-violet-600 font-medium">Generating variant…</p>
                    <p className="text-xs text-gray-400">
                      {regenProvider === 'groq'
                        ? 'Calling Groq API… usually fast!'
                        : 'Ollama is thinking. This may take 15–30 seconds.'}
                    </p>
                  </div>
                )}

                {/* Error state */}
                {regenError && (
                  <div className="flex flex-col items-center justify-center h-48 gap-4">
                    <AlertCircle size={32} className="text-rose-400" />
                    <p className="text-sm text-rose-600 font-medium text-center max-w-xs">{regenError}</p>
                    <button
                      onClick={handleRetryRegen}
                      className="flex items-center gap-2 px-4 py-2 rounded-lg bg-rose-50 border border-rose-200 text-rose-600 text-sm hover:bg-rose-100 transition"
                    >
                      <RefreshCw size={13} /> Retry
                    </button>
                  </div>
                )}

                {/* Draft content */}
                {regenDraft && !regenMutation.isPending && (
                  <>
                    <div className="bg-white rounded-xl border border-violet-200 p-4 shadow-sm">
                      <RenderedContent content={regenDraft.stem_md} />
                    </div>
                    {Object.entries(regenDraft.options).length > 0 && (
                      <div className="space-y-2">
                        {Object.entries(regenDraft.options).map(([key, val]) => (
                          <div key={key} className={`flex gap-3 p-3 rounded-lg border text-sm ${
                            key === regenDraft.answer
                              ? 'border-emerald-300 bg-emerald-50'
                              : 'border-gray-200 bg-white'
                          }`}>
                            <span className={`font-bold flex-shrink-0 w-5 ${
                              key === regenDraft.answer ? 'text-emerald-600' : 'text-gray-400'
                            }`}>{key}</span>
                            <RenderedContent content={val} />
                          </div>
                        ))}
                      </div>
                    )}
                    {regenDraft.section_type !== 'mcq' && (
                      <p className="text-sm text-gray-600">Answer: <span className="font-mono font-bold">{regenDraft.answer}</span></p>
                    )}
                    <button
                      onClick={handleRetryRegen}
                      className="flex items-center gap-1.5 text-xs text-violet-500 hover:text-violet-700 transition mt-2"
                    >
                      <RefreshCw size={11} /> Generate another variant
                    </button>
                  </>
                )}
              </div>
            </div>

            {/* Modal footer */}
            <div className="border-t border-gray-200 flex-shrink-0">
              {/* Verify warning — shown once a draft is ready */}
              {regenDraft && !regenMutation.isPending && (
                <div className="px-6 py-2.5 bg-amber-50 border-b border-amber-200 flex items-start gap-2">
                  <AlertCircle size={14} className="text-amber-500 flex-shrink-0 mt-0.5" />
                  <p className="text-xs text-amber-700 leading-snug">
                    <span className="font-semibold">Always verify before saving:</span> Check that the
                    answer is mathematically correct, options are distinct, and all formulas/compounds
                    are valid before accepting.
                  </p>
                </div>
              )}
              <div className="flex items-center justify-between px-6 py-4 bg-gray-50">
                <button
                  onClick={() => { setRegenModalOpen(false); setRegenDraft(null); setRegenError(null) }}
                  className="px-5 py-2 rounded-xl border border-gray-300 text-gray-600 text-sm font-medium hover:bg-gray-100 transition"
                >
                  Discard
                </button>
                <div className="flex items-center gap-3">
                  {saveMutation.isError && (
                    <p className="text-xs text-rose-500">Save failed. Try again.</p>
                  )}
                  <button
                    onClick={handleAcceptRegen}
                    disabled={!regenDraft || saveMutation.isPending || regenMutation.isPending}
                    className="flex items-center gap-2 px-6 py-2 rounded-xl bg-violet-600 text-white text-sm font-semibold
                      hover:bg-violet-700 disabled:opacity-40 disabled:cursor-not-allowed transition shadow-sm"
                  >
                    {saveMutation.isPending
                      ? <Loader2 size={14} className="animate-spin" />
                      : <CheckCircle2 size={14} />}
                    Accept &amp; Save as New Question
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

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
            <div className="px-4 py-4 border-t border-gray-200 space-y-2">
              {/* Regenerate button — hidden for diagram questions */}
              {canRegenerate && (
                <button
                  onClick={handleOpenRegen}
                  disabled={regenMutation.isPending}
                  className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg
                    border border-violet-200 text-violet-600 text-xs font-medium
                    hover:bg-violet-50 hover:border-violet-400
                    disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  title="Generate a new AI variant of this question (text-only)"
                >
                  <Sparkles size={13} />
                  AI Regenerate
                </button>
              )}

              {/* Lineage badge for AI-regenerated questions */}
              {question.generation_type === 'ai_regenerated' && (
                <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-violet-50 border border-violet-100">
                  <GitBranch size={11} className="text-violet-400" />
                  <span className="text-[11px] text-violet-500 font-medium">AI Regenerated</span>
                </div>
              )}

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

import { useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  CheckCircle2, XCircle, RefreshCw, Lock, Unlock,
  ChevronLeft, AlertCircle, Loader2, Download, FileText,
  BookOpen, BarChart2, Layers, ArrowRight, CheckCheck,
  Printer, Eye, EyeOff, Sparkles,
} from 'lucide-react'
import {
  getPaper,
  lockQuestion,
  removeQuestion,
  swapQuestion,
  getAlternatives,
  approvePaper,
  exportPaper,
} from '../api/papers'
import { regenerateQuestion, saveRegeneratedQuestion } from '../api/questions'
import type { Paper, PaperQuestionItem } from '../types/paper'
import type { QuestionDetail } from '../types/question'
import RenderedContent from '../components/question/RenderedContent'

// ── Helpers ───────────────────────────────────────────────────────────────

const OPTION_LABELS = ['A', 'B', 'C', 'D', 'E']

const DIFF_STYLE: Record<string, string> = {
  easy:   'bg-emerald-100 text-emerald-700',
  medium: 'bg-amber-100 text-amber-700',
  hard:   'bg-rose-100 text-rose-700',
}

function Pill({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <span className={`inline-block px-2 py-0.5 rounded-md text-[11px] font-medium ${className}`}>
      {children}
    </span>
  )
}

// ── Print export ──────────────────────────────────────────────────────────

function printPaper(paper: Paper, answerKeyOnly = false) {
  const win = window.open('', '_blank')
  if (!win) { alert('Allow pop-ups to export.'); return }

  const questions = [...paper.questions].sort((a, b) => a.position - b.position)

  const optionLabels = OPTION_LABELS
  const style = `
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
      * { box-sizing: border-box; margin: 0; padding: 0; }
      body { font-family: Inter, sans-serif; font-size: 14px; color: #111; padding: 32px 48px; line-height: 1.6; }
      h1 { font-size: 20px; font-weight: 700; margin-bottom: 4px; }
      .meta { font-size: 12px; color: #666; margin-bottom: 24px; border-bottom: 1px solid #ddd; padding-bottom: 12px; }
      .question { page-break-inside: avoid; margin-bottom: 28px; padding-bottom: 24px; border-bottom: 1px solid #eee; }
      .qnum { font-weight: 700; margin-right: 6px; }
      .stem { margin: 8px 0; }
      .options { margin-top: 10px; padding-left: 12px; }
      .opt { margin: 6px 0; display: flex; gap: 8px; }
      .opt-label { font-weight: 600; min-width: 22px; }
      .correct { color: #15803d; font-weight: 600; }
      .section-heading { font-size: 16px; font-weight: 700; margin: 20px 0 12px; border-top: 2px solid #111; padding-top: 12px; }
      .ak-row { display: flex; gap: 8px; align-items: center; margin: 4px 0; font-size: 13px; }
      img { max-width: 340px; display: block; margin: 8px 0; border: 1px solid #ddd; border-radius: 6px; }
      @media print { body { padding: 24px; } }
    </style>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
  `

  let body = ''
  const bp = paper.blueprint as Record<string, unknown>

  if (answerKeyOnly) {
    body = `
      <h1>${String(bp.exam_name ?? 'Paper')} — Answer Key</h1>
      <p class="meta">Subject: ${String(bp.subject ?? '—')} | Total: ${questions.length} questions | Generated from: "${paper.prompt}"</p>
      <div class="section-heading">Answer Key</div>
      ${questions.map((pq) => {
        const q = pq.question
        const ansIdx = Object.keys(q.options).indexOf(q.answer)
        const ansLabel = ansIdx >= 0 ? optionLabels[ansIdx] : q.answer
        return `<div class="ak-row"><b>Q${pq.display_number ?? pq.position}.</b> ${q.section_type === 'mcq' ? ansLabel : q.answer}</div>`
      }).join('')}
    `
  } else {
    body = `
      <h1>${String(bp.exam_name ?? 'Paper')} — ${String(bp.subject ?? '')}</h1>
      <p class="meta">Total Questions: ${questions.length} | Generated from: "${paper.prompt}"</p>
      ${questions.map((pq, idx) => {
        const q = pq.question
        const optEntries = Object.entries(q.options)
        const ansIdx = Object.keys(q.options).indexOf(q.answer)
        return `
          <div class="question">
            <span class="qnum">Q${pq.display_number ?? idx + 1}.</span>
            <span class="stem">${q.stem_md.replace(/\$\$(.*?)\$\$/gs, '\\($1\\)').replace(/\$(.*?)\$/gs, '\\($1\\)')}</span>
            ${q.images.map((img: { filename: string }) => `<img src="/api/images/${img.filename}" alt="diagram" />`).join('')}
            ${q.section_type === 'mcq' && optEntries.length > 0 ? `
              <div class="options">
                ${optEntries.map(([, v], i) => `
                  <div class="opt ${q.answer === Object.keys(q.options)[i] ? 'correct' : ''}">
                    <span class="opt-label">${optionLabels[i]}.</span>
                    <span>${v}</span>
                  </div>
                `).join('')}
              </div>
            ` : ''}
            <div style="margin-top:8px;font-size:12px;color:#888;">
              Chapter: ${q.chapter ?? '—'} | Difficulty: ${q.difficulty ?? '—'} | Answer: <b>${q.section_type === 'mcq' && ansIdx >= 0 ? optionLabels[ansIdx] : q.answer}</b>
            </div>
          </div>
        `
      }).join('')}
    `
  }

  win.document.write(`<!DOCTYPE html><html><head><meta charset="utf-8"><title>Export</title>${style}</head><body>${body}</body></html>`)
  win.document.close()
  setTimeout(() => win.print(), 800)
}

// ── AI Regeneration panel (inline, below question) ──────────────────

function AIRegenPanel({
  questionId, paperId, pqId, onSwap, onCancel,
}: {
  questionId: string
  paperId: string
  pqId: string
  onSwap: () => void
  onCancel: () => void
}) {
  const qc = useQueryClient()
  const [provider, setProvider] = useState<'ollama' | 'groq'>(
    () => (localStorage.getItem('regenProvider') as 'ollama' | 'groq') || 'ollama'
  )
  const [draft, setDraft] = useState<{ stem_md: string; options: Record<string, string>; answer: string; section_type: string } | null>(null)
  const [error, setError] = useState<string | null>(null)

  const regenMut = useMutation({
    mutationFn: (p: 'ollama' | 'groq') => regenerateQuestion(questionId, p),
    onSuccess: (d) => { setDraft(d as typeof draft); setError(null) },
    onError: (e: Error) => setError(e.message || 'Generation failed. Try again.'),
  })

  const saveMut = useMutation({
    mutationFn: async () => {
      if (!draft) throw new Error('No draft')
      // 1. Save as a new question in the DB
      const saved = await saveRegeneratedQuestion(questionId, {
        stem_md: draft.stem_md,
        options: draft.options,
        answer: draft.answer,
      })
      // 2. Swap it into the paper slot
      await swapQuestion(paperId, pqId, (saved as { id: string }).id)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['paper', paperId] })
      onSwap()
    },
    onError: (e: Error) => setError(e.message || 'Save failed.'),
  })

  const handleGenerate = (p: 'ollama' | 'groq' = provider) => {
    localStorage.setItem('regenProvider', p)
    setError(null)
    regenMut.mutate(p)
  }

  const switchProvider = (p: 'ollama' | 'groq') => {
    if (p === provider) return
    setProvider(p)
    setError(null)
    // If a draft already exists, auto-generate with new provider
    if (draft || regenMut.isPending) {
      setDraft(null)
      handleGenerate(p)
    }
  }

  const optionEntries = Object.entries(draft?.options ?? {})

  return (
    <div className="border-t border-gray-100 bg-violet-50/40 p-4 space-y-4">
      {/* Panel header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles size={14} className="text-violet-500" />
          <span className="text-xs font-semibold text-violet-700">AI Regeneration</span>
        </div>
        <div className="flex items-center gap-2">
          {/* Provider toggle */}
          <div className="flex items-center bg-white border border-gray-200 rounded-lg p-0.5 gap-0.5">
            {(['ollama', 'groq'] as const).map((p) => (
              <button
                key={p}
                onClick={() => switchProvider(p)}
                disabled={regenMut.isPending || saveMut.isPending}
                className={`px-2.5 py-1 rounded-md text-[11px] font-semibold transition-all ${
                  provider === p ? 'bg-violet-600 text-white shadow-sm' : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                {p === 'ollama' ? '🖥 Ollama' : '⚡ Groq'}
              </button>
            ))}
          </div>
          <button onClick={onCancel} className="text-xs text-gray-400 hover:text-gray-600 transition">Cancel</button>
        </div>
      </div>

      {/* Idle: no generation started */}
      {!regenMut.isPending && !draft && !error && (
        <div className="flex flex-col items-center gap-3 py-4">
          <p className="text-xs text-gray-500">Select provider and generate a variant of this question.</p>
          <button
            onClick={() => handleGenerate()}
            className="flex items-center gap-2 px-5 py-2 rounded-xl bg-violet-600 text-white text-xs font-semibold hover:bg-violet-700 transition shadow-sm"
          >
            <Sparkles size={12} /> Generate Variant
          </button>
        </div>
      )}

      {/* Loading */}
      {regenMut.isPending && (
        <div className="flex items-center gap-3 py-3 justify-center">
          <Loader2 size={16} className="animate-spin text-violet-500" />
          <span className="text-xs text-violet-600 font-medium">
            {provider === 'groq' ? 'Calling Groq… usually fast!' : 'Ollama thinking… may take 30s+'}
          </span>
        </div>
      )}

      {/* Error */}
      {error && !regenMut.isPending && (
        <div className="flex items-center gap-3 bg-rose-50 border border-rose-200 rounded-xl p-3">
          <AlertCircle size={14} className="text-rose-500 flex-shrink-0" />
          <p className="text-xs text-rose-600 flex-1">{error}</p>
          <button
            onClick={() => handleGenerate()}
            className="text-xs text-rose-600 font-semibold hover:underline"
          >Retry</button>
        </div>
      )}

      {/* Draft preview */}
      {draft && !regenMut.isPending && (
        <div className="space-y-3">
          {/* Verify warning */}
          <div className="flex items-start gap-2 bg-amber-50 border border-amber-200 rounded-xl p-2.5">
            <AlertCircle size={12} className="text-amber-500 flex-shrink-0 mt-0.5" />
            <p className="text-[11px] text-amber-700 leading-snug">
              <span className="font-semibold">Verify before swapping:</span> Check the answer is correct and formulas are valid.
            </p>
          </div>
          <div className="bg-white rounded-xl border border-violet-200 p-3 text-sm">
            <RenderedContent content={draft.stem_md} />
          </div>
          {optionEntries.length > 0 && (
            <div className="space-y-1.5">
              {optionEntries.map(([key, val]) => (
                <div key={key} className={`flex gap-2 px-3 py-2 rounded-lg border text-xs ${
                  key === draft.answer ? 'border-emerald-300 bg-emerald-50 text-emerald-800' : 'border-gray-200 bg-white text-gray-700'
                }`}>
                  <span className={`font-bold flex-shrink-0 w-4 ${key === draft.answer ? 'text-emerald-600' : 'text-gray-400'}`}>{key}</span>
                  <RenderedContent content={val} />
                </div>
              ))}
            </div>
          )}
          {draft.section_type !== 'mcq' && (
            <p className="text-xs text-gray-600">Answer: <span className="font-mono font-bold">{draft.answer}</span></p>
          )}
          <div className="flex items-center gap-2 pt-1">
            <button
              onClick={() => { setDraft(null); handleGenerate() }}
              className="flex items-center gap-1 text-[11px] text-violet-500 hover:text-violet-700 transition"
            >
              <RefreshCw size={10} /> Generate another
            </button>
            <div className="flex-1" />
            <button
              onClick={() => saveMut.mutate()}
              disabled={saveMut.isPending}
              className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-violet-600 text-white text-xs font-semibold hover:bg-violet-700 disabled:opacity-50 transition"
            >
              {saveMut.isPending ? <Loader2 size={11} className="animate-spin" /> : <CheckCircle2 size={11} />}
              Accept &amp; Swap into Paper
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Alternative question picker ───────────────────────────────────────────

function AlternativePicker({
  paperId, pqId,
  onSwap, onCancel,
}: {
  paperId: string
  pqId: string
  onSwap: () => void
  onCancel: () => void
}) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['alternatives', paperId, pqId],
    queryFn: () => getAlternatives(paperId, pqId),
  })
  const qc = useQueryClient()
  const swap = useMutation({
    mutationFn: (newId: string) => swapQuestion(paperId, pqId, newId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['paper', paperId] })
      onSwap()
    },
  })

  if (isLoading) return (
    <div className="flex items-center gap-2 p-4 text-gray-500 text-sm">
      <Loader2 size={15} className="animate-spin" /> Finding alternatives…
    </div>
  )
  if (isError || !data?.alternatives?.length) return (
    <div className="p-4 text-sm text-gray-500">No alternatives found.</div>
  )

  return (
    <div className="border-t border-gray-100 bg-indigo-50/50 p-4 space-y-3">
      <div className="flex items-center justify-between mb-1">
        <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide">
          Choose a replacement ({data.alternatives.length} found)
        </p>
        <button onClick={onCancel} className="text-xs text-gray-400 hover:text-gray-600">Cancel</button>
      </div>
      {data.alternatives.map((alt: QuestionDetail) => (
        <div key={alt.id} className="bg-white rounded-xl border border-gray-200 p-4 flex items-start gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex gap-1.5 mb-2 flex-wrap">
              {alt.chapter && <Pill className="bg-indigo-100 text-indigo-700">{alt.chapter}</Pill>}
              {alt.difficulty && <Pill className={DIFF_STYLE[alt.difficulty] ?? 'bg-gray-100 text-gray-600'}>{alt.difficulty}</Pill>}
              {alt.question_type && <Pill className="bg-gray-100 text-gray-600">{alt.question_type}</Pill>}
            </div>
            <div className="text-sm text-gray-800 line-clamp-3">
              <RenderedContent content={alt.stem_md} />
            </div>
          </div>
          <button
            onClick={() => swap.mutate(alt.id)}
            disabled={swap.isPending}
            className="flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600
              text-white text-xs rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition"
          >
            {swap.isPending ? <Loader2 size={12} className="animate-spin" /> : <ArrowRight size={12} />}
            Use this
          </button>
        </div>
      ))}
    </div>
  )
}

// ── Single question card ──────────────────────────────────────────────────

function QuestionCard({
  pq, paperId, showAnswers,
}: {
  pq: PaperQuestionItem
  paperId: string
  showAnswers: boolean
}) {
  const qc = useQueryClient()
  const [showAlt, setShowAlt] = useState(false)
  const [showAIRegen, setShowAIRegen] = useState(false)
  const q = pq.question
  // Hide AI regen button for questions with images (V1 rule)
  const hasImages = q.images && q.images.length > 0

  const lockMut = useMutation({
    mutationFn: () => lockQuestion(paperId, pq.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['paper', paperId] }),
  })
  const removeMut = useMutation({
    mutationFn: () => removeQuestion(paperId, pq.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['paper', paperId] }),
  })

  const optEntries = Object.entries(q.options)
  const ansIdx = Object.keys(q.options).indexOf(q.answer)

  return (
    <div className={`bg-white rounded-2xl border-2 transition-colors ${pq.locked ? 'border-emerald-300' : 'border-gray-200'}`}>
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100">
        <div className="flex items-center gap-3">
          <span className="text-base font-bold text-gray-800">Q{pq.display_number ?? pq.position}</span>
          {q.chapter && (
            <span className="flex items-center gap-1 text-xs text-gray-500">
              <BookOpen size={11} /> {q.chapter}
            </span>
          )}
          {q.difficulty && (
            <Pill className={DIFF_STYLE[q.difficulty] ?? 'bg-gray-100 text-gray-600'}>
              <BarChart2 size={10} className="inline mr-1" />
              {q.difficulty}
            </Pill>
          )}
          {q.section_type && (
            <Pill className="bg-violet-100 text-violet-700">
              <Layers size={10} className="inline mr-1" />
              {q.section_type.toUpperCase()}
            </Pill>
          )}
          {q.question_type && (
            <Pill className="bg-gray-100 text-gray-600">{q.question_type}</Pill>
          )}
          {pq.paper_section && (
            <Pill className="bg-slate-100 text-slate-600">{pq.paper_section}</Pill>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1">
          {/* AI Regenerate (hidden for questions with images) */}
          {!hasImages && (
            <button
              onClick={() => { setShowAIRegen(!showAIRegen); setShowAlt(false) }}
              title="AI Regenerate question"
              className={`p-2 rounded-lg text-sm transition ${
                showAIRegen ? 'bg-violet-100 text-violet-700' : 'text-gray-400 hover:bg-violet-50 hover:text-violet-600'
              }`}
            >
              <Sparkles size={15} />
            </button>
          )}

          {/* Swap with alternative */}
          <button
            onClick={() => { setShowAlt(!showAlt); setShowAIRegen(false) }}
            title="Swap with alternative from question bank"
            className={`p-2 rounded-lg text-sm transition ${
              showAlt ? 'bg-indigo-100 text-indigo-700' : 'text-gray-400 hover:bg-gray-100 hover:text-gray-700'
            }`}
          >
            <RefreshCw size={15} />
          </button>

          {/* Lock / Unlock */}
          <button
            onClick={() => lockMut.mutate()}
            disabled={lockMut.isPending}
            title={pq.locked ? 'Unlock question' : 'Approve (lock) question'}
            className={`p-2 rounded-lg transition ${
              pq.locked
                ? 'bg-emerald-100 text-emerald-700 hover:bg-emerald-200'
                : 'text-gray-400 hover:bg-emerald-50 hover:text-emerald-600'
            }`}
          >
            {lockMut.isPending ? (
              <Loader2 size={15} className="animate-spin" />
            ) : pq.locked ? (
              <Lock size={15} />
            ) : (
              <Unlock size={15} />
            )}
          </button>

          {/* Remove */}
          <button
            onClick={() => { if (confirm('Remove this question from the draft?')) removeMut.mutate() }}
            disabled={removeMut.isPending}
            title="Remove question"
            className="p-2 rounded-lg text-gray-400 hover:bg-rose-50 hover:text-rose-600 transition"
          >
            {removeMut.isPending ? (
              <Loader2 size={15} className="animate-spin" />
            ) : (
              <XCircle size={15} />
            )}
          </button>
        </div>
      </div>

      {/* Question body */}
      <div className="px-5 py-4">
        <RenderedContent content={q.stem_md} />

        {/* Diagram */}
        {q.images?.filter((img: { position: string }) => img.position === 'stem').map((img: { filename: string }) => (
          <img
            key={img.filename}
            src={`/api/images/${img.filename}`}
            alt="diagram"
            className="mt-3 max-w-sm rounded-xl border border-gray-200"
          />
        ))}

        {/* MCQ options */}
        {q.section_type === 'mcq' && optEntries.length > 0 && (
          <div className="mt-4 space-y-2">
            {optEntries.map(([key, value], i) => {
              const isCorrect = key === q.answer
              return (
                <div
                  key={key}
                  className={`flex items-start gap-3 px-3 py-2.5 rounded-xl border text-sm transition-colors ${
                    showAnswers && isCorrect
                      ? 'border-emerald-400 bg-emerald-50 text-emerald-800'
                      : 'border-gray-150 bg-gray-50/60 text-gray-700'
                  }`}
                >
                  <span className={`flex-shrink-0 w-6 h-6 rounded-full text-xs font-bold flex items-center justify-center mt-0.5 ${
                    showAnswers && isCorrect
                      ? 'bg-emerald-500 text-white'
                      : 'bg-gray-200 text-gray-600'
                  }`}>
                    {OPTION_LABELS[i]}
                  </span>
                  {showAnswers && isCorrect && <CheckCircle2 size={15} className="text-emerald-500 flex-shrink-0 mt-0.5" />}
                  <div className="flex-1 min-w-0">
                    <RenderedContent content={String(value)} />
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {/* Integer answer */}
        {q.section_type === 'integer' && showAnswers && (
          <div className="mt-4 flex items-center gap-2">
            <span className="text-xs text-gray-500 font-medium">Answer:</span>
            <span className="px-3 py-1.5 bg-emerald-50 border border-emerald-300 rounded-lg font-mono font-bold text-emerald-700">
              {q.answer}
            </span>
          </div>
        )}
      </div>

      {/* AI Regen panel */}
      {showAIRegen && (
        <AIRegenPanel
          questionId={q.id}
          paperId={paperId}
          pqId={pq.id}
          onSwap={() => setShowAIRegen(false)}
          onCancel={() => setShowAIRegen(false)}
        />
      )}

      {/* Alternative picker */}
      {showAlt && (
        <AlternativePicker
          paperId={paperId}
          pqId={pq.id}
          onSwap={() => setShowAlt(false)}
          onCancel={() => setShowAlt(false)}
        />
      )}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────

export default function PaperDraft() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [showAnswers, setShowAnswers] = useState(false)

  const { data: paper, isLoading, isError } = useQuery({
    queryKey: ['paper', id],
    queryFn: () => getPaper(id!),
    enabled: !!id,
    refetchOnWindowFocus: false,
  })

  const approveMut = useMutation({
    mutationFn: (notes: string) => approvePaper(id!, notes || undefined),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['paper', id] }),
  })

  const exportMut = useMutation({
    mutationFn: () => {
      if (paper!.status === 'approved') {
        // Use backend Markdown export for approved papers
        return exportPaper(id!).then((md) => {
          const blob = new Blob([md], { type: 'text/markdown' })
          const url = URL.createObjectURL(blob)
          const a = document.createElement('a')
          a.href = url
          a.download = `paper_${id?.slice(0, 8)}.md`
          a.click()
          URL.revokeObjectURL(url)
        })
      } else {
        // Client-side Markdown for draft
        const qs = [...paper!.questions].sort((a, b) => a.position - b.position)
        const bp = paper!.blueprint as Record<string, unknown>
        const lines: string[] = [
          `# ${String(bp.exam_name ?? 'Paper')} — ${String(bp.subject ?? '')}`,
          ``,
          `> Prompt: "${paper!.prompt}"`,
          `> Questions: ${qs.length} | Status: ${paper!.status}`,
          ``,
        ]
        qs.forEach((pq, idx) => {
          const q = pq.question
          lines.push(`## Q${pq.display_number ?? idx + 1}.`)
          lines.push(``)
          lines.push(q.stem_md)
          lines.push(``)
          Object.entries(q.options).forEach(([, v], i) => {
            const label = ['A', 'B', 'C', 'D', 'E'][i]
            const isAns = Object.keys(q.options)[i] === q.answer
            lines.push(`- **${label}.** ${v}${isAns ? ' ✅' : ''}`)
          })
          lines.push(``)
          lines.push(`*Chapter: ${q.chapter ?? '—'} | Difficulty: ${q.difficulty ?? '—'} | Answer: ${q.answer}*`)
          lines.push(``)
          lines.push(`---`)
          lines.push(``)
        })
        const blob = new Blob([lines.join('\n')], { type: 'text/markdown' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `draft_${id?.slice(0, 8)}.md`
        a.click()
        URL.revokeObjectURL(url)
        return Promise.resolve()
      }
    },
  })

  if (isLoading) return (
    <div className="flex items-center justify-center h-64 gap-3 text-gray-500">
      <Loader2 className="animate-spin" size={22} /> Loading draft…
    </div>
  )
  if (isError || !paper) return (
    <div className="p-8">
      <div className="flex items-center gap-3 text-rose-600 bg-rose-50 rounded-xl p-4">
        <AlertCircle size={20} />
        <p className="text-sm font-semibold">Failed to load paper. Check the paper ID.</p>
      </div>
    </div>
  )

  const qs = [...paper.questions].sort((a, b) => a.position - b.position)
  const total    = qs.length
  const locked   = qs.filter((q) => q.locked).length
  const pending  = total - locked
  const allDone  = total > 0 && pending === 0

  return (
    <div className="min-h-screen bg-slate-50">

      {/* ── Top bar ───────────────────────────────────────────────── */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10 px-8 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/papers')}
            className="text-gray-400 hover:text-gray-700 transition p-1"
          >
            <ChevronLeft size={20} />
          </button>
          <div>
            <p className="text-sm font-bold text-gray-800 truncate max-w-lg">{paper.prompt}</p>
            <p className="text-xs text-gray-400 mt-0.5">
              Draft · {total} questions · {(paper.blueprint as Record<string, unknown>).exam_name as string ?? '—'} · {(paper.blueprint as Record<string, unknown>).subject as string ?? '—'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Toggle answers */}
          <button
            onClick={() => setShowAnswers(!showAnswers)}
            className={`flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg border transition ${
              showAnswers ? 'bg-indigo-50 border-indigo-300 text-indigo-700' : 'border-gray-200 text-gray-600 hover:bg-gray-50'
            }`}
          >
            {showAnswers ? <EyeOff size={14} /> : <Eye size={14} />}
            {showAnswers ? 'Hide Answers' : 'Show Answers'}
          </button>

          {/* Export Markdown */}
          <button
            onClick={() => exportMut.mutate()}
            disabled={exportMut.isPending}
            className="flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 transition"
          >
            {exportMut.isPending ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
            Export .md
          </button>

          {/* Print paper */}
          <button
            onClick={() => printPaper(paper, false)}
            className="flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 transition"
          >
            <Printer size={14} />
            Print Paper
          </button>

          {/* Print answer key */}
          <button
            onClick={() => printPaper(paper, true)}
            className="flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 transition"
          >
            <FileText size={14} />
            Answer Key
          </button>

          {/* Approve paper */}
          {paper.status !== 'approved' && (
            <button
              onClick={() => approveMut.mutate('')}
              disabled={approveMut.isPending || total === 0}
              className="flex items-center gap-2 px-4 py-1.5 text-sm rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-40 transition font-semibold"
            >
              {approveMut.isPending ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <CheckCheck size={14} />
              )}
              {allDone ? 'Approve Paper' : `Approve (${pending} pending)`}
            </button>
          )}
          {paper.status === 'approved' && (
            <span className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-100 text-emerald-700 text-sm rounded-lg font-semibold">
              <CheckCircle2 size={14} /> Approved
            </span>
          )}
        </div>
      </div>

      <div className="flex">

        {/* ── Questions ─────────────────────────────────────────────── */}
        <main className="flex-1 px-8 py-6 space-y-5">
          {qs.length === 0 && (
            <div className="text-center py-16 text-gray-400">
              <AlertCircle className="mx-auto mb-3" size={32} />
              <p>All questions have been removed.</p>
              <Link to="/papers" className="text-indigo-600 text-sm mt-2 inline-block hover:underline">
                ← Back to generator
              </Link>
            </div>
          )}

          {qs.map((pq) => (
            <div key={pq.id} data-pq={pq.id}>
              <QuestionCard
                pq={pq}
                paperId={id!}
                showAnswers={showAnswers}
              />
            </div>
          ))}
        </main>

        {/* ── Right sidebar ──────────────────────────────────────────── */}
        <aside className="w-56 flex-shrink-0 border-l border-gray-200 bg-white sticky top-16 h-[calc(100vh-64px)] overflow-y-auto">
          <div className="p-4">
            {/* Status counters */}
            <div className="space-y-2 mb-5">
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-500">Total</span>
                <span className="font-bold text-gray-800">{total}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-1 text-emerald-600">
                  <Lock size={12} /> Approved
                </span>
                <span className="font-bold text-emerald-700">{locked}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-1 text-gray-500">
                  <Unlock size={12} /> Pending
                </span>
                <span className="font-bold text-gray-700">{pending}</span>
              </div>
            </div>

            {/* Progress bar */}
            <div className="w-full h-2 bg-gray-100 rounded-full mb-5">
              <div
                className="h-2 bg-emerald-400 rounded-full transition-all"
                style={{ width: total ? `${(locked / total) * 100}%` : '0%' }}
              />
            </div>

            {/* Paper status */}
            <div className={`text-center py-2 px-3 rounded-xl text-xs font-semibold mb-4 ${
              paper.status === 'approved'
                ? 'bg-emerald-100 text-emerald-700'
                : 'bg-amber-100 text-amber-700'
            }`}>
              {paper.status === 'approved' ? '✅ Approved' : '🔄 Draft'}
            </div>

            {/* Blueprint info */}
            <div className="space-y-2">
              <p className="text-[10px] uppercase tracking-widest text-gray-400 font-semibold">Blueprint</p>
              {Object.entries(paper.blueprint as Record<string, unknown>)
                .filter(([k]) => ['exam_name', 'subject', 'total_questions', 'seed'].includes(k))
                .map(([k, v]) => (
                  <div key={k} className="flex justify-between text-xs">
                    <span className="text-gray-500 capitalize">{k.replace(/_/g, ' ')}</span>
                    <span className="text-gray-800 font-medium text-right max-w-24 truncate">{String(v)}</span>
                  </div>
                ))}
            </div>

            {/* Mini question palette */}
            <div className="mt-5">
              <p className="text-[10px] uppercase tracking-widest text-gray-400 font-semibold mb-2">Questions</p>
              <div className="flex flex-wrap gap-1">
                {qs.map((pq, i) => (
                  <button
                    key={pq.id}
                    onClick={() => {
                      document.querySelectorAll(`[data-pq="${pq.id}"]`)[0]?.scrollIntoView({ behavior: 'smooth', block: 'start' })
                    }}
                    title={`Q${pq.display_number ?? i + 1} — ${pq.question?.chapter ?? ''}`}
                    className={`w-7 h-7 rounded text-[11px] font-semibold transition ${
                      pq.locked
                        ? 'bg-emerald-100 text-emerald-700 ring-1 ring-emerald-400'
                        : pq.question?.difficulty === 'easy'
                          ? 'bg-emerald-50 text-emerald-600'
                          : pq.question?.difficulty === 'hard'
                            ? 'bg-rose-100 text-rose-700'
                            : 'bg-amber-100 text-amber-700'
                    }`}
                  >
                    {i + 1}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </aside>

      </div>
    </div>
  )
}

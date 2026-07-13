import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Wand2, Loader2, AlertCircle, CheckCircle2, ChevronRight,
  BookOpen, BarChart2, Layers, Tag, AlertTriangle, FileText,
  ArrowRight, XCircle,
} from 'lucide-react'
import { syllabusQuery } from '../api/papers'
import type { SyllabusQueryResponse } from '../types/paper'

// ── Small helpers ─────────────────────────────────────────────────────────

const EXAMPLE_PROMPTS = [
  'Generate 30 JEE Main Physics questions till Rotational Motion.',
  'Generate 20 easy Chemistry questions from Organic Chemistry.',
  'Generate 15 Maths numerical questions.',
  'Generate 25 Physics questions after Thermodynamics, exclude Oscillations.',
  'Generate 40 NEET Biology questions from Genetics to Biotechnology.',
]

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[11px] uppercase tracking-widest font-semibold text-gray-400 mb-2">
      {children}
    </p>
  )
}

function Pill({
  children, color = 'gray',
}: {
  children: React.ReactNode
  color?: 'gray' | 'indigo' | 'emerald' | 'amber' | 'rose' | 'violet' | 'sky'
}) {
  const map: Record<string, string> = {
    gray:    'bg-gray-100 text-gray-700',
    indigo:  'bg-indigo-100 text-indigo-700',
    emerald: 'bg-emerald-100 text-emerald-700',
    amber:   'bg-amber-100 text-amber-700',
    rose:    'bg-rose-100 text-rose-700',
    violet:  'bg-violet-100 text-violet-700',
    sky:     'bg-sky-100 text-sky-700',
  }
  return (
    <span className={`inline-block px-2.5 py-1 rounded-lg text-xs font-medium ${map[color]}`}>
      {children}
    </span>
  )
}

function StatBox({
  label, value, sub, color = 'gray',
}: {
  label: string
  value: string | number
  sub?: string
  color?: 'gray' | 'indigo' | 'emerald' | 'amber' | 'rose'
}) {
  const border: Record<string, string> = {
    gray:    'border-gray-200',
    indigo:  'border-indigo-300',
    emerald: 'border-emerald-300',
    amber:   'border-amber-300',
    rose:    'border-rose-300',
  }
  const text: Record<string, string> = {
    gray:    'text-gray-800',
    indigo:  'text-indigo-700',
    emerald: 'text-emerald-700',
    amber:   'text-amber-700',
    rose:    'text-rose-700',
  }
  return (
    <div className={`bg-white border-2 ${border[color]} rounded-xl p-4 text-center`}>
      <p className={`text-2xl font-bold ${text[color]}`}>{value}</p>
      <p className="text-xs font-medium text-gray-500 mt-0.5">{label}</p>
      {sub && <p className="text-[11px] text-gray-400 mt-0.5">{sub}</p>}
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────

export default function PaperGenerator() {
  const navigate = useNavigate()
  const [prompt, setPrompt] = useState('')
  const [status, setStatus] = useState<'idle' | 'loading' | 'done' | 'error'>('idle')
  const [result, setResult] = useState<SyllabusQueryResponse | null>(null)
  const [errorMsg, setErrorMsg] = useState('')

  const handlePreview = async () => {
    if (!prompt.trim()) return
    setStatus('loading')
    setResult(null)
    setErrorMsg('')
    try {
      const data = await syllabusQuery(prompt.trim())
      setResult(data)
      setStatus('done')
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string | { message?: string } } } }
      const detail = e?.response?.data?.detail
      if (typeof detail === 'object' && detail !== null && 'message' in detail) {
        setErrorMsg((detail as { message: string }).message)
      } else {
        setErrorMsg(typeof detail === 'string' ? detail : 'Preview failed. Check the API server.')
      }
      setStatus('error')
    }
  }

  const bp = result?.candidates.resolved_blueprint

  return (
    <div className="p-8 max-w-4xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Paper Generator</h1>
        <p className="text-sm text-gray-500 mt-1">
          Describe the paper you want. The backend resolves chapter order, selects questions,
          and creates a draft for your review.
        </p>
      </div>

      {/* ── Prompt input ────────────────────────────────────────────── */}
      <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm mb-6">
        <SectionLabel>Natural Language Prompt</SectionLabel>

        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          rows={3}
          placeholder="e.g. Generate 30 JEE Main Physics questions till Rotational Motion."
          className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm resize-none
            focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent
            placeholder:text-gray-300"
          onKeyDown={(e) => {
            if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) handlePreview()
          }}
        />

        {/* Example prompts */}
        <div className="mt-3">
          <p className="text-[11px] text-gray-400 mb-2">Examples — click to use:</p>
          <div className="flex flex-wrap gap-2">
            {EXAMPLE_PROMPTS.map((ex) => (
              <button
                key={ex}
                onClick={() => setPrompt(ex)}
                className="text-[11px] px-2.5 py-1 bg-gray-50 border border-gray-200
                  rounded-lg text-gray-600 hover:bg-indigo-50 hover:border-indigo-300
                  hover:text-indigo-700 transition text-left"
              >
                {ex}
              </button>
            ))}
          </div>
        </div>

        <div className="mt-4 flex items-center gap-3">
          <button
            onClick={handlePreview}
            disabled={!prompt.trim() || status === 'loading'}
            className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 text-white
              text-sm font-semibold rounded-xl hover:bg-indigo-700 disabled:opacity-40
              disabled:cursor-not-allowed transition shadow-sm"
          >
            {status === 'loading' ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Wand2 size={16} />
            )}
            {status === 'loading' ? 'Analysing…' : 'Preview'}
          </button>
          <span className="text-xs text-gray-400">or Ctrl+Enter</span>
        </div>
      </div>

      {/* ── Error ────────────────────────────────────────────────────── */}
      {status === 'error' && (
        <div className="flex items-start gap-3 bg-rose-50 border border-rose-200 rounded-xl p-4 mb-6">
          <AlertCircle className="text-rose-500 flex-shrink-0 mt-0.5" size={18} />
          <div>
            <p className="text-sm font-semibold text-rose-700">Preview failed</p>
            <p className="text-sm text-rose-600 mt-0.5">{errorMsg}</p>
          </div>
        </div>
      )}

      {/* ── Preview results ─────────────────────────────────────────── */}
      {status === 'done' && result && (
        <div className="space-y-5">

          {/* ── Parsed query summary ───────────────────────────────── */}
          <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm">
            <SectionLabel>Parsed Query</SectionLabel>
            <div className="flex flex-wrap gap-2">
              {bp?.exam_name && <Pill color="indigo">{bp.exam_name}</Pill>}
              {bp?.subject && <Pill color="sky">{bp.subject}</Pill>}
              {bp?.chapter_filter_mode && bp.chapter_filter_mode !== 'all' && (
                <Pill color="violet">mode: {bp.chapter_filter_mode}</Pill>
              )}
              {bp?.difficulty && <Pill color="amber">difficulty: {bp.difficulty}</Pill>}
              {bp?.question_type && <Pill color="gray">type: {bp.question_type}</Pill>}
              {bp?.section_type && <Pill color="gray">{bp.section_type.toUpperCase()}</Pill>}
              {bp?.has_diagram && <Pill color="sky">has diagram</Pill>}
              {bp?.has_formula && <Pill color="violet">has formula</Pill>}
            </div>

            {bp?.chapter_range_description && (
              <p className="mt-3 text-sm text-gray-600 bg-gray-50 rounded-lg px-3 py-2">
                <span className="font-medium">Range: </span>
                {bp.chapter_range_description}
              </p>
            )}

            {/* Resolver warnings */}
            {bp?.resolver_warnings && bp.resolver_warnings.length > 0 && (
              <div className="mt-3 space-y-1">
                {bp.resolver_warnings.map((w, i) => (
                  <div key={i} className="flex items-start gap-2 text-amber-700 bg-amber-50 rounded-lg px-3 py-2 text-xs">
                    <AlertTriangle size={13} className="flex-shrink-0 mt-0.5" />
                    {w}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* ── Candidate stats ─────────────────────────────────────── */}
          <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm">
            <SectionLabel>Candidates Available</SectionLabel>
            <div className="grid grid-cols-4 gap-3 mb-5">
              <StatBox
                label="Available"
                value={result.candidates.total_available}
                color={result.candidates.can_generate ? 'emerald' : 'rose'}
              />
              <StatBox
                label="Requested"
                value={bp?.question_count ?? '—'}
                color="indigo"
              />
              {result.candidates.shortage > 0 && (
                <StatBox
                  label="Shortage"
                  value={result.candidates.shortage}
                  color="rose"
                />
              )}
              <StatBox
                label="Chapters"
                value={bp?.resolved_chapters.length ?? 0}
              />
            </div>

            {/* Not enough questions */}
            {!result.candidates.can_generate && (
              <div className="flex items-center gap-3 bg-rose-50 border border-rose-200 rounded-xl p-4">
                <XCircle className="text-rose-500 flex-shrink-0" size={20} />
                <div>
                  <p className="text-sm font-semibold text-rose-700">Not enough questions</p>
                  <p className="text-xs text-rose-600 mt-0.5">
                    Only {result.candidates.total_available} questions match your filters,
                    but you requested {bp?.question_count}. Broaden the chapter range,
                    reduce the count, or ingest more PDFs.
                  </p>
                </div>
              </div>
            )}

            {/* Difficulty breakdown */}
            {Object.keys(result.candidates.by_difficulty).length > 0 && (
              <div className="mt-4">
                <p className="text-[11px] text-gray-400 mb-2 font-medium">By Difficulty</p>
                <div className="flex gap-2 flex-wrap">
                  {Object.entries(result.candidates.by_difficulty).map(([d, n]) => {
                    const col: Record<string, string> = {
                      easy: 'bg-emerald-100 text-emerald-700',
                      medium: 'bg-amber-100 text-amber-700',
                      hard: 'bg-rose-100 text-rose-700',
                    }
                    return (
                      <span key={d} className={`px-3 py-1 rounded-lg text-xs font-semibold ${col[d] ?? 'bg-gray-100 text-gray-600'}`}>
                        {d}: {n}
                      </span>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Chapter breakdown */}
            {Object.keys(result.candidates.by_chapter).length > 0 && (
              <div className="mt-4">
                <p className="text-[11px] text-gray-400 mb-2 font-medium">By Chapter</p>
                <div className="grid grid-cols-2 gap-1">
                  {Object.entries(result.candidates.by_chapter)
                    .sort(([, a], [, b]) => b - a)
                    .map(([ch, n]) => (
                      <div key={ch} className="flex items-center justify-between text-xs text-gray-600 bg-gray-50 px-3 py-1.5 rounded-lg">
                        <span className="truncate mr-2">{ch}</span>
                        <span className="font-semibold flex-shrink-0">{n}</span>
                      </div>
                    ))}
                </div>
              </div>
            )}

            {/* Resolved chapters */}
            {bp?.resolved_chapters && bp.resolved_chapters.length > 0 && (
              <div className="mt-4">
                <p className="text-[11px] text-gray-400 mb-2 font-medium">
                  Resolved Chapters ({bp.resolved_chapters.length})
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {bp.resolved_chapters.map((ch, i) => (
                    <span key={ch} className="text-[11px] bg-indigo-50 text-indigo-700 border border-indigo-100 px-2 py-0.5 rounded-md">
                      {i + 1}. {ch}
                    </span>
                  ))}
                </div>
                {bp.excluded_chapters.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {bp.excluded_chapters.map((ch) => (
                      <span key={ch} className="text-[11px] bg-rose-50 text-rose-600 border border-rose-100 px-2 py-0.5 rounded-md line-through">
                        {ch}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* ── 5 sample questions ──────────────────────────────────── */}
          {result.candidates.sample_questions.length > 0 && (
            <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm">
              <SectionLabel>Sample Questions (first 5)</SectionLabel>
              <div className="space-y-3">
                {result.candidates.sample_questions.map((q, i) => (
                  <div key={q.id} className="flex items-start gap-3 p-3 bg-gray-50 rounded-xl">
                    <span className="flex-shrink-0 w-7 h-7 bg-indigo-100 text-indigo-700 rounded-full flex items-center justify-center text-xs font-bold">
                      {i + 1}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-gray-800 leading-snug">{q.stem_preview}</p>
                      <div className="flex gap-2 mt-1.5 flex-wrap">
                        {q.chapter && (
                          <span className="flex items-center gap-1 text-[11px] text-gray-500">
                            <BookOpen size={10} /> {q.chapter}
                          </span>
                        )}
                        {q.difficulty && (
                          <span className="flex items-center gap-1 text-[11px] text-gray-500">
                            <BarChart2 size={10} /> {q.difficulty}
                          </span>
                        )}
                        {q.question_type && (
                          <span className="flex items-center gap-1 text-[11px] text-gray-500">
                            <Tag size={10} /> {q.question_type}
                          </span>
                        )}
                        {q.question_number && (
                          <span className="flex items-center gap-1 text-[11px] text-gray-500">
                            <Layers size={10} /> Q{q.question_number}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ── CTA: Go to draft ────────────────────────────────────── */}
          {result.candidates.can_generate && result.paper_id && (
            <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-6 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <CheckCircle2 className="text-emerald-500" size={24} />
                <div>
                  <p className="text-sm font-semibold text-emerald-800">Draft paper created</p>
                  <p className="text-xs text-emerald-600 mt-0.5">
                    {bp?.question_count} questions selected and saved as a draft.
                    Review and approve each question below.
                  </p>
                </div>
              </div>
              <button
                onClick={() => navigate(`/papers/${result.paper_id}`)}
                className="flex items-center gap-2 px-5 py-2.5 bg-emerald-600 text-white
                  text-sm font-semibold rounded-xl hover:bg-emerald-700 transition
                  shadow-sm flex-shrink-0 ml-4"
              >
                <FileText size={15} />
                Review Draft
                <ArrowRight size={15} />
              </button>
            </div>
          )}

        </div>
      )}
    </div>
  )
}

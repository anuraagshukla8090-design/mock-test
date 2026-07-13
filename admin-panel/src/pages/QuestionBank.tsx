import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { getQuestions } from '../api/questions'
import type { QuestionFilters } from '../types/question'
import { DifficultyBadge, Badge } from '../components/ui/Badge'
import { PageSpinner } from '../components/ui/Spinner'
import ErrorAlert from '../components/ui/ErrorAlert'
import { Image, FlaskConical, AlertTriangle, GraduationCap } from 'lucide-react'
import { EXAMS, SUBJECTS } from '../constants/exams'

const PAGE_SIZE = 50

export default function QuestionBank() {
  const [params, setParams] = useSearchParams()

  const filters: QuestionFilters = {
    exam_name: params.get('exam_name') || undefined,
    subject: params.get('subject') || undefined,
    chapter: params.get('chapter') || undefined,
    difficulty: params.get('difficulty') || undefined,
    question_type: params.get('question_type') || undefined,
    search: params.get('search') || undefined,
    skip: Number(params.get('skip') ?? 0),
    limit: PAGE_SIZE,
  }

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['questions', filters],
    queryFn: () => getQuestions(filters),
  })

  const set = (key: string, value: string) => {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    next.delete('skip')
    setParams(next)
  }

  const page = Number(params.get('skip') ?? 0) / PAGE_SIZE
  const goPage = (dir: 1 | -1) => {
    const next = new URLSearchParams(params)
    const newSkip = Math.max(0, (Number(params.get('skip') ?? 0)) + dir * PAGE_SIZE)
    next.set('skip', String(newSkip))
    setParams(next)
  }

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Question Bank</h1>
          <p className="text-sm text-gray-500 mt-0.5">{data?.length ?? '…'} questions shown</p>
        </div>
        <Link
          to={`/test?${params.toString()}`}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 transition shadow-sm"
        >
          <GraduationCap size={15} />
          Open in Test View
        </Link>
      </div>

      {/* Filter bar */}
      <div className="bg-white border border-gray-200 rounded-lg p-4 mb-4 flex flex-wrap gap-3">
        <input
          type="text"
          placeholder="Search…"
          value={params.get('search') ?? ''}
          onChange={(e) => set('search', e.target.value)}
          className="border border-gray-200 rounded px-3 py-1.5 text-sm w-40 focus:outline-none focus:ring-2 focus:ring-indigo-400"
        />
        {/* Exam filter */}
        <select
          value={params.get('exam_name') ?? ''}
          onChange={(e) => set('exam_name', e.target.value)}
          className="border border-gray-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
        >
          <option value="">All Exams</option>
          {EXAMS.map((e) => (
            <option key={e.value} value={e.value}>{e.label}</option>
          ))}
        </select>

        {[
          {
            key: 'subject', label: 'Subject',
            options: SUBJECTS.map((s) => ({ value: s.value, label: s.label })),
          },
          {
            key: 'difficulty', label: 'Difficulty',
            options: ['easy', 'medium', 'hard'].map((v) => ({ value: v, label: v.charAt(0).toUpperCase() + v.slice(1) })),
          },
          {
            key: 'question_type', label: 'Type',
            options: ['conceptual', 'numerical', 'assertion_reason', 'match_the_following', 'statement_based']
              .map((v) => ({ value: v, label: v.replace(/_/g, ' ') })),
          },
        ].map(({ key, label, options }) => (
          <select
            key={key}
            value={params.get(key) ?? ''}
            onChange={(e) => set(key, e.target.value)}
            className="border border-gray-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
          >
            <option value="">All {label}s</option>
            {options.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        ))}
        <input
          type="text"
          placeholder="Chapter…"
          value={params.get('chapter') ?? ''}
          onChange={(e) => set('chapter', e.target.value)}
          className="border border-gray-200 rounded px-3 py-1.5 text-sm w-40 focus:outline-none focus:ring-2 focus:ring-indigo-400"
        />
        {[...params.entries()].filter(([k]) => ['subject','difficulty','question_type','chapter','search'].includes(k)).length > 0 && (
          <button
            onClick={() => setParams({})}
            className="text-xs text-gray-400 hover:text-red-500 underline"
          >
            Clear filters
          </button>
        )}
      </div>

      {/* Table */}
      {isLoading && <PageSpinner />}
      {isError && <ErrorAlert message="Failed to load questions" detail={String(error)} />}
      {data && (
        <div className="bg-white border border-gray-200 rounded-lg overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-gray-500 border-b border-gray-100 bg-gray-50">
                <th className="px-4 py-3 font-medium">Q#</th>
                <th className="px-4 py-3 font-medium">Subject</th>
                <th className="px-4 py-3 font-medium">Chapter</th>
                <th className="px-4 py-3 font-medium">Topic</th>
                <th className="px-4 py-3 font-medium">Difficulty</th>
                <th className="px-4 py-3 font-medium">Type</th>
                <th className="px-4 py-3 font-medium">Flags</th>
                <th className="px-4 py-3 font-medium"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {data.map((q) => (
                <tr key={q.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-2.5 font-mono text-xs text-gray-600">{q.question_number ?? '—'}</td>
                  <td className="px-4 py-2.5 capitalize text-gray-700">{q.subject ?? <span className="text-red-400">⚠ missing</span>}</td>
                  <td className="px-4 py-2.5 text-gray-700 max-w-[160px]">
                    <span className="truncate block" title={q.chapter ?? ''}>{q.chapter ?? <span className="text-red-400">⚠ missing</span>}</span>
                  </td>
                  <td className="px-4 py-2.5 text-gray-500 max-w-[140px]">
                    <span className="truncate block text-xs">{q.topic ?? '—'}</span>
                  </td>
                  <td className="px-4 py-2.5"><DifficultyBadge difficulty={q.difficulty} /></td>
                  <td className="px-4 py-2.5 text-gray-500 text-xs">{q.question_type ?? '—'}</td>
                  <td className="px-4 py-2.5">
                    <div className="flex gap-1">
                      {q.has_diagram && <span title="Has diagram"><Image size={13} className="text-purple-500" /></span>}
                      {q.has_formula && <span title="Has formula"><FlaskConical size={13} className="text-blue-500" /></span>}
                      {(!q.chapter || !q.difficulty) && <span title="Missing metadata"><AlertTriangle size={13} className="text-yellow-500" /></span>}
                    </div>
                  </td>
                  <td className="px-4 py-2.5">
                    <Link to={`/questions/${q.id}`} className="text-indigo-600 text-xs hover:underline">View →</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {data.length === 0 && (
            <p className="text-center text-gray-400 text-sm py-12">No questions match these filters</p>
          )}

          {/* Pagination */}
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100">
            <p className="text-xs text-gray-400">Page {page + 1} · {data.length} results</p>
            <div className="flex gap-2">
              <button
                onClick={() => goPage(-1)}
                disabled={page === 0}
                className="px-3 py-1 text-xs border border-gray-200 rounded hover:bg-gray-100 disabled:opacity-40"
              >← Prev</button>
              <button
                onClick={() => goPage(1)}
                disabled={data.length < PAGE_SIZE}
                className="px-3 py-1 text-xs border border-gray-200 rounded hover:bg-gray-100 disabled:opacity-40"
              >Next →</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

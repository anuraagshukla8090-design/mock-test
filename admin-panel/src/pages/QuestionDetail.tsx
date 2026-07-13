import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useParams, Link } from 'react-router-dom'
import { getQuestion } from '../api/questions'
import { DifficultyBadge, Badge } from '../components/ui/Badge'
import { PageSpinner } from '../components/ui/Spinner'
import ErrorAlert from '../components/ui/ErrorAlert'
import Collapsible from '../components/ui/Collapsible'
import RenderedContent from '../components/question/RenderedContent'
import OptionsList from '../components/question/OptionsList'
import MetadataEditForm from '../components/question/MetadataEditForm'
import {
  Copy, Code, ExternalLink, FileText,
  Image, FlaskConical, CheckCircle, AlertTriangle, Edit2,
} from 'lucide-react'

function DevActionsBar({ question }: { question: ReturnType<typeof useQuery<any>>['data'] }) {
  const [copied, setCopied] = useState<string | null>(null)

  const copy = (label: string, text: string) => {
    navigator.clipboard.writeText(text)
    setCopied(label)
    setTimeout(() => setCopied(null), 1500)
  }

  const btn = (label: string, icon: React.ReactNode, onClick: () => void) => (
    <button
      key={label}
      onClick={onClick}
      className="flex items-center gap-1.5 px-3 py-1.5 text-xs border border-gray-200 rounded hover:bg-gray-100 text-gray-600 transition-colors"
    >
      {icon}
      {copied === label ? '✓ Copied!' : label}
    </button>
  )

  return (
    <div className="flex flex-wrap gap-2 mb-6 bg-gray-50 border border-gray-200 rounded-lg px-4 py-3">
      <span className="text-xs font-medium text-gray-400 self-center mr-2">Dev actions:</span>
      {btn('Copy Markdown', <Copy size={12} />, () => copy('Copy Markdown', question.stem_md))}
      {btn('Copy Raw JSON', <Code size={12} />, () => copy('Copy Raw JSON', JSON.stringify(question, null, 2)))}
      <Link
        to={`/ingestions/${question.ingestion_id}`}
        className="flex items-center gap-1.5 px-3 py-1.5 text-xs border border-gray-200 rounded hover:bg-gray-100 text-gray-600"
      >
        <ExternalLink size={12} />
        Open Ingestion
      </Link>
      <Link
        to={`/ingestions/${question.ingestion_id}`}
        className="flex items-center gap-1.5 px-3 py-1.5 text-xs border border-gray-200 rounded hover:bg-gray-100 text-gray-600"
      >
        <FileText size={12} />
        Processing Report
      </Link>
    </div>
  )
}

function MetadataGrid({ question }: { question: any }) {
  const fields: Array<[string, any]> = [
    ['Exam', question.exam_name],
    ['Subject', question.subject],
    ['Chapter', question.chapter],
    ['Topic', question.topic],
    ['Subtopic', question.subtopic],
    ['Difficulty', question.difficulty],
    ['Type', question.question_type],
    ['Has Formula', question.has_formula ? '✓ Yes' : 'No'],
    ['Has Diagram', question.has_diagram ? '✓ Yes' : 'No'],
  ]
  const missing = fields.filter(([, v]) => !v || v === null)

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-3 gap-2">
        {fields.map(([label, val]) => (
          <div key={label} className={`rounded p-2.5 ${!val ? 'bg-red-50 border border-red-200' : 'bg-gray-50'}`}>
            <p className="text-xs text-gray-400">{label}</p>
            {val
              ? <p className="text-sm font-medium text-gray-900 capitalize">{String(val)}</p>
              : <p className="text-xs text-red-500 font-medium">⚠ Missing</p>
            }
          </div>
        ))}
      </div>
      {question.concepts?.length > 0 && (
        <div>
          <p className="text-xs text-gray-400 mb-1">Concepts</p>
          <div className="flex flex-wrap gap-1">
            {question.concepts.map((c: string) => <Badge key={c}>{c}</Badge>)}
          </div>
        </div>
      )}
      {missing.length > 0 && (
        <div className="flex items-center gap-2 text-xs text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
          <AlertTriangle size={13} />
          {missing.length} field{missing.length > 1 ? 's' : ''} missing: {missing.map(([l]) => l).join(', ')}
        </div>
      )}
    </div>
  )
}

export default function QuestionDetail() {
  const { id } = useParams<{ id: string }>()
  const [editingMeta, setEditingMeta] = useState(false)

  const { data: q, isLoading, isError, error } = useQuery({
    queryKey: ['question', id],
    queryFn: () => getQuestion(id!),
    enabled: !!id,
  })

  if (isLoading) return <PageSpinner />
  if (isError || !q) return <div className="p-8"><ErrorAlert message="Not found" detail={String(error)} /></div>

  return (
    <div className="p-8 max-w-5xl">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <Link to="/questions" className="text-xs text-gray-400 hover:text-gray-600">← Question Bank</Link>
          <h1 className="text-xl font-bold text-gray-900 mt-1">
            Question #{q.question_number ?? '?'}
          </h1>
          <p className="text-sm text-gray-500 font-mono">{q.id}</p>
        </div>
        <div className="flex gap-2 flex-wrap justify-end">
          {q.has_diagram && <Badge variant="purple"><Image size={11} className="inline mr-1" />Diagram</Badge>}
          {q.has_formula && <Badge variant="blue"><FlaskConical size={11} className="inline mr-1" />Formula</Badge>}
          <Badge variant={q.answer ? 'green' : 'red'}>{q.answer ? `Ans: ${q.answer}` : 'No answer'}</Badge>
          <Badge variant="gray">{q.section_type}</Badge>
        </div>
      </div>

      {/* Developer actions */}
      <DevActionsBar question={q} />

      {/* Ingestion info */}
      <div className="mb-6 text-xs text-gray-400 bg-gray-50 rounded px-4 py-2 flex flex-wrap gap-4">
        <span><span className="font-medium text-gray-600">Source:</span> {q.source_pdf}</span>
        {q.source_page && <span><span className="font-medium text-gray-600">Page:</span> {q.source_page}</span>}
        <span><span className="font-medium text-gray-600">Exam:</span> {q.exam_name ?? '—'}</span>
        <span><span className="font-medium text-gray-600">Subject:</span> <span className="capitalize">{q.subject ?? '—'}</span></span>
        <span><span className="font-medium text-gray-600">Layout:</span> {q.section_label ?? '—'}</span>
      </div>

      {/* Metadata */}
      <div className="mb-6 bg-white border border-gray-200 rounded-lg p-5">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-gray-700">Metadata</h2>
          <button
            onClick={() => setEditingMeta((e) => !e)}
            className="flex items-center gap-1.5 text-xs text-indigo-600 hover:text-indigo-800"
          >
            <Edit2 size={12} />
            {editingMeta ? 'Cancel' : 'Edit Metadata'}
          </button>
        </div>
        {editingMeta ? (
          <MetadataEditForm question={q} onClose={() => setEditingMeta(false)} />
        ) : (
          <MetadataGrid question={q} />
        )}
      </div>

      {/* Source Comparison */}
      <div className="mb-6 bg-white border border-gray-200 rounded-lg overflow-hidden">
        <div className="px-5 py-3 bg-gray-50 border-b border-gray-200">
          <h2 className="text-sm font-semibold text-gray-700">Source Comparison</h2>
          <p className="text-xs text-gray-400 mt-0.5">
            Left: raw markdown from parser · Right: rendered output — compare to spot parsing errors
          </p>
        </div>
        <div className="grid grid-cols-2 divide-x divide-gray-200">
          {/* Left: raw source */}
          <div className="p-4">
            <p className="text-xs font-medium text-gray-500 mb-2 flex items-center gap-1">
              <Code size={12} /> Raw Source
              {q.source_page && <span className="ml-auto text-gray-400">PDF page {q.source_page}</span>}
            </p>
            <pre className="text-xs font-mono text-gray-700 bg-gray-50 rounded p-3 overflow-x-auto whitespace-pre-wrap break-all max-h-96 overflow-y-auto">
              {q.stem_md}
            </pre>
            {q.options && Object.keys(q.options).length > 0 && (
              <pre className="mt-2 text-xs font-mono text-gray-500 bg-gray-50 rounded p-3 overflow-x-auto whitespace-pre-wrap">
                {Object.entries(q.options).map(([k, v]) => `${k}: ${v}`).join('\n')}
              </pre>
            )}
          </div>
          {/* Right: rendered */}
          <div className="p-4">
            <p className="text-xs font-medium text-gray-500 mb-2 flex items-center gap-1">
              <CheckCircle size={12} /> Rendered Output
            </p>
            <div className="max-h-96 overflow-y-auto">
              <RenderedContent content={q.stem_md} />
              {q.images?.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {q.images.map((img: any) => (
                    <img
                      key={img.filename}
                      src={`/api/images/${img.filename}`}
                      alt={img.filename}
                      className="max-w-xs max-h-40 object-contain border border-gray-200 rounded"
                    />
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Options */}
      <div className="mb-6 bg-white border border-gray-200 rounded-lg p-5">
        <h2 className="text-sm font-semibold text-gray-700 mb-3">
          Options
          {q.answer && <span className="ml-2 text-xs font-normal text-green-600">Correct: {q.answer}</span>}
        </h2>
        {q.section_type !== 'mcq'
          ? <p className="text-sm text-gray-500">Integer/numerical — answer: <span className="font-mono font-bold">{q.answer ?? '—'}</span></p>
          : <OptionsList options={q.options} answer={q.answer} />
        }
      </div>

      {/* Raw LLM response */}
      {q.llm_raw_response && (
        <Collapsible title="Raw LLM JSON Response" className="mb-6">
          <pre className="p-4 text-xs font-mono text-gray-600 bg-gray-50 overflow-x-auto max-h-80 overflow-y-auto">
            {JSON.stringify(q.llm_raw_response, null, 2)}
          </pre>
        </Collapsible>
      )}

      {/* Raw text for search debugging */}
      {q.raw_text && (
        <Collapsible title="Search Index Text (raw_text)" className="mb-6">
          <pre className="p-4 text-xs font-mono text-gray-500 bg-gray-50 whitespace-pre-wrap break-all max-h-48 overflow-y-auto">
            {q.raw_text}
          </pre>
        </Collapsible>
      )}
    </div>
  )
}

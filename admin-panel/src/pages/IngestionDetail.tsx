import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useParams, Link } from 'react-router-dom'
import { getIngestionStatus, retryIngestion } from '../api/ingestion'
import { getQuestions } from '../api/questions'
import { StatusBadge, DifficultyBadge } from '../components/ui/Badge'
import { PageSpinner } from '../components/ui/Spinner'
import ErrorAlert from '../components/ui/ErrorAlert'
import Collapsible from '../components/ui/Collapsible'

export default function IngestionDetail() {
  const { id } = useParams<{ id: string }>()
  const qc = useQueryClient()

  const { data: ing, isLoading, isError, error } = useQuery({
    queryKey: ['ingestion', id],
    queryFn: () => getIngestionStatus(id!),
    refetchInterval: (q) =>
      ['SAVED', 'FAILED'].includes(q.state.data?.status ?? '') ? false : 4000,
    enabled: !!id,
  })

  const { data: questions } = useQuery({
    queryKey: ['questions', { ingestion_id: id }],
    queryFn: () => getQuestions({ limit: 200 }),
    enabled: ing?.status === 'SAVED',
  })

  const retry = useMutation({
    mutationFn: () => retryIngestion(id!),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ingestion', id] }),
  })

  if (isLoading) return <PageSpinner />
  if (isError || !ing) return <div className="p-8"><ErrorAlert message="Not found" detail={String(error)} /></div>

  const report = ing.processing_report

  return (
    <div className="p-8 max-w-4xl">
      <div className="flex items-start justify-between mb-6">
        <div>
          <Link to="/ingestions" className="text-xs text-gray-400 hover:text-gray-600">← Ingestions</Link>
          <h1 className="text-2xl font-bold text-gray-900 mt-1">{ing.filename}</h1>
          <p className="text-sm text-gray-500 font-mono">{ing.id}</p>
        </div>
        {ing.status === 'FAILED' && (
          <button
            onClick={() => retry.mutate()}
            disabled={retry.isPending}
            className="px-4 py-2 bg-red-600 text-white text-sm rounded hover:bg-red-700"
          >
            {retry.isPending ? 'Retrying…' : 'Retry'}
          </button>
        )}
      </div>

      {/* Info grid */}
      <div className="grid grid-cols-4 gap-3 mb-6">
        {[
          ['Status', <StatusBadge status={ing.status} />],
          ['Exam', ing.exam_name ?? '—'],
          ['Subject', <span className="capitalize">{ing.subject ?? '—'}</span>],
          ['Layout', ing.layout_type ?? '—'],
          ['Questions found', ing.questions_found ?? '—'],
          ['Questions saved', ing.questions_saved],
          ['Time', ing.processing_time_s ? `${ing.processing_time_s.toFixed(1)}s` : '—'],
          ['Created', new Date(ing.created_at).toLocaleString()],
        ].map(([label, val]) => (
          <div key={label as string} className="bg-white border border-gray-200 rounded p-3">
            <p className="text-xs text-gray-400">{label}</p>
            <p className="text-sm font-medium text-gray-900 mt-0.5">{val as any}</p>
          </div>
        ))}
      </div>

      {/* Error message */}
      {ing.error_message && (
        <div className="mb-6 bg-red-50 border border-red-200 rounded p-4">
          <p className="text-xs font-semibold text-red-700 mb-1">Error at stage: {ing.failed_at_stage}</p>
          <pre className="text-xs text-red-600 whitespace-pre-wrap break-all">{ing.error_message}</pre>
        </div>
      )}

      {/* Processing report */}
      {report && (
        <div className="mb-6 bg-white border border-gray-200 rounded-lg p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Processing Report</h2>
          <div className="grid grid-cols-3 gap-3 text-sm mb-4">
            {[
              ['Detected', report.questions_detected],
              ['Stored', report.questions_stored],
              ['Skipped', report.questions_skipped],
              ['Answers mapped', report.answers_mapped],
              ['Images linked', report.images_linked],
              ['Time', `${report.processing_time_s}s`],
            ].map(([label, val]) => (
              <div key={label as string} className="bg-gray-50 rounded px-3 py-2">
                <p className="text-xs text-gray-500">{label}</p>
                <p className="font-semibold text-gray-900">{val}</p>
              </div>
            ))}
          </div>

          {report.warnings.length > 0 && (
            <Collapsible title={`⚠ ${report.warnings.length} warnings`}>
              <div className="p-3 space-y-1">
                {report.warnings.map((w, i) => (
                  <p key={i} className="text-xs text-yellow-700 font-mono">{w}</p>
                ))}
              </div>
            </Collapsible>
          )}
        </div>
      )}

      {/* Questions from this ingestion */}
      {questions && questions.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg overflow-x-auto">
          <div className="px-5 py-3 border-b border-gray-100">
            <h2 className="text-sm font-semibold text-gray-700">Extracted Questions ({questions.length})</h2>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-gray-500 border-b border-gray-100 bg-gray-50">
                <th className="px-4 py-2 font-medium">Q#</th>
                <th className="px-4 py-2 font-medium">Chapter</th>
                <th className="px-4 py-2 font-medium">Topic</th>
                <th className="px-4 py-2 font-medium">Difficulty</th>
                <th className="px-4 py-2 font-medium">Type</th>
                <th className="px-4 py-2 font-medium"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {questions.map((q) => (
                <tr key={q.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2 font-mono text-xs">{q.question_number ?? '—'}</td>
                  <td className="px-4 py-2 text-gray-700">{q.chapter ?? <span className="text-red-400">Missing</span>}</td>
                  <td className="px-4 py-2 text-gray-600">{q.topic ?? '—'}</td>
                  <td className="px-4 py-2"><DifficultyBadge difficulty={q.difficulty} /></td>
                  <td className="px-4 py-2 text-gray-500 text-xs">{q.question_type ?? '—'}</td>
                  <td className="px-4 py-2">
                    <Link to={`/questions/${q.id}`} className="text-indigo-600 text-xs hover:underline">View</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

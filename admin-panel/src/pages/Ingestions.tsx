import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { getIngestions, deleteIngestion } from '../api/ingestion'
import { StatusBadge } from '../components/ui/Badge'
import { PageSpinner } from '../components/ui/Spinner'
import ErrorAlert from '../components/ui/ErrorAlert'
import { Trash2 } from 'lucide-react'

export default function Ingestions() {
  const queryClient = useQueryClient()

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['ingestions'],
    queryFn: () => getIngestions(0, 100),
    refetchInterval: 10000,
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteIngestion(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ingestions'] })
    },
  })

  const handleDelete = (id: string, filename: string) => {
    if (!window.confirm(`Delete "${filename}"?\n\nThis will permanently remove the ingestion record and ALL associated questions. This cannot be undone.`)) return
    deleteMutation.mutate(id)
  }

  if (isLoading) return <PageSpinner />
  if (isError) return <div className="p-8"><ErrorAlert message="Failed to load ingestions" detail={String(error)} /></div>

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Ingestions</h1>
          <p className="text-sm text-gray-500 mt-0.5">{data?.length ?? 0} total uploads</p>
        </div>
        <Link
          to="/upload"
          className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded hover:bg-indigo-700"
        >
          + Upload PDF
        </Link>
      </div>

      {deleteMutation.isError && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
          Delete failed. Please try again.
        </div>
      )}

      <div className="bg-white border border-gray-200 rounded-lg overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-gray-500 border-b border-gray-100 bg-gray-50">
              {['ID', 'File', 'Exam · Subject', 'Layout', 'Status', 'Found', 'Saved', 'Time', ''].map((h) => (
                <th key={h} className="px-4 py-3 font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {data?.map((ing) => (
              <tr key={ing.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-4 py-3 font-mono text-xs text-gray-400">{ing.id.slice(0, 8)}…</td>
                <td className="px-4 py-3 text-gray-700 max-w-[180px]">
                  <span className="truncate block" title={ing.filename}>{ing.filename}</span>
                </td>
                <td className="px-4 py-3 text-gray-600">
                  <span className="font-medium">{ing.exam_name ?? '—'}</span>
                  <span className="text-gray-400"> · </span>
                  <span className="capitalize">{ing.subject ?? '—'}</span>
                </td>
                <td className="px-4 py-3 text-gray-500 text-xs">{ing.layout_type ?? '—'}</td>
                <td className="px-4 py-3"><StatusBadge status={ing.status} /></td>
                <td className="px-4 py-3 text-gray-700">—</td>
                <td className="px-4 py-3 text-gray-700">{ing.questions_saved}</td>
                <td className="px-4 py-3 text-gray-500 text-xs">
                  {new Date(ing.created_at).toLocaleDateString()}
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-3">
                    <Link to={`/ingestions/${ing.id}`} className="text-indigo-600 text-xs hover:underline">
                      View →
                    </Link>
                    <button
                      onClick={() => handleDelete(ing.id, ing.filename)}
                      disabled={deleteMutation.isPending}
                      className="text-red-400 hover:text-red-600 transition-colors disabled:opacity-40"
                      title="Delete this ingestion and all its questions"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {data?.length === 0 && (
          <p className="text-center text-gray-400 text-sm py-12">
            No ingestions yet. <Link to="/upload" className="text-indigo-600 hover:underline">Upload a PDF</Link>
          </p>
        )}
      </div>
    </div>
  )
}

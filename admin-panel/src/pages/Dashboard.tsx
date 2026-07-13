import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { getStats } from '../api/questions'
import { getIngestions } from '../api/ingestion'
import StatCard from '../components/ui/StatCard'
import { StatusBadge } from '../components/ui/Badge'
import { PageSpinner } from '../components/ui/Spinner'
import ErrorAlert from '../components/ui/ErrorAlert'

export default function Dashboard() {
  const stats = useQuery({ queryKey: ['stats'], queryFn: getStats, refetchInterval: 30000 })
  const ingestions = useQuery({ queryKey: ['ingestions'], queryFn: () => getIngestions(0, 10) })

  if (stats.isLoading) return <PageSpinner />
  if (stats.isError) return (
    <div className="p-8"><ErrorAlert message="Failed to load stats" detail={String(stats.error)} /></div>
  )

  const s = stats.data!
  const saved = ingestions.data?.filter(i => i.status === 'SAVED').length ?? 0
  const failed = ingestions.data?.filter(i => i.status === 'FAILED').length ?? 0

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Dashboard</h1>
      <p className="text-sm text-gray-500 mb-6">Backend validation tool — not a production UI</p>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <StatCard label="Total Questions" value={s.total} color="indigo" />
        <StatCard label="Ingestions (ok)" value={saved} color="green" />
        <StatCard label="Ingestions (failed)" value={failed} color="red" />
        <StatCard
          label="Subjects"
          value={Object.keys(s.by_subject).length}
          sub={Object.entries(s.by_subject).map(([k, v]) => `${k}: ${v}`).join(' · ')}
          color="gray"
        />
      </div>

      {/* Breakdown grids */}
      <div className="grid grid-cols-2 gap-6 mb-8">
        <div className="bg-white border border-gray-200 rounded-lg p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">By Subject</h2>
          {Object.entries(s.by_subject).length === 0
            ? <p className="text-sm text-gray-400">No data</p>
            : Object.entries(s.by_subject).sort(([,a],[,b]) => b - a).map(([sub, cnt]) => (
              <div key={sub} className="flex justify-between items-center py-1 border-b border-gray-50 last:border-0">
                <span className="text-sm capitalize text-gray-700">{sub}</span>
                <span className="text-sm font-semibold text-indigo-600">{cnt}</span>
              </div>
            ))
          }
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">By Difficulty</h2>
          {Object.entries(s.by_difficulty).length === 0
            ? <p className="text-sm text-gray-400">No data</p>
            : Object.entries(s.by_difficulty).map(([diff, cnt]) => (
              <div key={diff} className="flex justify-between items-center py-1 border-b border-gray-50 last:border-0">
                <span className="text-sm capitalize text-gray-700">{diff}</span>
                <span className="text-sm font-semibold text-indigo-600">{cnt}</span>
              </div>
            ))
          }
        </div>
      </div>

      {/* Recent ingestions */}
      <div className="bg-white border border-gray-200 rounded-lg">
        <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-700">Recent Ingestions</h2>
          <Link to="/ingestions" className="text-xs text-indigo-600 hover:underline">View all →</Link>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-gray-500 border-b border-gray-100">
                <th className="px-5 py-3 font-medium">File</th>
                <th className="px-5 py-3 font-medium">Exam · Subject</th>
                <th className="px-5 py-3 font-medium">Layout</th>
                <th className="px-5 py-3 font-medium">Status</th>
                <th className="px-5 py-3 font-medium">Questions</th>
                <th className="px-5 py-3 font-medium"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {ingestions.data?.slice(0, 8).map((ing) => (
                <tr key={ing.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-5 py-3 font-mono text-xs text-gray-700 max-w-[200px] truncate">{ing.filename}</td>
                  <td className="px-5 py-3 text-gray-600">
                    {ing.exam_name ?? '—'} · <span className="capitalize">{ing.subject ?? '—'}</span>
                  </td>
                  <td className="px-5 py-3 text-gray-500 text-xs">{ing.layout_type ?? '—'}</td>
                  <td className="px-5 py-3"><StatusBadge status={ing.status} /></td>
                  <td className="px-5 py-3 text-gray-700">{ing.questions_saved}</td>
                  <td className="px-5 py-3">
                    <Link to={`/ingestions/${ing.id}`} className="text-indigo-600 text-xs hover:underline">View</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!ingestions.data?.length && (
            <p className="text-center text-gray-400 text-sm py-8">No ingestions yet</p>
          )}
        </div>
      </div>
    </div>
  )
}

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getStats } from '../api/questions'
import { getIngestions, getLayouts } from '../api/ingestion'
import axios from 'axios'
import { PageSpinner } from '../components/ui/Spinner'
import { Badge } from '../components/ui/Badge'
import { CheckCircle, XCircle, AlertCircle } from 'lucide-react'

function HealthCard() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['health'],
    queryFn: () => axios.get('/health').then((r) => r.data),
    refetchInterval: 15000,
  })

  if (isLoading) return <div className="bg-white border border-gray-200 rounded-lg p-5"><PageSpinner /></div>

  const ok = !isError && data?.status === 'ok'
  const degraded = data?.status === 'degraded'

  return (
    <div className={`bg-white border rounded-lg p-5 ${ok ? 'border-green-200' : degraded ? 'border-yellow-200' : 'border-red-200'}`}>
      <div className="flex items-center gap-2 mb-4">
        {ok && <CheckCircle size={18} className="text-green-600" />}
        {degraded && <AlertCircle size={18} className="text-yellow-600" />}
        {isError && <XCircle size={18} className="text-red-600" />}
        <h2 className="text-sm font-semibold text-gray-700">Backend Health</h2>
        <span className={`ml-auto text-xs font-medium px-2 py-0.5 rounded ${ok ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
          {isError ? 'UNREACHABLE' : data?.status?.toUpperCase()}
        </span>
      </div>

      {isError ? (
        <p className="text-sm text-red-600">Cannot reach FastAPI at localhost:8000</p>
      ) : (
        <div className="space-y-2 text-sm">
          {[
            ['Version', data?.version],
            ['Database', data?.database],
            ['LLM Provider', data?.llm_provider],
            ['LLM Model', data?.llm_model],
          ].map(([label, val]) => (
            <div key={label as string} className="flex justify-between">
              <span className="text-gray-500">{label}</span>
              <span className={`font-mono text-xs ${String(val).includes('error') ? 'text-red-600' : 'text-gray-700'}`}>{String(val ?? '—')}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function BuildersCard() {
  const { data } = useQuery({
    queryKey: ['health'],
    queryFn: () => axios.get('/health').then((r) => r.data),
  })

  const { data: layouts } = useQuery({ queryKey: ['layouts'], queryFn: getLayouts })

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5">
      <h2 className="text-sm font-semibold text-gray-700 mb-4">Registered QuestionBuilders</h2>
      {data?.builders
        ? Object.entries(data.builders).map(([key, info]: any) => (
          <div key={key} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
            <div>
              <p className="text-sm font-mono text-gray-700">{key}</p>
              <p className="text-xs text-gray-400">{info.class}</p>
            </div>
            <Badge variant={info.implemented ? 'green' : 'gray'}>
              {info.implemented ? 'Implemented' : 'Placeholder'}
            </Badge>
          </div>
        ))
        : <p className="text-sm text-gray-400">Loading…</p>
      }
      {layouts && (
        <div className="mt-4 pt-3 border-t border-gray-100">
          <p className="text-xs text-gray-400 mb-2">Upload form labels:</p>
          {Object.entries(layouts).map(([k, v]) => (
            <div key={k} className="text-xs text-gray-500 py-0.5">
              <span className="font-mono text-gray-700">{k}</span> → {v as string}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function StatsCard() {
  const { data, isLoading } = useQuery({ queryKey: ['stats'], queryFn: getStats })
  if (isLoading) return null
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5">
      <h2 className="text-sm font-semibold text-gray-700 mb-3">Question Bank Stats</h2>
      <p className="text-3xl font-bold text-indigo-600 mb-3">{data?.total ?? 0}</p>
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <p className="text-xs text-gray-400 mb-1">By Subject</p>
          {Object.entries(data?.by_subject ?? {}).map(([k, v]) => (
            <div key={k} className="flex justify-between text-xs py-0.5">
              <span className="capitalize text-gray-600">{k}</span><span className="font-medium">{v}</span>
            </div>
          ))}
        </div>
        <div>
          <p className="text-xs text-gray-400 mb-1">By Difficulty</p>
          {Object.entries(data?.by_difficulty ?? {}).map(([k, v]) => (
            <div key={k} className="flex justify-between text-xs py-0.5">
              <span className="capitalize text-gray-600">{k}</span><span className="font-medium">{v}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function ApiTester() {
  const [url, setUrl] = useState('/api/questions/stats')
  const [response, setResponse] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const run = async () => {
    setLoading(true); setErr(null); setResponse(null)
    try {
      const res = await axios.get(url)
      setResponse(res.data)
    } catch (e: any) {
      setErr(String(e?.response?.data?.detail ?? e?.message ?? e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5">
      <h2 className="text-sm font-semibold text-gray-700 mb-3">Raw API Tester</h2>
      <div className="flex gap-2 mb-3">
        <input
          type="text"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && run()}
          className="flex-1 border border-gray-200 rounded px-3 py-1.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-indigo-400"
        />
        <button
          onClick={run}
          disabled={loading}
          className="px-4 py-1.5 bg-indigo-600 text-white text-sm rounded hover:bg-indigo-700 disabled:opacity-40"
        >
          {loading ? '…' : 'GET'}
        </button>
      </div>
      {err && <p className="text-xs text-red-600 mb-2">{err}</p>}
      {response && (
        <pre className="text-xs font-mono text-gray-600 bg-gray-50 rounded p-3 overflow-x-auto max-h-80 overflow-y-auto">
          {JSON.stringify(response, null, 2)}
        </pre>
      )}
    </div>
  )
}

export default function ApiDebug() {
  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">API Debug</h1>
      <p className="text-sm text-gray-500 mb-6">Backend introspection — developer use only</p>

      <div className="grid grid-cols-2 gap-5 mb-5">
        <HealthCard />
        <StatsCard />
      </div>
      <div className="grid grid-cols-2 gap-5 mb-5">
        <BuildersCard />
        <ApiTester />
      </div>
    </div>
  )
}

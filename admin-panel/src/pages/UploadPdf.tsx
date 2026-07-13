import { useState, useRef } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { uploadPdf, getLayouts, getIngestionStatus } from '../api/ingestion'
import type { IngestionDetail } from '../types/ingestion'
import { StatusBadge } from '../components/ui/Badge'
import Spinner from '../components/ui/Spinner'
import ErrorAlert from '../components/ui/ErrorAlert'
import { Upload, FileText, CheckCircle, XCircle, AlertCircle } from 'lucide-react'
import { EXAMS, subjectsForExam } from '../constants/exams'

function ProcessingReport({ report }: { report: NonNullable<IngestionDetail['processing_report']> }) {
  return (
    <div className="mt-4 space-y-3">
      <div className="grid grid-cols-3 gap-3 text-sm">
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
        <div className="bg-yellow-50 border border-yellow-200 rounded p-3">
          <p className="text-xs font-medium text-yellow-800 mb-1">⚠ Warnings ({report.warnings.length})</p>
          <ul className="text-xs text-yellow-700 space-y-0.5">
            {report.warnings.slice(0, 10).map((w, i) => <li key={i}>{w}</li>)}
            {report.warnings.length > 10 && <li>… and {report.warnings.length - 10} more</li>}
          </ul>
        </div>
      )}
      {report.errors.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded p-3">
          <p className="text-xs font-medium text-red-800 mb-1">✗ Errors</p>
          <ul className="text-xs text-red-700 space-y-0.5">
            {report.errors.map((e, i) => <li key={i}>{e}</li>)}
          </ul>
        </div>
      )}
    </div>
  )
}

function IngestionStatusCard({ ingestionId }: { ingestionId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ['ingestion', ingestionId],
    queryFn: () => getIngestionStatus(ingestionId),
    refetchInterval: (q) => {
      const done = ['SAVED', 'FAILED']
      return done.includes(q.state.data?.status ?? '') ? false : 3000
    },
  })

  if (isLoading || !data) return <div className="flex gap-2 items-center text-sm text-gray-500 mt-4"><Spinner size="sm" /> Loading status…</div>

  const isDone = ['SAVED', 'FAILED'].includes(data.status)
  const isSuccess = data.status === 'SAVED'

  return (
    <div className={`mt-4 rounded-lg border p-4 ${isSuccess ? 'border-green-200 bg-green-50' : data.status === 'FAILED' ? 'border-red-200 bg-red-50' : 'border-blue-200 bg-blue-50'}`}>
      <div className="flex items-center gap-3 mb-2">
        {!isDone && <Spinner size="sm" />}
        {isSuccess && <CheckCircle size={18} className="text-green-600" />}
        {data.status === 'FAILED' && <XCircle size={18} className="text-red-600" />}
        <div>
          <p className="text-sm font-medium text-gray-900">
            Ingestion {data.id.slice(0, 8)}…
          </p>
          <StatusBadge status={data.status} />
        </div>
        {!isDone && (
          <p className="ml-auto text-xs text-gray-500 animate-pulse">Processing…</p>
        )}
      </div>

      {data.status === 'FAILED' && data.error_message && (
        <div className="mt-2 text-xs text-red-700 font-mono bg-red-100 rounded p-2 break-all">
          {data.error_message}
        </div>
      )}

      {data.processing_report && <ProcessingReport report={data.processing_report} />}

      {isSuccess && (
        <p className="mt-3 text-sm font-semibold text-green-700">
          ✓ {data.questions_saved} questions saved
        </p>
      )}
    </div>
  )
}

export default function UploadPdf() {
  const [file, setFile] = useState<File | null>(null)
  const [examName, setExamName] = useState('')
  const [subject, setSubject] = useState('')
  const [layoutType, setLayoutType] = useState('')
  const [uploadProgress, setUploadProgress] = useState(0)
  const [ingestionId, setIngestionId] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  const layouts = useQuery({ queryKey: ['layouts'], queryFn: getLayouts })

  const upload = useMutation({
    mutationFn: async () => {
      const fd = new FormData()
      fd.append('file', file!)
      fd.append('exam_name', examName)
      fd.append('subject', subject)
      fd.append('layout_type', layoutType)

      const { default: axios } = await import('axios')
      const res = await axios.post<IngestionDetail>('/api/ingestion/upload', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) => {
          if (e.total) setUploadProgress(Math.round((e.loaded / e.total) * 100))
        },
      })
      return res.data
    },
    onSuccess: (data) => setIngestionId(data.id),
  })

  const isFullPaper = layoutType === 'full_paper'
  const canSubmit = file && examName.trim() && layoutType && (isFullPaper || subject.trim())

  // When exam changes, reset subject if it's no longer valid for the new exam
  const handleExamChange = (newExam: string) => {
    setExamName(newExam)
    const validSubjects = subjectsForExam(newExam).map((s) => s.value)
    if (subject && !validSubjects.includes(subject as never)) {
      setSubject('')
    }
  }

  return (
    <div className="p-8 max-w-2xl">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">Upload PDF</h1>
      <p className="text-sm text-gray-500 mb-6">Start the ingestion pipeline for a new exam paper</p>

      <div className="bg-white border border-gray-200 rounded-lg p-6 space-y-4">
        {/* File drop */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">PDF File</label>
          <div
            onClick={() => fileRef.current?.click()}
            className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center cursor-pointer hover:border-indigo-400 transition-colors"
          >
            {file ? (
              <div className="flex items-center justify-center gap-2 text-gray-700">
                <FileText size={20} />
                <span className="text-sm font-medium">{file.name}</span>
                <span className="text-xs text-gray-400">({(file.size / 1024 / 1024).toFixed(1)} MB)</span>
              </div>
            ) : (
              <div className="text-gray-400">
                <Upload size={24} className="mx-auto mb-2" />
                <p className="text-sm">Click to select a PDF file</p>
              </div>
            )}
          </div>
          <input
            ref={fileRef}
            type="file"
            accept=".pdf"
            className="hidden"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </div>

        {/* Exam name */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Exam</label>
          <select
            value={examName}
            onChange={(e) => handleExamChange(e.target.value)}
            className="w-full border border-gray-200 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
          >
            <option value="">— select exam —</option>
            {EXAMS.map((e) => (
              <option key={e.value} value={e.value}>{e.label}</option>
            ))}
          </select>
        </div>

        {/* Subject */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Subject
            {isFullPaper && (
              <span className="ml-2 text-xs font-normal text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full">
                Auto-detected by AI
              </span>
            )}
          </label>
          <select
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            disabled={!examName || isFullPaper}
            className="w-full border border-gray-200 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <option value="">
              {isFullPaper
                ? '— AI identifies subject per question —'
                : examName
                ? '— select subject —'
                : '— select exam first —'}
            </option>
            {!isFullPaper && subjectsForExam(examName).map((s) => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>
          {isFullPaper && (
            <p className="mt-1 text-xs text-gray-400">
              For full papers, the AI identifies Physics / Chemistry / Mathematics per question automatically.
            </p>
          )}
        </div>

        {/* Layout type */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">PDF Layout Type</label>
          {layouts.isLoading ? (
            <div className="flex items-center gap-2 text-sm text-gray-400"><Spinner size="sm" /> Loading layouts…</div>
          ) : (
            <select
              value={layoutType}
              onChange={(e) => setLayoutType(e.target.value)}
              className="w-full border border-gray-200 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
            >
              <option value="">— select layout —</option>
              {layouts.data && Object.entries(layouts.data).map(([key, label]) => (
                <option key={key} value={key}>{label}</option>
              ))}
            </select>
          )}
        </div>

        {/* Error */}
        {upload.isError && (
          <ErrorAlert
            message="Upload failed"
            detail={String((upload.error as any)?.response?.data?.detail ?? upload.error)}
          />
        )}

        {/* Progress */}
        {upload.isPending && uploadProgress > 0 && uploadProgress < 100 && (
          <div>
            <div className="flex justify-between text-xs text-gray-500 mb-1">
              <span>Uploading…</span><span>{uploadProgress}%</span>
            </div>
            <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
              <div className="h-full bg-indigo-500 transition-all" style={{ width: `${uploadProgress}%` }} />
            </div>
          </div>
        )}

        <button
          onClick={() => upload.mutate()}
          disabled={!canSubmit || upload.isPending}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {upload.isPending ? <><Spinner size="sm" /> Processing…</> : <><Upload size={16} /> Upload & Process</>}
        </button>
      </div>

      {/* Status tracking */}
      {ingestionId && <IngestionStatusCard ingestionId={ingestionId} />}
    </div>
  )
}

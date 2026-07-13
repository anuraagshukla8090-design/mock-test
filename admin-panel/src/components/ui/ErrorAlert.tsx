import { AlertCircle } from 'lucide-react'

export default function ErrorAlert({ message, detail }: { message: string; detail?: string }) {
  return (
    <div className="rounded-md bg-red-50 border border-red-200 p-4">
      <div className="flex gap-3">
        <AlertCircle className="text-red-500 flex-shrink-0 mt-0.5" size={16} />
        <div>
          <p className="text-sm font-medium text-red-800">{message}</p>
          {detail && <p className="mt-1 text-xs text-red-600 font-mono break-all">{detail}</p>}
        </div>
      </div>
    </div>
  )
}

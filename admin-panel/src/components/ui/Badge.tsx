// Badge — small coloured pill label
export function Badge({ children, variant = 'default' }: {
  children: React.ReactNode
  variant?: 'default' | 'green' | 'red' | 'yellow' | 'blue' | 'gray' | 'purple'
}) {
  const cls = {
    default: 'bg-gray-100 text-gray-700',
    green: 'bg-green-100 text-green-800',
    red: 'bg-red-100 text-red-800',
    yellow: 'bg-yellow-100 text-yellow-800',
    blue: 'bg-blue-100 text-blue-800',
    gray: 'bg-gray-100 text-gray-500',
    purple: 'bg-purple-100 text-purple-800',
  }[variant]

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${cls}`}>
      {children}
    </span>
  )
}

// Status badge for ingestion pipeline stages
import type { IngestionStatus } from '../../types/ingestion'

export function StatusBadge({ status }: { status: IngestionStatus | string }) {
  const map: Record<string, 'green' | 'red' | 'yellow' | 'blue' | 'gray'> = {
    SAVED: 'green',
    FAILED: 'red',
    UPLOADED: 'yellow',
    MINERU_COMPLETE: 'blue',
    QUESTIONS_BUILT: 'blue',
    METADATA_COMPLETE: 'blue',
  }
  return <Badge variant={map[status] ?? 'gray'}>{status}</Badge>
}

// Difficulty badge
export function DifficultyBadge({ difficulty }: { difficulty: string | null }) {
  if (!difficulty) return <span className="text-gray-400 text-xs">—</span>
  const map: Record<string, 'green' | 'yellow' | 'red'> = {
    easy: 'green', medium: 'yellow', hard: 'red',
  }
  return <Badge variant={map[difficulty] ?? 'gray'}>{difficulty}</Badge>
}

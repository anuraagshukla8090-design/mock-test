import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'

export default function Collapsible({
  title, children, defaultOpen = false, className = '',
}: {
  title: string
  children: React.ReactNode
  defaultOpen?: boolean
  className?: string
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className={`border border-gray-200 rounded-md ${className}`}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-4 py-3 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
      >
        <span>{title}</span>
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
      </button>
      {open && <div className="border-t border-gray-200">{children}</div>}
    </div>
  )
}

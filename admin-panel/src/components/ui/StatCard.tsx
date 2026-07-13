export default function StatCard({
  label, value, sub, color = 'indigo',
}: {
  label: string
  value: number | string
  sub?: string
  color?: 'indigo' | 'green' | 'yellow' | 'red' | 'gray'
}) {
  const dot = {
    indigo: 'bg-indigo-500',
    green: 'bg-green-500',
    yellow: 'bg-yellow-500',
    red: 'bg-red-500',
    gray: 'bg-gray-400',
  }[color]

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5">
      <div className="flex items-center gap-2 mb-2">
        <span className={`inline-block h-2 w-2 rounded-full ${dot}`} />
        <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">{label}</p>
      </div>
      <p className="text-3xl font-bold text-gray-900">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  )
}

import RenderedContent from './RenderedContent'

const OPTION_KEYS = ['A', 'B', 'C', 'D']

interface Props {
  options: Record<string, string>
  answer: string | null
}

export default function OptionsList({ options, answer }: Props) {
  if (!options || Object.keys(options).length === 0) {
    return <p className="text-sm text-gray-400 italic">No options (integer/numerical type)</p>
  }

  return (
    <div className="space-y-2">
      {Object.entries(options).map(([key, value]) => {
        const isCorrect = answer && key.toUpperCase() === answer.toUpperCase()
        return (
          <div
            key={key}
            className={`flex gap-3 rounded-md border px-4 py-2.5 ${
              isCorrect
                ? 'border-green-400 bg-green-50'
                : 'border-gray-200 bg-white'
            }`}
          >
            <span
              className={`flex-shrink-0 font-semibold text-sm w-5 ${
                isCorrect ? 'text-green-700' : 'text-gray-500'
              }`}
            >
              {key.toUpperCase()}
            </span>
            <div className="text-sm text-gray-800 flex-1">
              <RenderedContent content={value} />
            </div>
            {isCorrect && (
              <span className="flex-shrink-0 text-green-600 text-xs font-semibold self-center">
                ✓ Correct
              </span>
            )}
          </div>
        )
      })}
      {answer && Object.keys(options).length > 0 && (
        <p className="text-xs text-gray-500 mt-1">
          Correct answer: <span className="font-semibold text-green-700">{answer}</span>
        </p>
      )}
      {!answer && (
        <p className="text-xs text-red-500 mt-1">⚠ Answer not set</p>
      )}
    </div>
  )
}

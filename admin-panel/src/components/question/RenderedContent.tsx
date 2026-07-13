import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'

interface Props {
  content: string
}

export default function RenderedContent({ content }: Props) {
  return (
    <div className="prose prose-sm max-w-none prose-p:my-1 prose-ul:my-1">
      <ReactMarkdown
        remarkPlugins={[remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={{
          img: ({ src, alt }) => (
            <img
              src={src?.startsWith('/api/images') ? src : `/api/images/${src}`}
              alt={alt ?? ''}
              className="max-w-full rounded border border-gray-200 my-2"
            />
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}

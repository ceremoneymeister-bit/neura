import { Square } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { Components } from 'react-markdown'
import { CodeBlock } from './CodeBlock'
import { NeuraIcon, NeuraThinking } from '@/components/ui/NeuraIcon'

interface StreamingMessageProps {
  text: string
  statusText: string | null
  toolText: string | null
  onStop: () => void
}

function getStatusLabel(statusText: string | null, toolText: string | null): string {
  if (toolText) return toolText
  if (statusText) return statusText.replace(/^[\u2699\uFE0F\u23F3\uD83C-\uDBFF\uDC00-\uDFFF\s]+/, '')
  return 'Думаю...'
}

const streamingComponents: Components = {
  code({ className, children }) {
    const match = /language-(\w+)/.exec(className ?? '')
    const lang = match?.[1] ?? ''
    if (match) {
      return <CodeBlock language={lang} code={String(children).replace(/\n$/, '')} />
    }
    return (
      <code className="font-mono text-xs bg-[var(--bg-input)] px-1.5 py-0.5 rounded text-[var(--code-inline)] border border-[var(--border)]">
        {children}
      </code>
    )
  },
  a({ href, children }) {
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="text-[var(--accent)] underline hover:text-[var(--accent-light)] transition-colors"
      >
        {children}
      </a>
    )
  },
  img({ src, alt }) {
    return (
      <a href={src} target="_blank" rel="noopener noreferrer" className="block my-3">
        <img
          src={src}
          alt={alt ?? ''}
          loading="lazy"
          className="max-w-full max-h-[400px] rounded-lg border border-[var(--border)] object-contain"
        />
      </a>
    )
  },
}

export function StreamingMessage({ text, statusText, toolText, onStop }: StreamingMessageProps) {
  const isThinking = !text

  return (
    <div className="flex gap-3 px-4 py-3 animate-fade-in will-change-transform">
      <div className="shrink-0 mt-0.5 select-none">
        {isThinking ? <NeuraThinking size={28} /> : <NeuraIcon size={28} />}
      </div>

      <div className="flex flex-col gap-2 max-w-[88%] min-w-0 items-start">
        <div className="px-4 py-3 rounded-xl bg-[var(--bg-card)] border border-[var(--border)] border-l-2 border-l-[var(--accent)]/30 text-sm text-[var(--text-primary)] leading-relaxed w-full">

          {isThinking && (
            <div className="space-y-2">
              <div className="h-1 w-48 rounded-full overflow-hidden bg-[var(--bg-input)]">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-[var(--accent)] via-[var(--accent-light)] to-[var(--accent)]"
                  style={{
                    animation: 'shimmer 1.5s infinite',
                    backgroundSize: '200% 100%',
                  }}
                />
              </div>
              <span className="text-xs text-[var(--text-muted)]">
                {getStatusLabel(statusText, toolText)}
              </span>
            </div>
          )}

          {toolText && text && (
            <div className="flex items-center gap-1.5 text-xs text-[var(--text-muted)] mb-2">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-[var(--accent)] animate-pulse" />
              <span>{toolText}</span>
            </div>
          )}

          {text && (
            <div className="prose-neura">
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={streamingComponents}>
                {text}
              </ReactMarkdown>
              <span
                className="inline-block w-[2px] h-[1em] bg-[var(--accent)] ml-0.5 align-middle rounded-sm"
                style={{
                  animation: 'blink 1s ease-in-out infinite',
                }}
              />
            </div>
          )}
        </div>

        <button
          onClick={onStop}
          className="flex items-center gap-1.5 text-xs text-[var(--text-muted)] hover:text-red-400 border border-[var(--border)] hover:border-red-500/50 px-3 py-1 rounded-md transition-all duration-150"
        >
          <Square size={10} fill="currentColor" />
          Остановить
        </button>
      </div>
    </div>
  )
}

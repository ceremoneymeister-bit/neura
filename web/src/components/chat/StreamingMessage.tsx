import { Square } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { Components } from 'react-markdown'
import { CodeBlock } from './CodeBlock'
import { NeuraIcon } from '@/components/ui/NeuraIcon'

interface StreamingMessageProps {
  text: string
  statusText: string | null
  toolText: string | null
  onStop: () => void
}

function getStatusIcon(statusText: string | null, toolText: string | null, text: string): string {
  if (text) return '\u270D\uFE0F'
  if (toolText) return '\uD83D\uDD27'
  if (statusText?.includes('\u0414\u0443\u043C\u0430')) return '\u23F3'
  return '\u23F3'
}

const streamingComponents: Components = {
  code({ className, children }) {
    const match = /language-(\w+)/.exec(className ?? '')
    const lang = match?.[1] ?? ''
    if (match) {
      return <CodeBlock language={lang} code={String(children).replace(/\n$/, '')} />
    }
    return (
      <code className="font-mono text-xs bg-[#1e1e1e] px-1.5 py-0.5 rounded text-[#e879f9] border border-[#262626]">
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
        className="text-[#7c3aed] underline hover:text-[#a78bfa] transition-colors"
      >
        {children}
      </a>
    )
  },
}

export function StreamingMessage({ text, statusText, toolText, onStop }: StreamingMessageProps) {
  const isThinking = !text
  const statusIcon = getStatusIcon(statusText, toolText, text)

  return (
    <div className="flex gap-3 px-4 py-3 animate-fade-in will-change-transform">
      {/* NeuraIcon avatar */}
      <div className="shrink-0 mt-0.5 select-none">
        <NeuraIcon size={28} />
      </div>

      <div className="flex flex-col gap-2 max-w-[88%] min-w-0 items-start">
        <div className="px-4 py-3 rounded-[12px] bg-[#141414] border border-[#262626] border-l-2 border-l-[#7c3aed]/30 text-sm text-[#e4e4e4] leading-relaxed w-full">

          {/* Thinking state — animated gradient bar + status text */}
          {isThinking && (
            <div className="space-y-2">
              <div className="h-1 w-48 rounded-full overflow-hidden bg-[#1e1e1e]">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-[#7c3aed] via-[#a78bfa] to-[#7c3aed]"
                  style={{
                    animation: 'shimmer 1.5s infinite',
                    backgroundSize: '200% 100%',
                  }}
                />
              </div>
              <span className="text-xs text-[#525252] flex items-center gap-1.5">
                {statusIcon} {toolText ?? statusText ?? '\u0414\u0443\u043C\u0430\u044E...'}
              </span>
            </div>
          )}

          {/* Tool indicator shown alongside streaming text */}
          {toolText && text && (
            <div className="flex items-center gap-1.5 text-xs text-[#525252] mb-2">
              <span className="animate-pulse">{'\u2699'}</span>
              <span>{toolText}</span>
            </div>
          )}

          {/* Streaming text with markdown + smooth blinking cursor */}
          {text && (
            <div className="prose-neura">
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={streamingComponents}>
                {text}
              </ReactMarkdown>
              <span
                className="inline-block w-[2px] h-[1em] bg-[#7c3aed] ml-0.5 align-middle rounded-sm"
                style={{
                  animation: 'blink 1s ease-in-out infinite',
                }}
              />
            </div>
          )}
        </div>

        {/* Stop generating button */}
        <button
          onClick={onStop}
          className="flex items-center gap-1.5 text-xs text-[#525252] hover:text-red-400 border border-[#262626] hover:border-red-500/50 px-3 py-1 rounded-[6px] transition-all duration-150"
        >
          <Square size={10} fill="currentColor" />
          Остановить
        </button>
      </div>
    </div>
  )
}

import { useState, useCallback } from 'react'
import { Copy, Check, RefreshCw, Clock } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { Components } from 'react-markdown'
import type { Message } from '@/api/conversations'
import { CodeBlock } from './CodeBlock'
import { NeuraIcon } from '@/components/ui/NeuraIcon'

interface MessageBubbleProps {
  message: Message
  isLast?: boolean
  onRegenerate?: () => void
}

function formatTime(dateStr: string | null): string {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
}

const markdownComponents: Components = {
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
        className="text-[#7c3aed] underline underline-offset-2 hover:text-[#a78bfa] transition-colors"
      >
        {children}
      </a>
    )
  },
  table({ children }) {
    return (
      <div className="overflow-x-auto my-3">
        <table className="border-collapse w-full text-sm">{children}</table>
      </div>
    )
  },
  th({ children }) {
    return (
      <th className="border border-[#262626] px-3 py-2 text-left text-[#a3a3a3] font-medium bg-[#1a1a1a]">
        {children}
      </th>
    )
  },
  td({ children }) {
    return (
      <td className="border border-[#262626] px-3 py-2 text-[#e4e4e4]">
        {children}
      </td>
    )
  },
  blockquote({ children }) {
    return (
      <blockquote className="border-l-2 border-[#7c3aed] pl-4 my-2 text-[#a3a3a3] italic">
        {children}
      </blockquote>
    )
  },
  hr() {
    return <hr className="border-none border-t border-[#262626] my-4" />
  },
}

export function MessageBubble({ message, isLast = false, onRegenerate }: MessageBubbleProps) {
  const [copied, setCopied] = useState(false)
  const isUser = message.role === 'user'

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(message.content)
    } catch {
      // clipboard API unavailable
    }
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }, [message.content])

  if (isUser) {
    return (
      <div className="group flex justify-end px-4 py-3 animate-fade-in will-change-transform">
        <div className="flex flex-col items-end gap-1 max-w-[88%] min-w-0">
          {/* User bubble — no avatar, right-aligned */}
          <div className="relative px-4 py-3 rounded-[12px] text-sm leading-relaxed break-words bg-[#7c3aed]/15 border border-[#7c3aed]/25 text-[#f5f5f5]">
            {/* Attached files */}
            {message.files && message.files.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mb-2">
                {message.files.map((f, i) => (
                  <span
                    key={i}
                    className="text-[11px] px-2 py-0.5 rounded bg-[#262626] text-[#a3a3a3] max-w-[160px] truncate"
                  >
                    📎 {f.split('/').pop()}
                  </span>
                ))}
              </div>
            )}
            <p className="whitespace-pre-wrap">{message.content}</p>
          </div>

          {/* Hover actions below — copy + time */}
          <div className="flex items-center gap-1.5 flex-row-reverse opacity-0 group-hover:opacity-100 transition-opacity duration-150">
            <button
              onClick={handleCopy}
              title="Копировать"
              className="flex items-center gap-1 text-[11px] text-[#525252] hover:text-[#a3a3a3] transition-colors p-1 rounded hover:bg-[#1a1a1a]"
            >
              {copied ? <Check size={11} /> : <Copy size={11} />}
            </button>

            {message.created_at && (
              <span className="flex items-center gap-0.5 text-[10px] text-[#3a3a3a]">
                <Clock size={9} />
                {formatTime(message.created_at)}
              </span>
            )}
          </div>
        </div>
      </div>
    )
  }

  // Assistant message
  return (
    <div className="group relative flex gap-3 px-4 py-3 animate-fade-in will-change-transform">
      {/* NeuraIcon avatar */}
      <div className="shrink-0 mt-0.5 select-none">
        <NeuraIcon size={28} />
      </div>

      {/* Content */}
      <div className="flex flex-col gap-1 max-w-[88%] min-w-0 items-start">
        <div className="relative px-4 py-3 rounded-[12px] text-sm leading-relaxed break-words bg-[#141414] border border-[#262626] border-l-2 border-l-[#7c3aed]/30 text-[#e4e4e4]">
          {/* Hover toolbar — top-right of the message */}
          <div className="absolute -top-7 right-0 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-150 bg-[#1e1e1e] border border-[#262626] rounded-[6px] px-1.5 py-0.5 shadow-lg">
            <button
              onClick={handleCopy}
              title="Копировать"
              className="flex items-center gap-1 text-[11px] text-[#525252] hover:text-[#a3a3a3] transition-colors p-1 rounded hover:bg-[#262626]"
            >
              {copied ? <Check size={11} /> : <Copy size={11} />}
            </button>

            {isLast && onRegenerate && (
              <button
                onClick={onRegenerate}
                title="Перегенерировать"
                className="flex items-center gap-1 text-[11px] text-[#525252] hover:text-[#a3a3a3] transition-colors p-1 rounded hover:bg-[#262626]"
              >
                <RefreshCw size={11} />
              </button>
            )}

            {message.created_at && (
              <span className="flex items-center gap-0.5 text-[10px] text-[#3a3a3a] px-1">
                <Clock size={9} />
                {formatTime(message.created_at)}
              </span>
            )}

            {message.duration_sec != null && (
              <span className="text-[10px] text-[#3a3a3a]">
                {message.duration_sec.toFixed(1)}s
              </span>
            )}
          </div>

          {/* Attached files */}
          {message.files && message.files.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-2">
              {message.files.map((f, i) => (
                <span
                  key={i}
                  className="text-[11px] px-2 py-0.5 rounded bg-[#262626] text-[#a3a3a3] max-w-[160px] truncate"
                >
                  📎 {f.split('/').pop()}
                </span>
              ))}
            </div>
          )}

          {/* Message content — markdown */}
          <div className="prose-neura">
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
              {message.content}
            </ReactMarkdown>
          </div>
        </div>
      </div>
    </div>
  )
}

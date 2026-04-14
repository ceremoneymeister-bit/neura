import { useState, useCallback, useEffect } from 'react'
import { Copy, Check, RefreshCw, X, Download, ThumbsUp, ThumbsDown } from 'lucide-react'
import { AnimatePresence, motion } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { Components } from 'react-markdown'
import type { Message } from '@/api/conversations'
import { CodeBlock } from './CodeBlock'
import { FilePreview } from './FilePreview'
import { fileIcon } from '@/utils/time'
import { copyToClipboard } from '@/utils/clipboard'

function formatModel(model: string): string {
  if (model.includes('opus')) return 'Opus'
  if (model.includes('haiku')) return 'Haiku'
  if (model.includes('sonnet')) return 'Sonnet'
  return model.split('-')[0]
}

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
      <code className="font-mono text-xs bg-[var(--bg-input)] px-1.5 py-0.5 rounded text-[var(--code-inline)] border border-[var(--border)] break-all">
        {children}
      </code>
    )
  },
  a({ href, children }) {
    // Intercept file links → FilePreview
    if (href?.includes('/api/files/serve/')) {
      const filename = href.split('/').pop() ?? ''
      return <FilePreview url={href} filename={filename} />
    }
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="text-[var(--accent)] underline underline-offset-2 hover:text-[var(--accent-light)] transition-colors"
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
      <th className="border border-[var(--border)] px-3 py-2 text-left text-[var(--text-secondary)] font-medium bg-[var(--bg-hover)]">
        {children}
      </th>
    )
  },
  td({ children }) {
    return (
      <td className="border border-[var(--border)] px-3 py-2 text-[var(--text-primary)]">
        {children}
      </td>
    )
  },
  blockquote({ children }) {
    return (
      <blockquote className="border-l-2 border-[var(--accent)] pl-4 my-2 text-[var(--text-secondary)] italic">
        {children}
      </blockquote>
    )
  },
  hr() {
    return <hr className="border-none border-t border-[var(--border)] my-4" />
  },
  img({ src, alt }) {
    return (
      <button
        type="button"
        onClick={() => {
          document.dispatchEvent(new CustomEvent('neura:lightbox', { detail: { src, alt } }))
        }}
        className="block my-3 cursor-pointer bg-transparent border-0 p-0"
      >
        <img
          src={src}
          alt={alt ?? ''}
          loading="lazy"
          className="max-w-full max-h-[400px] rounded-lg border border-[var(--border)] object-contain hover:opacity-90 transition-opacity"
        />
      </button>
    )
  },
}

export function ImageLightbox() {
  const [image, setImage] = useState<{ src: string; alt: string } | null>(null)

  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail
      if (detail?.src) setImage({ src: detail.src, alt: detail.alt ?? '' })
    }
    document.addEventListener('neura:lightbox', handler)
    return () => document.removeEventListener('neura:lightbox', handler)
  }, [])

  useEffect(() => {
    if (!image) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setImage(null)
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [image])

  return (
    <AnimatePresence>
      {image && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
          className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
          onClick={() => setImage(null)}
        >
          <div className="absolute top-4 right-4 flex gap-2 z-10">
            <a
              href={image.src}
              download
              onClick={(e) => e.stopPropagation()}
              className="p-2 rounded-lg bg-white/10 hover:bg-white/20 text-white transition-colors"
              title="Скачать"
            >
              <Download size={18} />
            </a>
            <button
              onClick={() => setImage(null)}
              className="p-2 rounded-lg bg-white/10 hover:bg-white/20 text-white transition-colors"
              title="Закрыть"
            >
              <X size={18} />
            </button>
          </div>
          <img
            src={image.src}
            alt={image.alt}
            className="max-w-[90vw] max-h-[90vh] object-contain rounded-lg"
            onClick={(e) => e.stopPropagation()}
          />
        </motion.div>
      )}
    </AnimatePresence>
  )
}

// ── Action bar (Claude-style: hover-only, minimal) ──────────────

function ActionBar({
  onCopy,
  copied,
  time,
  model,
  duration,
  isLast,
  onRegenerate,
  messageId,
  align = 'left',
}: {
  onCopy: () => void
  copied: boolean
  time?: string | null
  model?: string | null
  duration?: number | null
  tokens?: number | null
  isLast?: boolean
  onRegenerate?: () => void
  messageId?: number
  align?: 'left' | 'right'
}) {
  const [vote, setVote] = useState<'up' | 'down' | null>(null)
  const [showFeedback, setShowFeedback] = useState(false)
  const [feedbackText, setFeedbackText] = useState('')

  const sendFeedback = useCallback(async (type: 'up' | 'down', comment?: string) => {
    setVote(type)
    if (type === 'up') setShowFeedback(false)
    try {
      const token = localStorage.getItem('neura_token')
      await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ message_id: messageId, vote: type, comment: comment || null }),
      })
    } catch { /* silent */ }
  }, [messageId])

  const handleThumbDown = useCallback(() => {
    if (vote === 'down') return
    setShowFeedback(true)
  }, [vote])

  const submitNegative = useCallback(() => {
    sendFeedback('down', feedbackText)
    setShowFeedback(false)
    setFeedbackText('')
  }, [sendFeedback, feedbackText])

  const isAssistant = align === 'left'

  return (
    <div className={`flex flex-col gap-1.5 mt-1 ${align === 'right' ? 'items-end' : 'items-start'}`}>
      {/* Action buttons — hidden until hover on message */}
      <div className={`flex items-center gap-0.5 opacity-0 group-hover/msg:opacity-100 transition-opacity duration-150 ${align === 'right' ? 'justify-end' : ''}`}>
        {/* Copy */}
        <button
          onClick={onCopy}
          title="Копировать"
          className="p-1.5 rounded-md text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition-colors"
        >
          {copied ? <Check size={14} className="text-green-400" /> : <Copy size={14} />}
        </button>

        {/* Thumbs — only for assistant */}
        {isAssistant && (
          <>
            <button
              onClick={() => vote !== 'up' && sendFeedback('up')}
              title="Хороший ответ"
              className={`p-1.5 rounded-md transition-colors ${vote === 'up' ? 'text-green-400' : 'text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)]'}`}
            >
              <ThumbsUp size={14} />
            </button>
            <button
              onClick={handleThumbDown}
              title="Плохой ответ"
              className={`p-1.5 rounded-md transition-colors ${vote === 'down' ? 'text-red-400' : 'text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)]'}`}
            >
              <ThumbsDown size={14} />
            </button>
          </>
        )}

        {/* Regenerate */}
        {isLast && onRegenerate && (
          <button
            onClick={onRegenerate}
            title="Повторить"
            className="p-1.5 rounded-md text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition-colors"
          >
            <RefreshCw size={14} />
          </button>
        )}

        {/* Meta — compact */}
        {model && (
          <span className="text-[10px] ml-2 text-[var(--text-muted)] font-mono">
            {formatModel(model)}
          </span>
        )}
        {duration != null && (
          <span className="text-[10px] text-[var(--text-muted)]">{duration.toFixed(1)}s</span>
        )}
        {time && (
          <span className="text-[10px] text-[var(--text-muted)] ml-1">{time}</span>
        )}
      </div>

      {/* Negative feedback form */}
      {showFeedback && (
        <div className="flex gap-2 items-end w-full max-w-md animate-fade-in">
          <input
            type="text"
            value={feedbackText}
            onChange={(e) => setFeedbackText(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && submitNegative()}
            placeholder="Что не так с ответом?"
            autoFocus
            className="flex-1 text-sm px-3 py-1.5 rounded-lg bg-[var(--bg-input)] border border-[var(--border)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:border-[var(--accent)] focus:outline-none"
          />
          <button
            onClick={submitNegative}
            className="text-xs px-3 py-1.5 rounded-lg bg-[var(--accent)]/20 text-[var(--accent)] hover:bg-[var(--accent)]/30 transition-colors"
          >
            Отправить
          </button>
          <button
            onClick={() => { setShowFeedback(false); setFeedbackText('') }}
            className="text-xs px-2 py-1.5 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
          >
            ✕
          </button>
        </div>
      )}
    </div>
  )
}

// ── Message bubble ──────────────────────────────────────────────

export function MessageBubble({ message, isLast = false, onRegenerate }: MessageBubbleProps) {
  const [copied, setCopied] = useState(false)
  const isUser = message.role === 'user'

  const handleCopy = useCallback(async () => {
    await copyToClipboard(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }, [message.content])

  if (isUser) {
    return (
      <div className="group/msg flex justify-end px-4 py-3 animate-fade-in will-change-transform">
        <div className="flex flex-col items-end gap-0 max-w-[88%] min-w-0">
          <div className="relative px-4 py-2.5 rounded-2xl text-[15px] leading-[1.7] break-words bg-[var(--bg-hover)] text-[var(--text-primary)]">
            {message.files && message.files.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mb-2">
                {message.files.map((f, i) => (
                  <span
                    key={i}
                    className="text-[11px] px-2 py-0.5 rounded bg-[var(--border)] text-[var(--text-secondary)] max-w-[160px] truncate"
                  >
                    {fileIcon(f.split('/').pop() ?? f)} {f.split('/').pop()}
                  </span>
                ))}
              </div>
            )}
            <p className="whitespace-pre-wrap">{message.content}</p>
          </div>

          <ActionBar
            onCopy={handleCopy}
            copied={copied}
            time={formatTime(message.created_at)}
            messageId={message.id}
            align="right"
          />
        </div>
      </div>
    )
  }

  return (
    <div className="group/msg flex px-4 py-3 animate-fade-in will-change-transform">
      <div className="flex flex-col gap-0 max-w-[min(720px,100%)] min-w-0 items-start">
        <div className="relative py-1 text-[15px] leading-[1.7] break-words overflow-hidden text-[var(--text-primary)]">
          {message.files && message.files.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-2">
              {message.files.map((f, i) => (
                <span
                  key={i}
                  className="text-[11px] px-2 py-0.5 rounded bg-[var(--border)] text-[var(--text-secondary)] max-w-[160px] truncate"
                >
                  {f.split('/').pop()}
                </span>
              ))}
            </div>
          )}

          <div className="prose-neura">
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
              {message.content}
            </ReactMarkdown>
          </div>
        </div>

        <ActionBar
          onCopy={handleCopy}
          copied={copied}
          time={formatTime(message.created_at)}
          model={message.model}
          duration={message.duration_sec}
          messageId={message.id}
          isLast={isLast}
          onRegenerate={onRegenerate}
        />
      </div>
    </div>
  )
}

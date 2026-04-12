import { useState, useCallback, useEffect } from 'react'
import { Copy, Check, RefreshCw, Clock, X, Download } from 'lucide-react'
import { AnimatePresence, motion } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { Components } from 'react-markdown'
import type { Message } from '@/api/conversations'
import { CodeBlock } from './CodeBlock'
import { NeuraIcon } from '@/components/ui/NeuraIcon'
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
      <div className="group flex justify-end px-4 py-3 animate-fade-in will-change-transform">
        <div className="flex flex-col items-end gap-1 max-w-[88%] min-w-0">
          <div className="relative px-4 py-3 rounded-xl text-sm leading-relaxed break-words bg-[var(--accent)]/15 border border-[var(--accent)]/25 text-[var(--text-primary)]">
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

          <div className="flex items-center gap-1.5 flex-row-reverse hover-hide">
            <button
              onClick={handleCopy}
              title="Копировать"
              className="flex items-center gap-1 text-[11px] text-[var(--text-muted)] hover:text-[var(--text-secondary)] transition-colors p-1 rounded hover:bg-[var(--bg-hover)]"
            >
              {copied ? <Check size={11} /> : <Copy size={11} />}
            </button>
            {message.created_at && (
              <span className="flex items-center gap-0.5 text-[10px] text-[var(--text-muted)]">
                <Clock size={9} />
                {formatTime(message.created_at)}
              </span>
            )}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="group relative flex gap-3 px-4 py-3 animate-fade-in will-change-transform">
      <div className="shrink-0 mt-0.5 select-none">
        <NeuraIcon size={28} />
      </div>

      <div className="flex flex-col gap-1 max-w-[88%] min-w-0 items-start">
        <div className="relative px-4 py-3 rounded-xl text-sm leading-relaxed break-words overflow-hidden bg-[var(--bg-card)] border border-[var(--border)] border-l-2 border-l-[var(--accent)]/30 text-[var(--text-primary)]">
          <div className="absolute -top-7 right-0 z-10 flex items-center gap-1 hover-hide bg-[var(--bg-input)] border border-[var(--border)] rounded-md px-1.5 py-0.5 shadow-lg">
            <button
              onClick={handleCopy}
              title="Копировать"
              className="flex items-center gap-1 text-[11px] text-[var(--text-muted)] hover:text-[var(--text-secondary)] transition-colors p-1 rounded hover:bg-[var(--border)]"
            >
              {copied ? <Check size={11} /> : <Copy size={11} />}
            </button>
            {isLast && onRegenerate && (
              <button
                onClick={onRegenerate}
                title="Перегенерировать"
                className="flex items-center gap-1 text-[11px] text-[var(--text-muted)] hover:text-[var(--text-secondary)] transition-colors p-1 rounded hover:bg-[var(--border)]"
              >
                <RefreshCw size={11} />
              </button>
            )}
            {message.created_at && (
              <span className="flex items-center gap-0.5 text-[10px] text-[var(--text-muted)] px-1">
                <Clock size={9} />
                {formatTime(message.created_at)}
              </span>
            )}
            {message.duration_sec != null && (
              <span className="text-[10px] text-[var(--text-muted)]">
                {message.duration_sec.toFixed(1)}s
              </span>
            )}
          </div>

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

          {(message.model || message.duration_sec != null || message.tokens_used != null) && (
            <div className="flex items-center gap-2 mt-2 pt-2 border-t border-[var(--border)]/50">
              {message.model && (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--accent)]/10 text-[var(--accent)] font-mono">
                  {formatModel(message.model)}
                </span>
              )}
              {message.duration_sec != null && (
                <span className="text-[10px] text-[var(--text-muted)]">{message.duration_sec.toFixed(1)}s</span>
              )}
              {message.tokens_used != null && (
                <span className="text-[10px] text-[var(--text-muted)]">{message.tokens_used} tok</span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

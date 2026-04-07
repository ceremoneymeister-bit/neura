import { useState, useMemo } from 'react'
import { Check, Copy } from 'lucide-react'
import hljs from 'highlight.js/lib/common'
import { copyToClipboard } from '@/utils/clipboard'

interface CodeBlockProps {
  language: string
  code: string
}

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

export function CodeBlock({ language, code }: CodeBlockProps) {
  const [copied, setCopied] = useState(false)

  const highlighted = useMemo(() => {
    try {
      if (language && hljs.getLanguage(language)) {
        return hljs.highlight(code, { language, ignoreIllegals: true }).value
      }
      return hljs.highlightAuto(code).value
    } catch {
      return escapeHtml(code)
    }
  }, [code, language])

  const lines = code.split('\n')
  const showLineNumbers = lines.length > 5

  const handleCopy = async () => {
    await copyToClipboard(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="relative my-3 rounded-md overflow-hidden border border-[var(--border)] bg-[#131312]">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-1.5 bg-[var(--bg-sidebar)] border-b border-[var(--border)]">
        <span className="text-[11px] font-mono text-[var(--text-muted)] uppercase tracking-wide select-none">
          {language || 'text'}
        </span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 text-[11px] text-[var(--text-muted)] hover:text-[var(--text-secondary)] transition-colors py-0.5 px-2 rounded hover:bg-[var(--bg-hover)]"
        >
          {copied ? <Check size={11} /> : <Copy size={11} />}
          <span>{copied ? 'Скопировано' : 'Копировать'}</span>
        </button>
      </div>

      {/* Code body */}
      <div className="overflow-x-auto max-h-[400px] overflow-y-auto flex">
        {showLineNumbers && (
          <div
            aria-hidden
            className="select-none shrink-0 py-3 px-3 text-right leading-6 text-xs font-mono text-[var(--text-muted)]/50 bg-[#171716] border-r border-[var(--border)]"
          >
            {lines.map((_line, idx) => (
              <div key={idx}>{idx + 1}</div>
            ))}
          </div>
        )}
        <pre className="flex-1 p-3 m-0 text-sm leading-6 font-mono overflow-x-auto bg-transparent text-[var(--text-primary)]">
          <code dangerouslySetInnerHTML={{ __html: highlighted }} />
        </pre>
      </div>
    </div>
  )
}

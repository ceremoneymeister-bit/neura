import { useState, useMemo } from 'react'
import { Check, Copy } from 'lucide-react'
import hljs from 'highlight.js/lib/common'

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
    try {
      await navigator.clipboard.writeText(code)
    } catch {
      // clipboard API unavailable
    }
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="relative my-3 rounded-[6px] overflow-hidden border border-[#262626] bg-[#0d0d0d]">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-1.5 bg-[#141414] border-b border-[#262626]">
        <span className="text-[11px] font-mono text-[#525252] uppercase tracking-wide select-none">
          {language || 'text'}
        </span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 text-[11px] text-[#525252] hover:text-[#a3a3a3] transition-colors py-0.5 px-2 rounded hover:bg-[#1a1a1a]"
        >
          {copied ? <Check size={11} /> : <Copy size={11} />}
          <span>{copied ? 'Copied!' : 'Copy'}</span>
        </button>
      </div>

      {/* Code body */}
      <div className="overflow-x-auto max-h-[400px] overflow-y-auto flex">
        {showLineNumbers && (
          <div
            aria-hidden
            className="select-none shrink-0 py-3 px-3 text-right leading-6 text-xs font-mono text-[#3a3a3a] bg-[#0a0a0a] border-r border-[#1e1e1e]"
          >
            {lines.map((_line, idx) => (
              <div key={idx}>{idx + 1}</div>
            ))}
          </div>
        )}
        <pre className="flex-1 p-3 m-0 text-sm leading-6 font-mono overflow-x-auto bg-transparent text-[#e4e4e4]">
          <code dangerouslySetInnerHTML={{ __html: highlighted }} />
        </pre>
      </div>
    </div>
  )
}

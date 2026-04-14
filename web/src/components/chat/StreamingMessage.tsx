import { useState, useEffect } from 'react'
import {
  Square, FileText, Pencil, Terminal, Search, Globe, FolderSearch, FileCode, Check,
} from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { Components } from 'react-markdown'
import { CodeBlock } from './CodeBlock'
import type { ToolStep } from '@/hooks/useWebSocket'

interface StreamingMessageProps {
  text: string
  statusText: string | null
  toolText: string | null
  toolSteps?: ToolStep[]
  onStop: () => void
}

// ── Thinking phases — rotate through to show activity ────────────

const THINKING_PHASES = [
  'Анализирую запрос',
  'Подбираю подход',
  'Формирую ответ',
]

function useThinkingPhase(isThinking: boolean, statusText: string | null): string {
  const [phaseIdx, setPhaseIdx] = useState(0)

  useEffect(() => {
    if (!isThinking) { setPhaseIdx(0); return }
    // If server sends a specific status, use it
    if (statusText) return
    const timer = setInterval(() => {
      setPhaseIdx(i => (i + 1) % THINKING_PHASES.length)
    }, 3000)
    return () => clearInterval(timer)
  }, [isThinking, statusText])

  if (statusText) {
    return statusText.replace(/^[\u2699\uFE0F\u23F3\uD83C-\uDBFF\uDC00-\uDFFF\s]+/, '')
  }
  return THINKING_PHASES[phaseIdx]
}

// ── Elapsed timer ────────────────────────────────────────────────

function useElapsed(active: boolean): number {
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    if (!active) { setElapsed(0); return }
    const start = Date.now()
    const timer = setInterval(() => {
      setElapsed(Math.floor((Date.now() - start) / 1000))
    }, 1000)
    return () => clearInterval(timer)
  }, [active])

  return elapsed
}

const streamingComponents: Components = {
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

// ── Tool icon mapping ────────────────────────────────────────────

const TOOL_ICONS: Record<string, typeof FileText> = {
  Read: FileText,
  Write: FileCode,
  Edit: Pencil,
  Bash: Terminal,
  Grep: Search,
  Glob: FolderSearch,
  WebSearch: Globe,
  WebFetch: Globe,
}

function StepIcon({ tool, status }: { tool: string; status: 'running' | 'done' }) {
  if (status === 'done') {
    return (
      <div className="w-5 h-5 rounded-full bg-emerald-500/15 flex items-center justify-center shrink-0">
        <Check size={10} className="text-emerald-400" />
      </div>
    )
  }
  const Icon = TOOL_ICONS[tool] ?? Terminal
  return (
    <div className="w-5 h-5 rounded-full bg-[var(--accent)]/15 flex items-center justify-center shrink-0">
      <Icon size={10} className="text-[var(--accent)] animate-pulse" />
    </div>
  )
}

function StepDetail({ detail }: { detail?: ToolStep['detail'] }) {
  if (!detail) return null
  const text = detail.file ?? detail.command ?? detail.pattern ?? detail.query ?? ''
  if (!text) return null
  const isBash = !!detail.command
  return (
    <span className={`text-[11px] truncate max-w-[280px] ${
      isBash
        ? 'font-mono text-emerald-400/70 bg-[var(--bg-primary)] px-1.5 py-0.5 rounded'
        : 'text-[var(--text-muted)]'
    }`}>
      {text}
    </span>
  )
}

function AgentSteps({ steps, collapsed = false }: { steps: ToolStep[]; collapsed?: boolean }) {
  const [isOpen, setIsOpen] = useState(!collapsed)

  // Auto-open when new steps arrive
  useEffect(() => {
    if (!collapsed) setIsOpen(true)
  }, [steps.length, collapsed])

  if (steps.length === 0) return null

  const doneCount = steps.filter((s) => s.status === 'done').length
  const summary = `${doneCount}/${steps.length} шагов`

  if (collapsed && !isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="flex items-center gap-2 text-[11px] text-[var(--text-muted)] hover:text-[var(--text-secondary)] mb-2 transition-colors"
      >
        <span className="inline-block w-1.5 h-1.5 rounded-full bg-[var(--accent)]" />
        <span>{summary}</span>
        <span className="opacity-50">▸</span>
      </button>
    )
  }

  return (
    <div className="space-y-0.5 mb-1">
      {collapsed && (
        <button
          onClick={() => setIsOpen(false)}
          className="flex items-center gap-2 text-[11px] text-[var(--text-muted)] hover:text-[var(--text-secondary)] mb-1 transition-colors"
        >
          <span>{summary}</span>
          <span className="opacity-50">▾</span>
        </button>
      )}
      {/* Timeline */}
      <div className="relative pl-3 border-l border-[var(--border)]/60">
        {steps.map((step, i) => (
          <div key={step.tool_id} className="flex items-center gap-2 py-1 relative">
            {/* Dot on timeline */}
            <div className="absolute -left-[calc(0.75rem+3px)]">
              <StepIcon tool={step.tool} status={step.status} />
            </div>
            {/* Label */}
            <div className="flex items-center gap-2 min-w-0 pl-3">
              <span className={`text-xs whitespace-nowrap ${
                step.status === 'done' ? 'text-[var(--text-muted)]' : 'text-[var(--text-secondary)]'
              }`}>
                {step.label.replace(/^[^\s]+\s/, '')}
              </span>
              <StepDetail detail={step.detail} />
              {step.status === 'running' && (
                <span className="text-[10px] text-[var(--text-muted)] tabular-nums animate-pulse">
                  …
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export function StreamingMessage({ text, statusText, toolText, toolSteps = [], onStop }: StreamingMessageProps) {
  const isThinking = !text
  const phaseLabel = useThinkingPhase(isThinking, statusText)
  const elapsed = useElapsed(true)

  return (
    <div className="group/msg flex px-4 py-3 animate-fade-in will-change-transform">
      <div className="flex flex-col gap-2 max-w-[min(720px,100%)] min-w-0 items-start">
        <div className="py-1 text-[15px] text-[var(--text-primary)] leading-relaxed min-w-0 overflow-hidden">

          {/* Thinking state — no text yet */}
          {isThinking && (
            <div className="space-y-3">
              {/* Phase label + timer */}
              <div className="flex items-center gap-3">
                <div className="h-1 w-32 rounded-full overflow-hidden bg-[var(--bg-input)]">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-[var(--accent)] via-[var(--accent-light)] to-[var(--accent)]"
                    style={{ animation: 'shimmer 1.5s infinite', backgroundSize: '200% 100%' }}
                  />
                </div>
                <span className="text-xs text-[var(--text-muted)] tabular-nums">{elapsed}с</span>
              </div>

              {/* Agent Steps Timeline */}
              {toolSteps.length > 0 && <AgentSteps steps={toolSteps} />}

              {/* Fallback: old-style tool text when no structured steps */}
              {toolSteps.length === 0 && toolText && (
                <div className="flex items-center gap-2 text-xs text-[var(--text-muted)] px-2.5 py-1.5 rounded-lg bg-[var(--bg-input)] border border-[var(--border)]">
                  <span className="inline-block w-1.5 h-1.5 rounded-full bg-[var(--accent)] animate-pulse shrink-0" />
                  <span className="text-[var(--text-secondary)]">{toolText}</span>
                </div>
              )}
            </div>
          )}

          {/* Agent steps while streaming text (collapsible) */}
          {text && toolSteps.length > 0 && (
            <AgentSteps steps={toolSteps} collapsed />
          )}

          {/* Streaming text with cursor */}
          {text && (
            <div className="prose-neura">
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={streamingComponents}>
                {text}
              </ReactMarkdown>
              <span
                className="inline-block w-[2px] h-[1em] bg-[var(--accent)] ml-0.5 align-middle rounded-sm"
                style={{ animation: 'blink 1s ease-in-out infinite' }}
              />
            </div>
          )}
        </div>

        {/* Stop button + elapsed */}
        <div className="flex items-center gap-3">
          <button
            onClick={onStop}
            className="flex items-center gap-1.5 text-xs text-[var(--text-muted)] hover:text-red-400 border border-[var(--border)] hover:border-red-500/50 px-3 py-1 rounded-md transition-all duration-150"
          >
            <Square size={10} fill="currentColor" />
            Остановить
          </button>
          {text && (
            <span className="text-[10px] text-[var(--text-muted)] tabular-nums">
              {elapsed}с
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

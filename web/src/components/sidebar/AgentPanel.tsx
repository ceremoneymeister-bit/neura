import { useEffect, useState } from 'react'
import { Activity, ChevronDown, ChevronUp, Cpu, Zap } from 'lucide-react'
import { api } from '@/api/client'
import { useAuth } from '@/hooks/useAuth'

interface AgentMetrics {
  status: string
  capsule?: {
    id: string
    name: string
    model: string
  } | null
  uptime_sec: number
  requests_total?: number
  errors_total?: number
  avg_duration_sec?: number
  skills?: string[]
}

// Short display names for model IDs
const MODEL_LABELS: Record<string, string> = {
  sonnet: 'Sonnet',
  opus: 'Opus',
  haiku: 'Haiku',
  'claude-sonnet-4-6': 'Sonnet 4.6',
  'claude-opus-4-6': 'Opus 4.6',
  'claude-haiku-4-5': 'Haiku 4.5',
  'claude-haiku-4-5-20251001': 'Haiku 4.5',
}

function modelLabel(m: string): string {
  return MODEL_LABELS[m] ?? m
}

export function AgentPanel() {
  const { token } = useAuth()
  const [open, setOpen] = useState(false)
  const [metrics, setMetrics] = useState<AgentMetrics | null>(null)

  useEffect(() => {
    if (!token) return
    let active = true

    const fetchMetrics = () => {
      api
        .get<AgentMetrics>('/api/metrics')
        .then((m) => { if (active) setMetrics(m) })
        .catch(() => {})
    }

    fetchMetrics()
    const interval = setInterval(fetchMetrics, 30_000)
    return () => {
      active = false
      clearInterval(interval)
    }
  }, [token])

  const isOnline = metrics?.status === 'online'
  const model = metrics?.capsule?.model ?? 'sonnet'
  const capsuleName = metrics?.capsule?.name
  const reqTotal = metrics?.requests_total ?? 0
  const errTotal = metrics?.errors_total ?? 0
  const avgDur = metrics?.avg_duration_sec
  const skills = metrics?.skills ?? []

  return (
    <div className="border-t border-[#1a1a1a]">
      {/* Collapsed header — always visible */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-2 px-3 py-2 hover:bg-[var(--bg-hover)] transition-colors"
      >
        {/* Status dot with glow when online */}
        <span
          className={[
            'inline-block w-1.5 h-1.5 rounded-full flex-shrink-0',
            isOnline
              ? 'bg-emerald-500 shadow-[0_0_5px_#10b981]'
              : 'bg-[#525252]',
          ].join(' ')}
        />

        <span className="flex-1 text-left text-[11px] text-[var(--text-secondary)] truncate">
          {capsuleName ?? (isOnline ? 'Агент' : 'Офлайн')}
        </span>

        <span className="text-[10px] text-[var(--text-muted)] font-mono flex-shrink-0">
          {modelLabel(model)}
        </span>

        {open
          ? <ChevronUp size={11} className="text-[var(--text-muted)] flex-shrink-0" />
          : <ChevronDown size={11} className="text-[var(--text-muted)] flex-shrink-0" />}
      </button>

      {/* Expanded panel */}
      {open && (
        <div className="px-3 pb-3 space-y-2">
          {/* Status row */}
          <div className="flex items-center gap-2 text-[11px] text-[var(--text-muted)]">
            <Activity size={11} />
            <span>Статус</span>
            <span
              className={[
                'ml-auto font-medium',
                isOnline ? 'text-emerald-400' : 'text-[var(--text-muted)]',
              ].join(' ')}
            >
              {isOnline ? 'Online' : 'Offline'}
            </span>
          </div>

          {/* Model row */}
          <div className="flex items-center gap-2 text-[11px] text-[var(--text-muted)]">
            <Cpu size={11} />
            <span>Модель</span>
            <span className="ml-auto text-[var(--text-secondary)] font-mono">{modelLabel(model)}</span>
          </div>

          {/* Requests row */}
          <div className="flex items-center gap-2 text-[11px] text-[var(--text-muted)]">
            <Zap size={11} />
            <span>Запросы</span>
            <span className="ml-auto text-[var(--text-secondary)]">
              {reqTotal} req
              {errTotal > 0 && (
                <span className="text-red-400 ml-1">· {errTotal} err</span>
              )}
            </span>
          </div>

          {/* Average duration */}
          {avgDur !== undefined && avgDur > 0 && (
            <div className="flex items-center gap-2 text-[11px] text-[var(--text-muted)]">
              <span className="w-[11px] text-center">⏱</span>
              <span>Среднее</span>
              <span className="ml-auto text-[var(--text-secondary)]">{avgDur.toFixed(1)}s</span>
            </div>
          )}

          {/* Skills badges */}
          {skills.length > 0 && (
            <div>
              <p className="text-[10px] text-[var(--text-muted)] mb-1">
                Скиллы ({skills.length})
              </p>
              <div className="flex flex-wrap gap-1">
                {skills.map((s) => (
                  <span
                    key={s}
                    className="px-1.5 py-0.5 rounded-[4px] bg-[var(--bg-hover)] border border-[var(--border)] text-[var(--text-secondary)] text-[10px]"
                  >
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* No data yet placeholder */}
          {!metrics && (
            <p className="text-[10px] text-[var(--text-muted)] text-center py-1">
              Загрузка данных...
            </p>
          )}
        </div>
      )}
    </div>
  )
}

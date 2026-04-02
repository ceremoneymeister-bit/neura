import { useEffect, useState } from 'react'
import { api, ApiError } from '@/api/client'
import { useAuth } from '@/hooks/useAuth'

interface Metrics {
  status: string
  capsule?: {
    id: string
    name: string
    model: string
  } | null
  uptime_sec: number
}

export function StatusBar() {
  const { token } = useAuth()
  const [metrics, setMetrics] = useState<Metrics | null>(null)

  useEffect(() => {
    if (!token) return
    let active = true
    const fetch = () => {
      api.get<Metrics>('/api/metrics')
        .then((m) => { if (active) setMetrics(m) })
        .catch((e) => {
          if (e instanceof ApiError && e.status === 401) return
          // silently ignore
        })
    }
    fetch()
    const interval = setInterval(fetch, 30_000)
    return () => {
      active = false
      clearInterval(interval)
    }
  }, [token])

  const model = metrics?.capsule?.model ?? 'sonnet'
  const isOnline = metrics?.status === 'online'

  return (
    <div className="flex items-center gap-3 px-4 h-7 bg-[#0f0f0f] border-t border-[#1a1a1a] text-[11px] text-[#525252] shrink-0">
      {/* Status dot */}
      <span className={`inline-block w-1.5 h-1.5 rounded-full ${isOnline ? 'bg-emerald-500' : 'bg-[#525252]'}`} />
      <span className="text-[#a3a3a3] font-mono">{model}</span>
      {metrics?.capsule?.name && (
        <>
          <span className="text-[#333]">·</span>
          <span className="truncate max-w-[120px]">{metrics.capsule.name}</span>
        </>
      )}
      <span className="ml-auto">Neura v2</span>
    </div>
  )
}

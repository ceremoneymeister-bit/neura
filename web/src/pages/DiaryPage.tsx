import { useCallback, useEffect, useState } from 'react'
import { BookOpen, Search, ChevronLeft, ChevronRight, Clock, Cpu, Wrench } from 'lucide-react'
import { getDiary, searchDiary, type DiaryEntry } from '@/api/diary'

function formatDate(d: Date): string {
  return d.toISOString().slice(0, 10)
}

function prettyDate(d: Date): string {
  return d.toLocaleDateString('ru-RU', { weekday: 'long', day: 'numeric', month: 'long' })
}

export function DiaryPage() {
  const [entries, setEntries] = useState<DiaryEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [date, setDate] = useState(() => new Date())
  const [searchQuery, setSearchQuery] = useState('')
  const [isSearching, setIsSearching] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getDiary(formatDate(date), 100)
      setEntries(data)
    } catch {
      setEntries([])
    } finally {
      setLoading(false)
    }
  }, [date])

  useEffect(() => {
    if (!isSearching) load()
  }, [load, isSearching])

  const handleSearch = useCallback(async () => {
    if (!searchQuery.trim()) {
      setIsSearching(false)
      return
    }
    setIsSearching(true)
    setLoading(true)
    try {
      const data = await searchDiary(searchQuery.trim(), 50)
      setEntries(data)
    } catch {
      setEntries([])
    } finally {
      setLoading(false)
    }
  }, [searchQuery])

  const prevDay = () => {
    setIsSearching(false)
    setSearchQuery('')
    setDate((d) => {
      const n = new Date(d)
      n.setDate(n.getDate() - 1)
      return n
    })
  }

  const nextDay = () => {
    setIsSearching(false)
    setSearchQuery('')
    setDate((d) => {
      const n = new Date(d)
      n.setDate(n.getDate() + 1)
      return n > new Date() ? d : n
    })
  }

  const today = () => {
    setIsSearching(false)
    setSearchQuery('')
    setDate(new Date())
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-3xl mx-auto px-4 py-6">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <BookOpen size={20} className="text-[var(--accent)]" />
          <h1 className="text-lg font-semibold text-[var(--text-primary)]">Дневник</h1>
        </div>

        {/* Search */}
        <div className="flex gap-2 mb-4">
          <div className="relative flex-1">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Поиск по истории..."
              className="w-full h-9 pl-9 pr-4 text-sm rounded-lg liquid-glass-input text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none focus:border-[var(--accent)]"
            />
          </div>
          {isSearching && (
            <button
              onClick={() => { setIsSearching(false); setSearchQuery('') }}
              className="text-xs text-[var(--text-muted)] hover:text-[var(--text-secondary)] px-3 py-2 rounded-lg hover:bg-[var(--bg-hover)] transition-colors"
            >
              Сбросить
            </button>
          )}
        </div>

        {/* Date nav */}
        {!isSearching && (
          <div className="flex items-center justify-between mb-6">
            <button onClick={prevDay} className="p-2 rounded-lg hover:bg-[var(--bg-hover)] text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors">
              <ChevronLeft size={16} />
            </button>
            <button onClick={today} className="text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors capitalize">
              {prettyDate(date)}
            </button>
            <button onClick={nextDay} className="p-2 rounded-lg hover:bg-[var(--bg-hover)] text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors">
              <ChevronRight size={16} />
            </button>
          </div>
        )}

        {/* Entries */}
        {loading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-4 animate-pulse">
                <div className="h-3 w-24 bg-[var(--skeleton-from)] rounded mb-3" />
                <div className="h-4 w-3/4 bg-[var(--skeleton-from)] rounded mb-2" />
                <div className="h-4 w-1/2 bg-[var(--skeleton-from)] rounded" />
              </div>
            ))}
          </div>
        ) : entries.length === 0 ? (
          <div className="text-center py-16">
            <BookOpen size={32} className="mx-auto text-[var(--text-muted)] mb-3" />
            <p className="text-sm text-[var(--text-muted)]">
              {isSearching ? 'Ничего не найдено' : 'Нет записей за этот день'}
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {entries.map((entry) => (
              <DiaryCard key={entry.id} entry={entry} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function DiaryCard({ entry }: { entry: DiaryEntry }) {
  const [expanded, setExpanded] = useState(false)
  const botPreview = entry.bot_response?.slice(0, 200) ?? ''
  const isLong = (entry.bot_response?.length ?? 0) > 200

  return (
    <div className="rounded-xl liquid-glass p-4 transition-colors hover:border-[var(--accent)]/20">
      {/* Meta */}
      <div className="flex items-center gap-3 mb-2 text-[10px] text-[var(--text-muted)]">
        <span className="flex items-center gap-1">
          <Clock size={10} />
          {entry.time?.slice(0, 5) ?? entry.created_at?.slice(11, 16)}
        </span>
        {entry.model && (
          <span className="flex items-center gap-1">
            <Cpu size={10} />
            {entry.model.includes('opus') ? 'Opus' : entry.model.includes('haiku') ? 'Haiku' : 'Sonnet'}
          </span>
        )}
        {entry.duration_sec != null && (
          <span>{entry.duration_sec.toFixed(1)}s</span>
        )}
        {entry.tools_used && (
          <span className="flex items-center gap-1">
            <Wrench size={10} />
            {entry.tools_used}
          </span>
        )}
        {entry.source && (
          <span className="px-2 py-0.5 rounded-full bg-[var(--accent)]/10 text-[var(--accent)] backdrop-blur-sm border border-[var(--accent)]/15">
            {entry.source}
          </span>
        )}
      </div>

      {/* User message */}
      <p className="text-sm text-[var(--text-primary)] mb-2 font-medium">
        {entry.user_message?.slice(0, 300) || '(без текста)'}
      </p>

      {/* Bot response */}
      <div className="text-sm text-[var(--text-secondary)] leading-relaxed">
        {expanded ? entry.bot_response : botPreview}
        {isLong && !expanded && '...'}
      </div>

      {isLong && (
        <button
          onClick={() => setExpanded((v) => !v)}
          className="text-xs text-[var(--accent)] hover:text-[var(--accent-light)] mt-2 transition-colors"
        >
          {expanded ? 'Свернуть' : 'Показать полностью'}
        </button>
      )}
    </div>
  )
}

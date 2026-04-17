import { useCallback, useEffect, useState } from 'react'
import { Brain, Trash2, Lightbulb, AlertCircle } from 'lucide-react'
import { getMemory, deleteMemory, getLearnings, type MemoryEntry, type LearningEntry } from '@/api/memory'
import { useToast } from '@/components/ui/Toast'

type Tab = 'memory' | 'learnings'

export function MemoryPage() {
  const { success, error: showError } = useToast()
  const [tab, setTab] = useState<Tab>('memory')
  const [memories, setMemories] = useState<MemoryEntry[]>([])
  const [learnings, setLearnings] = useState<LearningEntry[]>([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      if (tab === 'memory') {
        setMemories(await getMemory(100))
      } else {
        setLearnings(await getLearnings(100))
      }
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }, [tab])

  useEffect(() => { load() }, [load])

  const handleDelete = async (id: number) => {
    if (!window.confirm('Удалить эту запись?')) return
    try {
      await deleteMemory(id)
      setMemories((prev) => prev.filter((m) => m.id !== id))
      success('Удалено')
    } catch {
      showError('Не удалось удалить')
    }
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-3xl mx-auto px-4 py-6">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <Brain size={20} className="text-[var(--accent)]" />
          <h1 className="text-lg font-semibold text-[var(--text-primary)]">Память</h1>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-6 p-1 rounded-lg liquid-glass w-fit">
          <button
            onClick={() => setTab('memory')}
            className={`px-4 py-1.5 text-xs rounded-full transition-colors ${tab === 'memory' ? 'bg-[var(--accent)]/15 text-[var(--accent)] font-medium' : 'text-[var(--text-muted)] hover:text-[var(--text-secondary)]'}`}
          >
            Факты ({memories.length})
          </button>
          <button
            onClick={() => setTab('learnings')}
            className={`px-4 py-1.5 text-xs rounded-full transition-colors ${tab === 'learnings' ? 'bg-[var(--accent)]/15 text-[var(--accent)] font-medium' : 'text-[var(--text-muted)] hover:text-[var(--text-secondary)]'}`}
          >
            Уроки
          </button>
        </div>

        {/* Content */}
        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-4 animate-pulse">
                <div className="h-4 w-3/4 bg-[var(--skeleton-from)] rounded" />
              </div>
            ))}
          </div>
        ) : tab === 'memory' ? (
          memories.length === 0 ? (
            <div className="text-center py-16">
              <Brain size={32} className="mx-auto text-[var(--text-muted)] mb-3" />
              <p className="text-sm text-[var(--text-muted)]">Бот ещё ничего не запомнил</p>
            </div>
          ) : (
            <div className="space-y-2">
              {memories.map((m) => (
                <div key={m.id} className="group flex items-start gap-3 rounded-xl liquid-glass p-4 hover:border-[var(--accent)]/20 transition-colors">
                  <Lightbulb size={14} className="text-[var(--accent)] mt-0.5 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-[var(--text-primary)] leading-relaxed">{m.content}</p>
                    <div className="flex items-center gap-2 mt-1.5 text-[10px] text-[var(--text-muted)]">
                      {m.source && <span>{m.source}</span>}
                      <span>{new Date(m.created_at).toLocaleDateString('ru-RU')}</span>
                    </div>
                  </div>
                  <button
                    onClick={() => handleDelete(m.id)}
                    className="opacity-0 group-hover:opacity-100 p-1.5 rounded-md text-[var(--text-muted)] hover:text-red-400 hover:bg-red-500/10 transition-all"
                    title="Удалить"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              ))}
            </div>
          )
        ) : (
          learnings.length === 0 ? (
            <div className="text-center py-16">
              <AlertCircle size={32} className="mx-auto text-[var(--text-muted)] mb-3" />
              <p className="text-sm text-[var(--text-muted)]">Уроков пока нет</p>
            </div>
          ) : (
            <div className="space-y-2">
              {learnings.map((l) => (
                <div key={l.id} className="flex items-start gap-3 rounded-xl liquid-glass p-4 hover:border-[var(--accent)]/20 transition-colors">
                  <span className={`text-xs px-1.5 py-0.5 rounded font-mono shrink-0 ${l.type === 'correction' ? 'bg-orange-500/10 text-orange-400' : 'bg-green-500/10 text-green-400'}`}>
                    {l.type === 'correction' ? 'Коррекция' : 'Урок'}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-[var(--text-primary)] leading-relaxed">{l.content}</p>
                    <div className="flex items-center gap-2 mt-1.5 text-[10px] text-[var(--text-muted)]">
                      {l.source && <span>{l.source}</span>}
                      <span>{new Date(l.created_at).toLocaleDateString('ru-RU')}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )
        )}
      </div>
    </div>
  )
}

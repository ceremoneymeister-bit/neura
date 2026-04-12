import { useCallback, useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Heart, Plus, Trash2, Clock, Zap, Bell, Pencil, AlertCircle,
} from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Modal } from '@/components/ui/Modal'
import { useToast } from '@/components/ui/Toast'
import {
  type HeartbeatTask,
  listHeartbeats,
  createHeartbeat,
  updateHeartbeat,
  deleteHeartbeat,
} from '@/api/heartbeat'

// ── Schedule presets ─────────────────────────────────────────────

const SCHEDULE_PRESETS = [
  { label: 'Каждый день', value: 'daily', icon: Clock },
  { label: 'Пн', value: 'monday', icon: Clock },
  { label: 'Вт', value: 'tuesday', icon: Clock },
  { label: 'Ср', value: 'wednesday', icon: Clock },
  { label: 'Чт', value: 'thursday', icon: Clock },
  { label: 'Пт', value: 'friday', icon: Clock },
  { label: 'Сб', value: 'saturday', icon: Clock },
  { label: 'Вс', value: 'sunday', icon: Clock },
  { label: 'Каждые 2ч', value: 'every 2h', icon: Zap },
  { label: 'Каждые 4ч', value: 'every 4h', icon: Zap },
] as const

function scheduleToLabel(schedule: string): string {
  const s = schedule.toLowerCase().trim()
  if (s.startsWith('daily')) return 'Каждый день'
  if (s.startsWith('monday') || s.startsWith('пн')) return 'Понедельник'
  if (s.startsWith('tuesday') || s.startsWith('вт')) return 'Вторник'
  if (s.startsWith('wednesday') || s.startsWith('ср')) return 'Среда'
  if (s.startsWith('thursday') || s.startsWith('чт')) return 'Четверг'
  if (s.startsWith('friday') || s.startsWith('пт')) return 'Пятница'
  if (s.startsWith('saturday') || s.startsWith('сб')) return 'Суббота'
  if (s.startsWith('sunday') || s.startsWith('вс')) return 'Воскресенье'
  if (s.startsWith('every')) return s.replace('every ', 'Каждые ')
  return schedule
}

function extractTime(schedule: string): string {
  const m = schedule.match(/(\d{1,2}:\d{2})/)
  return m ? m[1] : '10:00'
}

function timeToMinutes(t: string): number {
  const [h, m] = t.split(':').map(Number)
  return h * 60 + m
}

function minutesToTime(mins: number): string {
  const total = mins % (24 * 60)
  const h = Math.floor(total / 60).toString().padStart(2, '0')
  const m = (total % 60).toString().padStart(2, '0')
  return `${h}:${m}`
}

// Convert snake_case technical name to readable title
function formatName(name: string): string {
  return name
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

// Detect if message is a script path, not human text
function isScriptMessage(message: string): boolean {
  const m = message.trim()
  return (
    m.startsWith('python3 ') ||
    m.startsWith('python ') ||
    m.startsWith('bash ') ||
    m.startsWith('/') ||
    m.startsWith('./') ||
    m.endsWith('.py') ||
    m.endsWith('.sh')
  )
}

// ── Empty state ──────────────────────────────────────────────────

function EmptyState({ onCreate }: { onCreate: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col items-center justify-center gap-4 py-20 text-center"
    >
      <div className="w-16 h-16 rounded-2xl bg-[var(--accent)]/10 flex items-center justify-center">
        <Heart size={28} className="text-[var(--accent)]" />
      </div>
      <div>
        <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-1">
          Нет напоминаний
        </h2>
        <p className="text-sm text-[var(--text-muted)] max-w-xs">
          Создайте напоминание или автозадачу — агент будет
          присылать их по расписанию
        </p>
      </div>
      <Button onClick={onCreate} icon={<Plus size={16} />}>
        Создать первое
      </Button>
    </motion.div>
  )
}

// ── Card ─────────────────────────────────────────────────────────

interface CardProps {
  task: HeartbeatTask
  onToggle: (name: string, enabled: boolean) => void
  onEdit: (task: HeartbeatTask) => void
  onDelete: (name: string) => void
}

function HeartbeatCard({ task, onToggle, onEdit, onDelete }: CardProps) {
  const isTask = task.type === 'task'

  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.15 }}
      className={[
        'group relative rounded-xl border p-4 transition-all duration-200',
        task.enabled
          ? 'bg-[var(--bg-card)] border-[var(--border)] hover:border-[var(--accent)]/40 hover:shadow-lg hover:shadow-[var(--accent)]/5'
          : 'bg-[var(--bg-primary)] border-[var(--border)]/50 opacity-60',
      ].join(' ')}
    >
      {/* Header row */}
      <div className="flex items-start gap-3 mb-3">
        <div className={[
          'mt-0.5 w-8 h-8 rounded-lg flex items-center justify-center shrink-0',
          isTask
            ? 'bg-amber-500/15 text-amber-400'
            : 'bg-[var(--accent)]/10 text-[var(--accent)]',
        ].join(' ')}>
          {isTask ? <Zap size={16} /> : <Bell size={16} />}
        </div>

        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-medium text-[var(--text-primary)] truncate">
            {task.display_name || formatName(task.name)}
          </h3>
          <p className="text-xs text-[var(--text-muted)] mt-0.5">
            {scheduleToLabel(task.schedule)}
            <span className="mx-1.5 opacity-40">·</span>
            {extractTime(task.schedule)}
          </p>
        </div>

        {/* Toggle */}
        <button
          onClick={() => onToggle(task.name, !task.enabled)}
          className={[
            'relative w-9 h-5 rounded-full transition-colors duration-200 shrink-0',
            task.enabled ? 'bg-[var(--accent)]' : 'bg-[var(--border)]',
          ].join(' ')}
          aria-label={task.enabled ? 'Выключить' : 'Включить'}
        >
          <span className={[
            'absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform duration-200 shadow-sm',
            task.enabled ? 'left-[18px]' : 'left-0.5',
          ].join(' ')} />
        </button>
      </div>

      {/* Message preview */}
      <p className="text-xs text-[var(--text-secondary)] line-clamp-2 leading-relaxed mb-3">
        {isScriptMessage(task.message)
          ? <span className="italic text-[var(--text-muted)]">Выполняет скрипт по расписанию</span>
          : task.message}
      </p>

      {/* Badge + actions */}
      <div className="flex items-center justify-between">
        <span className={[
          'text-[10px] font-medium uppercase tracking-wider px-2 py-0.5 rounded-md',
          isTask
            ? 'bg-amber-500/10 text-amber-400'
            : 'bg-[var(--accent)]/10 text-[var(--accent)]',
        ].join(' ')}>
          {isTask ? 'Автозадача' : 'Напоминание'}
        </span>

        <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={() => onEdit(task)}
            className="p-1.5 rounded-md text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition-colors"
            title="Редактировать"
          >
            <Pencil size={14} />
          </button>
          <button
            onClick={() => onDelete(task.name)}
            className="p-1.5 rounded-md text-[var(--text-muted)] hover:text-red-400 hover:bg-red-500/10 transition-colors"
            title="Удалить"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>
    </motion.div>
  )
}

// ── Form Modal ───────────────────────────────────────────────────

interface FormData {
  name: string
  display_name: string
  message: string
  scheduleBase: string
  time: string
  type: 'reminder' | 'task'
}

function HeartbeatFormModal({
  open,
  onClose,
  onSubmit,
  initial,
  loading,
  existingTasks,
}: {
  open: boolean
  onClose: () => void
  onSubmit: (data: FormData) => void
  initial?: HeartbeatTask | null
  loading: boolean
  existingTasks: HeartbeatTask[]
}) {
  const [form, setForm] = useState<FormData>({
    name: '',
    display_name: '',
    message: '',
    scheduleBase: 'daily',
    time: '10:00',
    type: 'reminder',
  })
  const [conflictWarning, setConflictWarning] = useState<{
    taskName: string
    suggestedTime: string
  } | null>(null)

  useEffect(() => {
    if (open) {
      if (initial) {
        const base = initial.schedule.replace(/\s*\d{1,2}:\d{2}/, '').trim() || 'daily'
        setForm({
          name: initial.name,
          display_name: initial.display_name || '',
          message: initial.message,
          scheduleBase: base.startsWith('every') ? base : base.toLowerCase(),
          time: extractTime(initial.schedule),
          type: initial.type,
        })
      } else {
        setForm({ name: '', display_name: '', message: '', scheduleBase: 'daily', time: '10:00', type: 'reminder' })
      }
    }
  }, [open, initial])

  const isInterval = form.scheduleBase.startsWith('every')

  useEffect(() => {
    if (isInterval) { setConflictWarning(null); return }
    const targetMins = timeToMinutes(form.time)
    const conflicts = existingTasks.filter(t => {
      if (t.name === initial?.name) return false
      if (t.schedule.startsWith('every')) return false
      const tBase = t.schedule.replace(/\s*\d{1,2}:\d{2}/, '').trim()
      if (tBase !== form.scheduleBase) return false
      return Math.abs(timeToMinutes(extractTime(t.schedule)) - targetMins) <= 5
    })
    if (conflicts.length > 0) {
      const maxMins = Math.max(...conflicts.map(t => timeToMinutes(extractTime(t.schedule))))
      setConflictWarning({ taskName: conflicts[0].name, suggestedTime: minutesToTime(maxMins + 5) })
    } else {
      setConflictWarning(null)
    }
  }, [form.scheduleBase, form.time, isInterval, existingTasks, initial])

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={initial ? 'Редактировать' : 'Новая автоматизация'}
      className="max-w-lg"
    >
      <div className="space-y-4">
        <Input
          label="Системное имя"
          placeholder="утренний_дайджест"
          value={form.name}
          onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
          disabled={!!initial}
        />

        <Input
          label="Название (как видите вы)"
          placeholder={form.name ? formatName(form.name) : 'Утренний дайджест'}
          value={form.display_name}
          onChange={(e) => setForm((f) => ({ ...f, display_name: e.target.value }))}
        />

        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-medium text-[var(--text-secondary)]">Сообщение</label>
          <textarea
            className="w-full rounded-lg bg-[var(--bg-input)] border border-[var(--border)] text-[var(--text-primary)] placeholder-[var(--text-muted)] px-3 py-2 text-sm focus:outline-none focus:border-[var(--accent)]/50 resize-none"
            rows={3}
            placeholder={form.type === 'task' ? 'Промпт для Claude...' : 'Текст напоминания...'}
            value={form.message}
            onChange={(e) => setForm((f) => ({ ...f, message: e.target.value }))}
          />
        </div>

        {/* Type selector */}
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-medium text-[var(--text-secondary)]">Тип</label>
          <div className="flex gap-2">
            {(['reminder', 'task'] as const).map((t) => (
              <button
                key={t}
                onClick={() => setForm((f) => ({ ...f, type: t }))}
                className={[
                  'flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg border text-sm transition-all',
                  form.type === t
                    ? 'border-[var(--accent)] bg-[var(--accent)]/10 text-[var(--accent)]'
                    : 'border-[var(--border)] text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]',
                ].join(' ')}
              >
                {t === 'task' ? <Zap size={14} /> : <Bell size={14} />}
                {t === 'task' ? 'Автозадача' : 'Напоминание'}
              </button>
            ))}
          </div>
          <p className="text-[11px] text-[var(--text-muted)]">
            {form.type === 'task'
              ? 'Агент выполнит промпт через Claude и пришлёт результат'
              : 'Агент отправит текст напоминания как есть'}
          </p>
        </div>

        {/* Schedule */}
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-medium text-[var(--text-secondary)]">Расписание</label>
          <div className="flex flex-wrap gap-1.5">
            {SCHEDULE_PRESETS.map((p) => (
              <button
                key={p.value}
                onClick={() => setForm((f) => ({ ...f, scheduleBase: p.value }))}
                className={[
                  'px-2.5 py-1 rounded-md text-xs transition-all',
                  form.scheduleBase === p.value
                    ? 'bg-[var(--accent)] text-white'
                    : 'bg-[var(--bg-input)] text-[var(--text-secondary)] border border-[var(--border)] hover:bg-[var(--bg-hover)]',
                ].join(' ')}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {/* Time picker (only for non-interval) */}
        {!isInterval && (
          <Input
            label="Время (МСК)"
            type="time"
            value={form.time}
            onChange={(e) => setForm((f) => ({ ...f, time: e.target.value }))}
          />
        )}

        {/* Conflict warning */}
        {conflictWarning && (
          <div className="flex items-start gap-2 px-3 py-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20">
            <AlertCircle size={14} className="text-amber-400 mt-0.5 shrink-0" />
            <p className="text-xs text-amber-300/90 leading-relaxed">
              В это время уже работает «{conflictWarning.taskName}».
              Задачи могут конкурировать за агента.{' '}
              <button
                type="button"
                onClick={() => setForm(f => ({ ...f, time: conflictWarning.suggestedTime }))}
                className="font-medium underline hover:no-underline text-amber-300"
              >
                Сдвинуть на {conflictWarning.suggestedTime}
              </button>
            </p>
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="ghost" onClick={onClose} disabled={loading}>
            Отмена
          </Button>
          <Button
            onClick={() => onSubmit(form)}
            loading={loading}
            disabled={!form.name.trim() || !form.message.trim()}
          >
            {initial ? 'Сохранить' : 'Создать'}
          </Button>
        </div>
      </div>
    </Modal>
  )
}

// ── Page ─────────────────────────────────────────────────────────

export function HeartbeatPage() {
  const [tasks, setTasks] = useState<HeartbeatTask[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<HeartbeatTask | null>(null)
  const { toast } = useToast()

  const load = useCallback(async () => {
    try {
      setLoading(true)
      const data = await listHeartbeats()
      setTasks(data)
    } catch {
      toast('Не удалось загрузить напоминания', 'error')
    } finally {
      setLoading(false)
    }
  }, [toast])

  useEffect(() => { load() }, [load])

  const handleCreate = () => {
    setEditing(null)
    setModalOpen(true)
  }

  const handleEdit = (task: HeartbeatTask) => {
    setEditing(task)
    setModalOpen(true)
  }

  const handleToggle = async (name: string, enabled: boolean) => {
    // Optimistic update
    setTasks((prev) => prev.map((t) => t.name === name ? { ...t, enabled } : t))
    try {
      await updateHeartbeat(name, { enabled })
    } catch {
      toast('Ошибка при обновлении', 'error')
      load()
    }
  }

  const handleDelete = async (name: string) => {
    setTasks((prev) => prev.filter((t) => t.name !== name))
    try {
      await deleteHeartbeat(name)
      toast('Удалено', 'success')
    } catch {
      toast('Ошибка при удалении', 'error')
      load()
    }
  }

  const handleSubmit = async (data: FormData) => {
    setSaving(true)
    try {
      const schedule = data.scheduleBase.startsWith('every')
        ? data.scheduleBase
        : `${data.scheduleBase} ${data.time}`

      if (editing) {
        await updateHeartbeat(editing.name, {
          display_name: data.display_name.trim() || null,
          message: data.message,
          schedule,
          type: data.type,
        })
        toast('Обновлено', 'success')
      } else {
        await createHeartbeat({
          name: data.name.trim().replace(/\s+/g, '_'),
          display_name: data.display_name.trim() || undefined,
          message: data.message,
          schedule,
          type: data.type,
        })
        toast('Создано', 'success')
      }
      setModalOpen(false)
      load()
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Ошибка'
      toast(msg, 'error')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="h-full overflow-y-auto">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
          <div className="flex items-center gap-3 mb-6">
            <div className="skeleton w-10 h-10 rounded-xl" />
            <div>
              <div className="skeleton h-5 w-24 rounded mb-1" />
              <div className="skeleton h-3 w-48 rounded" />
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="rounded-xl border border-[var(--border)] p-4">
                <div className="flex items-start gap-3 mb-3">
                  <div className="skeleton w-8 h-8 rounded-lg" />
                  <div className="flex-1">
                    <div className="skeleton h-4 w-2/3 rounded mb-1.5" />
                    <div className="skeleton h-3 w-1/3 rounded" />
                  </div>
                </div>
                <div className="skeleton h-3 w-full rounded mb-1.5" />
                <div className="skeleton h-3 w-3/4 rounded" />
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[var(--accent)]/10 flex items-center justify-center">
              <Heart size={20} className="text-[var(--accent)]" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-[var(--text-primary)]">Автоматизации</h1>
              <p className="text-xs text-[var(--text-muted)]">Напоминания и автозадачи по расписанию</p>
            </div>
          </div>
          {tasks.length > 0 && (
            <Button size="sm" onClick={handleCreate} icon={<Plus size={14} />}>
              Добавить
            </Button>
          )}
        </div>

        {/* Content */}
        {tasks.length === 0 ? (
          <EmptyState onCreate={handleCreate} />
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            <AnimatePresence mode="popLayout">
              {tasks.map((task) => (
                <HeartbeatCard
                  key={task.name}
                  task={task}
                  onToggle={handleToggle}
                  onEdit={handleEdit}
                  onDelete={handleDelete}
                />
              ))}
            </AnimatePresence>
          </div>
        )}

        {/* Stats footer */}
        {tasks.length > 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-6 flex items-center gap-4 text-xs text-[var(--text-muted)]"
          >
            <span>{tasks.length} {tasks.length === 1 ? 'задача' : tasks.length < 5 ? 'задачи' : 'задач'}</span>
            <span className="opacity-40">·</span>
            <span>{tasks.filter((t) => t.enabled).length} активных</span>
            <span className="opacity-40">·</span>
            <span>{tasks.filter((t) => t.type === 'task').length} автозадач</span>
          </motion.div>
        )}
      </div>

      {/* Form modal */}
      <HeartbeatFormModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSubmit={handleSubmit}
        initial={editing}
        loading={saving}
        existingTasks={tasks}
      />
    </div>
  )
}

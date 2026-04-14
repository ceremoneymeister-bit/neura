import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { useAuth } from '@/hooks/useAuth'
import { Avatar } from '@/components/ui/Avatar'
import { Button } from '@/components/ui/Button'
import { LogOut, Keyboard, Info, Sparkles, User, Sun, Moon, Monitor, Cpu, Zap } from 'lucide-react'
import { useTheme, type ThemePreference } from '@/hooks/useTheme'
import { api } from '@/api/client'

const MODELS = [
  {
    id: 'sonnet-4-6',
    label: 'Claude Sonnet 4.6',
    desc: 'Быстрый и умный — оптимальный баланс скорости и качества',
  },
  {
    id: 'opus-4-6',
    label: 'Claude Opus 4.6',
    desc: 'Максимальный интеллект для сложных задач и анализа',
  },
  {
    id: 'haiku-4-5',
    label: 'Claude Haiku 4.5',
    desc: 'Сверхбыстрый — мгновенные ответы на простые вопросы',
  },
]

const ENGINES = [
  {
    id: 'claude',
    label: 'Claude Code',
    desc: 'Anthropic CLI — максимальное качество, подписка Max',
    icon: '🧠',
  },
  {
    id: 'opencode',
    label: 'OpenCode',
    desc: 'Open-source агент — любые модели через API',
    icon: '⚡',
  },
  {
    id: 'yandex',
    label: 'YandexGPT',
    desc: 'Яндекс — русскоязычная модель, быстрая и дешёвая',
    icon: '🔍',
  },
]

const SHORTCUTS = [
  { keys: 'Ctrl + K', action: 'Поиск' },
  { keys: 'Ctrl + B', action: 'Переключить боковую панель' },
  { keys: 'Ctrl + Shift + N', action: 'Новый чат' },
  { keys: 'Enter', action: 'Отправить сообщение' },
  { keys: 'Shift + Enter', action: 'Новая строка' },
  { keys: 'Esc', action: 'Закрыть панель (мобильные)' },
  { keys: '\u2191 \u2193', action: 'Навигация по чатам' },
]

const THEMES: { id: ThemePreference; label: string; desc: string; icon: React.ReactNode }[] = [
  { id: 'light', label: 'Светлая', desc: 'Светлый фон, тёмный текст', icon: <Sun size={16} /> },
  { id: 'dark', label: 'Тёмная', desc: 'Тёмный фон, светлый текст', icon: <Moon size={16} /> },
  { id: 'system', label: 'Системная', desc: 'Следует настройкам устройства', icon: <Monitor size={16} /> },
]

interface OpenCodeModel {
  id: string
  label: string
  price: string
  tier: string
}

export function SettingsPage() {
  const { user, logout } = useAuth()
  const { preference, setPreference } = useTheme()
  const [selectedModel, setSelectedModel] = useState(
    () => localStorage.getItem('neura_model') ?? 'sonnet-4-6'
  )
  const [selectedEngine, setSelectedEngine] = useState('claude')
  const [selectedOpenCodeModel, setSelectedOpenCodeModel] = useState('')
  const [openCodeModels, setOpenCodeModels] = useState<OpenCodeModel[]>([])
  const [selectedYandexModel, setSelectedYandexModel] = useState('')
  const [yandexModels, setYandexModels] = useState<OpenCodeModel[]>([])
  const [engineLoading, setEngineLoading] = useState(false)

  useEffect(() => {
    api.get<{engine: string; opencode_model: string; models: OpenCodeModel[]; yandex_model: string; yandex_models: OpenCodeModel[]}>('/api/engine')
      .then(data => {
        setSelectedEngine(data.engine || 'claude')
        setSelectedOpenCodeModel(data.opencode_model || '')
        setOpenCodeModels(data.models || [])
        setSelectedYandexModel(data.yandex_model || 'yandexgpt-lite')
        setYandexModels(data.yandex_models || [])
      })
      .catch(() => {})
  }, [])

  const updateEngine = async (engine: string) => {
    setSelectedEngine(engine)
    setEngineLoading(true)
    try {
      await api.post('/api/engine', { engine })
    } catch {}
    setEngineLoading(false)
  }

  const updateOpenCodeModel = async (modelId: string) => {
    setSelectedOpenCodeModel(modelId)
    setEngineLoading(true)
    try {
      await api.post('/api/engine', { opencode_model: modelId })
    } catch {}
    setEngineLoading(false)
  }

  const updateYandexModel = async (modelId: string) => {
    setSelectedYandexModel(modelId)
    setEngineLoading(true)
    try {
      await api.post('/api/engine', { yandex_model: modelId })
    } catch {}
    setEngineLoading(false)
  }

  return (
    <div className="h-full overflow-y-auto">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="max-w-2xl mx-auto px-4 py-8"
      >
        <h1 className="text-lg font-semibold text-[var(--text-primary)] mb-8">Настройки</h1>

        <Section title="Профиль" icon={<User size={14} />}>
          <div className="flex items-center gap-4">
            <Avatar name={user?.name ?? ''} size="lg" />
            <div className="min-w-0">
              <p className="text-sm font-medium text-[var(--text-primary)] truncate">
                {user?.name ?? 'Пользователь'}
              </p>
              <p className="text-xs text-[var(--text-muted)] truncate">{user?.email}</p>
              {user?.capsule_id && (
                <p className="text-xs text-[var(--accent)] mt-0.5">
                  Capsule: {user.capsule_id}
                </p>
              )}
            </div>
          </div>
        </Section>

        <Section title="Тема" icon={<Sun size={14} />}>
          <div className="flex gap-2">
            {THEMES.map((t) => (
              <button
                key={t.id}
                onClick={() => setPreference(t.id)}
                className={[
                  'flex-1 flex flex-col items-center gap-2 px-3 py-3.5 rounded-lg border transition-all',
                  preference === t.id
                    ? 'border-[var(--accent)] bg-[var(--accent)]/10'
                    : 'border-[var(--border)] bg-[var(--bg-hover)] hover:border-[var(--text-muted)]/30',
                ].join(' ')}
              >
                <span className={preference === t.id ? 'text-[var(--accent)]' : 'text-[var(--text-muted)]'}>
                  {t.icon}
                </span>
                <span className="text-sm text-[var(--text-primary)]">{t.label}</span>
                <span className="text-[10px] text-[var(--text-muted)] leading-tight text-center">{t.desc}</span>
              </button>
            ))}
          </div>
        </Section>

        <Section title="Модель по умолчанию" icon={<Sparkles size={14} />}>
          <div className="flex flex-col gap-2">
            {MODELS.map((m) => (
              <button
                key={m.id}
                onClick={() => {
                  setSelectedModel(m.id)
                  localStorage.setItem('neura_model', m.id)
                }}
                className={[
                  'flex items-center gap-3 px-3.5 py-3 rounded-lg border transition-all text-left',
                  selectedModel === m.id
                    ? 'border-[var(--accent)] bg-[var(--accent)]/10'
                    : 'border-[var(--border)] bg-[var(--bg-hover)] hover:border-[var(--text-muted)]/30',
                ].join(' ')}
              >
                <span
                  className={[
                    'w-3.5 h-3.5 rounded-full border-2 shrink-0 transition-colors',
                    selectedModel === m.id
                      ? 'border-[var(--accent)] bg-[var(--accent)]'
                      : 'border-[var(--text-muted)]',
                  ].join(' ')}
                />
                <div className="min-w-0">
                  <p className="text-sm text-[var(--text-primary)]">{m.label}</p>
                  <p className="text-xs text-[var(--text-muted)] mt-0.5">{m.desc}</p>
                </div>
              </button>
            ))}
          </div>
        </Section>

        <Section title="Движок агента" icon={<Cpu size={14} />}>
          <div className="flex flex-col gap-2">
            {ENGINES.map((e) => (
              <button
                key={e.id}
                onClick={() => updateEngine(e.id)}
                disabled={engineLoading}
                className={[
                  'flex items-center gap-3 px-3.5 py-3 rounded-lg border transition-all text-left',
                  selectedEngine === e.id
                    ? 'border-[var(--accent)] bg-[var(--accent)]/10'
                    : 'border-[var(--border)] bg-[var(--bg-hover)] hover:border-[var(--text-muted)]/30',
                ].join(' ')}
              >
                <span className="text-lg shrink-0">{e.icon}</span>
                <div className="min-w-0">
                  <p className="text-sm text-[var(--text-primary)]">{e.label}</p>
                  <p className="text-xs text-[var(--text-muted)] mt-0.5">{e.desc}</p>
                </div>
                {selectedEngine === e.id && (
                  <span className="ml-auto text-[var(--accent)] text-xs font-medium shrink-0">Активен</span>
                )}
              </button>
            ))}
          </div>
        </Section>

        {selectedEngine === 'opencode' && openCodeModels.length > 0 && (
          <Section title="Модель OpenCode" icon={<Zap size={14} />}>
            <div className="flex flex-col gap-2">
              {openCodeModels.map((m) => (
                <button
                  key={m.id}
                  onClick={() => updateOpenCodeModel(m.id)}
                  disabled={engineLoading}
                  className={[
                    'flex items-center gap-3 px-3.5 py-3 rounded-lg border transition-all text-left',
                    selectedOpenCodeModel === m.id
                      ? 'border-[var(--accent)] bg-[var(--accent)]/10'
                      : 'border-[var(--border)] bg-[var(--bg-hover)] hover:border-[var(--text-muted)]/30',
                  ].join(' ')}
                >
                  <span
                    className={[
                      'w-3.5 h-3.5 rounded-full border-2 shrink-0 transition-colors',
                      selectedOpenCodeModel === m.id
                        ? 'border-[var(--accent)] bg-[var(--accent)]'
                        : 'border-[var(--text-muted)]',
                    ].join(' ')}
                  />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-[var(--text-primary)]">{m.label}</p>
                    <p className="text-xs text-[var(--text-muted)] mt-0.5">{m.price}</p>
                  </div>
                  <span className={[
                    'text-[10px] px-1.5 py-0.5 rounded-full shrink-0',
                    m.tier === 'free' ? 'bg-green-500/10 text-green-500' :
                    m.tier === 'budget' ? 'bg-blue-500/10 text-blue-500' :
                    m.tier === 'standard' ? 'bg-yellow-500/10 text-yellow-500' :
                    'bg-purple-500/10 text-purple-500',
                  ].join(' ')}>
                    {m.tier}
                  </span>
                </button>
              ))}
            </div>
          </Section>
        )}

        {selectedEngine === 'yandex' && yandexModels.length > 0 && (
          <Section title="Модель YandexGPT" icon={<Zap size={14} />}>
            <div className="flex flex-col gap-2">
              {yandexModels.map((m) => (
                <button
                  key={m.id}
                  onClick={() => updateYandexModel(m.id)}
                  disabled={engineLoading}
                  className={[
                    'flex items-center gap-3 px-3.5 py-3 rounded-lg border transition-all text-left',
                    selectedYandexModel === m.id
                      ? 'border-[var(--accent)] bg-[var(--accent)]/10'
                      : 'border-[var(--border)] bg-[var(--bg-hover)] hover:border-[var(--text-muted)]/30',
                  ].join(' ')}
                >
                  <span
                    className={[
                      'w-3.5 h-3.5 rounded-full border-2 shrink-0 transition-colors',
                      selectedYandexModel === m.id
                        ? 'border-[var(--accent)] bg-[var(--accent)]'
                        : 'border-[var(--text-muted)]',
                    ].join(' ')}
                  />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-[var(--text-primary)]">{m.label}</p>
                    <p className="text-xs text-[var(--text-muted)] mt-0.5">{m.price}</p>
                  </div>
                  <span className={[
                    'text-[10px] px-1.5 py-0.5 rounded-full shrink-0',
                    m.tier === 'budget' ? 'bg-blue-500/10 text-blue-500' :
                    m.tier === 'standard' ? 'bg-yellow-500/10 text-yellow-500' :
                    'bg-purple-500/10 text-purple-500',
                  ].join(' ')}>
                    {m.tier}
                  </span>
                </button>
              ))}
            </div>
          </Section>
        )}

        <Section title="Горячие клавиши" icon={<Keyboard size={14} />}>
          <div className="flex flex-col gap-0">
            {SHORTCUTS.map((s, i) => (
              <div
                key={s.keys}
                className={`flex items-center justify-between py-2.5 px-1 ${
                  i < SHORTCUTS.length - 1 ? 'border-b border-[var(--border)]/50' : ''
                }`}
              >
                <span className="text-sm text-[var(--text-secondary)]">{s.action}</span>
                <kbd className="px-2 py-0.5 rounded-md bg-[var(--bg-hover)] border border-[var(--border)] text-xs text-[var(--text-muted)] font-mono whitespace-nowrap">
                  {s.keys}
                </kbd>
              </div>
            ))}
          </div>
        </Section>

        <Section title="О приложении" icon={<Info size={14} />}>
          <div className="flex flex-col gap-3">
            <InfoRow label="Версия" value="Neura v2.0.0" />
            <InfoRow label="Стек" value="React 19 + Tailwind v4" />
            <InfoRow label="Движок" value="Vite 8" />
          </div>
        </Section>

        <Section title="Аккаунт">
          <Button variant="danger" icon={<LogOut size={14} />} onClick={() => { if (window.confirm('Выйти из аккаунта?')) logout() }}>
            Выйти из аккаунта
          </Button>
        </Section>
      </motion.div>
    </div>
  )
}

function Section({
  title,
  icon,
  children,
}: {
  title: string
  icon?: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <div className="mb-6">
      <div className="flex items-center gap-2 mb-3">
        {icon && <span className="text-[var(--text-muted)]">{icon}</span>}
        <h2 className="text-sm font-semibold text-[var(--text-primary)]">{title}</h2>
      </div>
      <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded-xl p-5">
        {children}
      </div>
    </div>
  )
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs text-[var(--text-muted)]">{label}</span>
      <span className="text-sm text-[var(--text-secondary)]">{value}</span>
    </div>
  )
}

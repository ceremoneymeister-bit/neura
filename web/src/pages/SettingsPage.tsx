import { useState } from 'react'
import { motion } from 'framer-motion'
import { useAuth } from '@/hooks/useAuth'
import { Avatar } from '@/components/ui/Avatar'
import { Button } from '@/components/ui/Button'
import { LogOut, Keyboard, Info, Sparkles, User } from 'lucide-react'

const MODELS = [
  {
    id: 'claude-sonnet-4-6',
    label: 'Claude Sonnet 4.6',
    desc: 'Быстрый и умный — оптимальный баланс скорости и качества',
  },
  {
    id: 'claude-opus-4-6',
    label: 'Claude Opus 4.6',
    desc: 'Максимальный интеллект для сложных задач и анализа',
  },
  {
    id: 'claude-haiku-4-5',
    label: 'Claude Haiku 4.5',
    desc: 'Сверхбыстрый — мгновенные ответы на простые вопросы',
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

export function SettingsPage() {
  const { user, logout } = useAuth()
  const [selectedModel, setSelectedModel] = useState('claude-sonnet-4-6')

  return (
    <div className="h-full overflow-y-auto">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="max-w-2xl mx-auto px-4 py-8"
      >
        <h1 className="text-lg font-semibold text-[#f5f5f5] mb-8">Настройки</h1>

        {/* ── Profile ───────────────────────────────── */}
        <Section title="Профиль" icon={<User size={14} />}>
          <div className="flex items-center gap-4">
            <Avatar name={user?.name ?? ''} size="lg" />
            <div className="min-w-0">
              <p className="text-sm font-medium text-[#f5f5f5] truncate">
                {user?.name ?? 'Пользователь'}
              </p>
              <p className="text-xs text-[#525252] truncate">{user?.email}</p>
              {user?.capsule_id && (
                <p className="text-xs text-[#7c3aed] mt-0.5">
                  Capsule: {user.capsule_id}
                </p>
              )}
            </div>
          </div>
        </Section>

        {/* ── Model Preferences ─────────────────────── */}
        <Section title="Модель по умолчанию" icon={<Sparkles size={14} />}>
          <div className="flex flex-col gap-2">
            {MODELS.map((m) => (
              <button
                key={m.id}
                onClick={() => setSelectedModel(m.id)}
                className={[
                  'flex items-center gap-3 px-3.5 py-3 rounded-[10px] border transition-all text-left',
                  selectedModel === m.id
                    ? 'border-[#7c3aed] bg-[#7c3aed]/10'
                    : 'border-[#262626] bg-[#1a1a1a] hover:border-[#333]',
                ].join(' ')}
              >
                <span
                  className={[
                    'w-3.5 h-3.5 rounded-full border-2 shrink-0 transition-colors',
                    selectedModel === m.id
                      ? 'border-[#7c3aed] bg-[#7c3aed]'
                      : 'border-[#525252]',
                  ].join(' ')}
                />
                <div className="min-w-0">
                  <p className="text-sm text-[#f5f5f5]">{m.label}</p>
                  <p className="text-xs text-[#525252] mt-0.5">{m.desc}</p>
                </div>
              </button>
            ))}
          </div>
        </Section>

        {/* ── Keyboard Shortcuts ────────────────────── */}
        <Section
          title="Горячие клавиши"
          icon={<Keyboard size={14} />}
        >
          <div className="flex flex-col gap-0">
            {SHORTCUTS.map((s, i) => (
              <div
                key={s.keys}
                className={`flex items-center justify-between py-2.5 px-1 ${
                  i < SHORTCUTS.length - 1 ? 'border-b border-[#262626]/50' : ''
                }`}
              >
                <span className="text-sm text-[#a3a3a3]">{s.action}</span>
                <kbd className="px-2 py-0.5 rounded-[6px] bg-[#1a1a1a] border border-[#262626] text-xs text-[#525252] font-mono whitespace-nowrap">
                  {s.keys}
                </kbd>
              </div>
            ))}
          </div>
        </Section>

        {/* ── About ─────────────────────────────────── */}
        <Section title="О приложении" icon={<Info size={14} />}>
          <div className="flex flex-col gap-3">
            <InfoRow label="Версия" value="Neura v2.0.0" />
            <InfoRow label="Стек" value="React 19 + Tailwind v4" />
            <InfoRow label="Движок" value="Vite 8" />
          </div>
        </Section>

        {/* ── Logout ────────────────────────────────── */}
        <Section title="Аккаунт">
          <Button variant="danger" icon={<LogOut size={14} />} onClick={logout}>
            Выйти из аккаунта
          </Button>
        </Section>
      </motion.div>
    </div>
  )
}

/* ── Helpers ──────────────────────────────────────────────── */

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
        {icon && <span className="text-[#525252]">{icon}</span>}
        <h2 className="text-sm font-semibold text-[#f5f5f5]">{title}</h2>
      </div>
      <div className="bg-[#141414] border border-[#262626] rounded-[12px] p-5">
        {children}
      </div>
    </div>
  )
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs text-[#525252]">{label}</span>
      <span className="text-sm text-[#a3a3a3]">{value}</span>
    </div>
  )
}

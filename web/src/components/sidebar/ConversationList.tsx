import {
  type KeyboardEvent,
  useMemo,
  useRef,
  useState,
  useCallback,
} from 'react'
import {
  Check,
  Folder,
  MessageSquare,
  MoreHorizontal,
  Pencil,
  Pin,
  PinOff,
  Trash2,
  X,
} from 'lucide-react'
import {
  type Conversation,
  deleteConversation,
  updateConversation,
} from '@/api/conversations'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { type Project } from '@/api/projects'
import { useToast } from '@/components/ui/Toast'

interface ConversationListProps {
  conversations: Conversation[]
  projects: Project[]
  activeId?: string
  unreadIds?: Set<number>
  onNavigate: (id: number) => void
  onReload: () => void
}

interface CtxMenuState {
  conv: Conversation
  x: number
  y: number
}

type DateGroup = 'Сегодня' | 'Вчера' | 'Эта неделя' | 'Этот месяц' | 'Ранее'

const DATE_GROUP_ORDER: DateGroup[] = ['Сегодня', 'Вчера', 'Эта неделя', 'Этот месяц', 'Ранее']

function getDateGroup(dateStr: string | null): DateGroup {
  if (!dateStr) return 'Ранее'
  const now = new Date()
  const d = new Date(dateStr)
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const diffMs = todayStart.getTime() - new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime()
  const diffDays = diffMs / (1000 * 60 * 60 * 24)

  if (diffDays <= 0) return 'Сегодня'
  if (diffDays <= 1) return 'Вчера'
  if (diffDays <= 7) return 'Эта неделя'
  if (diffDays <= 30) return 'Этот месяц'
  return 'Ранее'
}

export function ConversationList({
  conversations,
  projects,
  activeId,
  unreadIds,
  onNavigate,
  onReload,
}: ConversationListProps) {
  const { error: showError } = useToast()
  const [ctxMenu, setCtxMenu] = useState<CtxMenuState | null>(null)
  const [showMoveSubmenu, setShowMoveSubmenu] = useState(false)
  const [deleteConv, setDeleteConv] = useState<Conversation | null>(null)
  const [renamingId, setRenamingId] = useState<number | null>(null)
  const [renameValue, setRenameValue] = useState('')
  const renameRef = useRef<HTMLInputElement>(null)

  const openCtx = useCallback((e: React.MouseEvent, conv: Conversation) => {
    e.preventDefault()
    e.stopPropagation()
    setCtxMenu({ conv, x: e.clientX, y: e.clientY })
    setShowMoveSubmenu(false)
  }, [])

  const closeCtx = useCallback(() => {
    setCtxMenu(null)
    setShowMoveSubmenu(false)
  }, [])

  const handlePin = async (conv: Conversation) => {
    closeCtx()
    try {
      await updateConversation(conv.id, { pinned: !conv.pinned })
      onReload()
    } catch (e) {
      console.error(e)
      showError('Не удалось обновить чат')
    }
  }

  const handleRenameStart = (conv: Conversation) => {
    closeCtx()
    setRenamingId(conv.id)
    setRenameValue(conv.title)
    setTimeout(() => renameRef.current?.focus(), 30)
  }

  const handleRenameCommit = async () => {
    const id = renamingId
    const name = renameValue.trim()
    setRenamingId(null)
    setRenameValue('')
    if (!id || !name) return
    try {
      await updateConversation(id, { title: name })
      onReload()
    } catch (e) {
      console.error(e)
      showError('Не удалось переименовать чат')
    }
  }

  const handleRenameKey = (e: KeyboardEvent) => {
    if (e.key === 'Enter') handleRenameCommit()
    if (e.key === 'Escape') { setRenamingId(null); setRenameValue('') }
  }

  const handleMove = async (conv: Conversation, projectId: number | null) => {
    closeCtx()
    try {
      await updateConversation(conv.id, { project_id: projectId })
      onReload()
    } catch (e) {
      console.error(e)
      showError('Не удалось переместить чат')
    }
  }

  const handleDelete = async (conv: Conversation) => {
    closeCtx()
    try {
      await deleteConversation(conv.id)
      onReload()
    } catch (e) {
      console.error(e)
      showError('Не удалось удалить чат')
    }
  }

  const renderConversation = (c: Conversation) => {
    const isActive = String(c.id) === activeId
    const isRenaming = renamingId === c.id
    const isUnread = !isActive && unreadIds?.has(c.id)

    return (
      <div
        key={c.id}
        data-conv-nav
        className={[
          'group relative flex items-center rounded-lg transition-colors',
          isActive
            ? 'bg-[var(--bg-hover)]'
            : 'hover:bg-[var(--bg-hover)]',
        ].join(' ')}
        onContextMenu={(e) => openCtx(e, c)}
      >
        {isRenaming ? (
          <div className="flex items-center gap-1 flex-1 px-2 py-1">
            <input
              ref={renameRef}
              value={renameValue}
              onChange={(e) => setRenameValue(e.target.value)}
              onKeyDown={handleRenameKey}
              onBlur={handleRenameCommit}
              className="flex-1 h-5 px-1.5 rounded bg-[var(--bg-input)] border border-[var(--accent)]/50 text-xs text-[var(--text-primary)] focus:outline-none"
            />
            <button
              onMouseDown={(e) => e.preventDefault()}
              onClick={handleRenameCommit}
              aria-label="Подтвердить"
              title="Подтвердить"
              className="text-emerald-400 hover:text-emerald-300 transition-colors"
            >
              <Check size={11} />
            </button>
            <button
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => { setRenamingId(null); setRenameValue('') }}
              aria-label="Отменить"
              title="Отменить"
              className="text-[var(--text-muted)] hover:text-red-400 transition-colors"
            >
              <X size={11} />
            </button>
          </div>
        ) : (
          <>
            <button
              onClick={() => onNavigate(c.id)}
              className="flex-1 flex items-center gap-1.5 text-left px-2.5 py-2 min-w-0"
            >
              {isUnread && (
                <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent)] shrink-0" />
              )}
              <p
                className={[
                  'text-sm truncate',
                  isActive
                    ? 'text-[var(--text-primary)]'
                    : isUnread
                      ? 'text-[var(--text-primary)] font-medium'
                      : 'text-[var(--text-secondary)] group-hover:text-[var(--text-primary)]',
                ].join(' ')}
              >
                {c.title}
              </p>
            </button>

            {/* "..." actions */}
            <button
              onClick={(e) => openCtx(e, c)}
              title="Действия"
              aria-label="Действия"
              className="mr-1.5 p-0.5 hover-hide text-[var(--text-muted)] hover:text-[var(--text-secondary)] flex-shrink-0"
            >
              <MoreHorizontal size={14} />
            </button>
          </>
        )}
      </div>
    )
  }

  const grouped = useMemo(() => {
    const groups = new Map<DateGroup, Conversation[]>()
    for (const c of conversations) {
      const g = getDateGroup(c.updated_at)
      const arr = groups.get(g)
      if (arr) arr.push(c)
      else groups.set(g, [c])
    }
    return DATE_GROUP_ORDER
      .filter((g) => groups.has(g))
      .map((g) => ({ label: g, items: groups.get(g)! }))
  }, [conversations])

  if (conversations.length === 0) {
    return (
      <div className="flex flex-col items-center py-6 text-center px-2.5">
        <MessageSquare size={24} className="text-[var(--text-muted)]/30 mb-2" />
        <p className="text-xs text-[var(--text-muted)]">Нет чатов</p>
      </div>
    )
  }

  return (
    <div className="space-y-0.5">
      {grouped.map(({ label, items }) => (
        <div key={label}>
          <div className="text-[11px] font-medium text-[var(--text-muted)] uppercase tracking-wider px-2.5 pt-3 pb-1.5">
            {label}
          </div>
          {items.map(renderConversation)}
        </div>
      ))}

      {/* Context menu */}
      {ctxMenu && (
        <>
          <div className="fixed inset-0 z-40" onClick={closeCtx} onKeyDown={(e) => e.key === 'Escape' && closeCtx()} tabIndex={-1} />
          <div
            className="fixed z-50 min-w-[168px] bg-[var(--bg-card)] border border-[var(--border)] rounded-lg shadow-2xl py-1 text-xs"
            style={{
              left: Math.min(ctxMenu.x, window.innerWidth - 190),
              top: Math.min(ctxMenu.y, window.innerHeight - 220),
            }}
          >
            <CtxItem
              icon={ctxMenu.conv.pinned ? <PinOff size={12} /> : <Pin size={12} />}
              label={ctxMenu.conv.pinned ? 'Открепить' : 'Закрепить'}
              onClick={() => handlePin(ctxMenu.conv)}
            />
            <CtxItem
              icon={<Pencil size={12} />}
              label="Переименовать"
              onClick={() => handleRenameStart(ctxMenu.conv)}
            />
            {projects.length > 0 && (
              <>
                <CtxItem
                  icon={<Folder size={12} />}
                  label={showMoveSubmenu ? 'Выбери проект \u25BE' : 'В проект \u2192'}
                  onClick={() => setShowMoveSubmenu((v) => !v)}
                />
                {showMoveSubmenu && (
                  <div className="border-t border-[var(--border)] mt-0.5 pt-0.5">
                    {ctxMenu.conv.project_id && (
                      <button
                        onClick={() => handleMove(ctxMenu.conv, null)}
                        className="w-full text-left px-3 py-1.5 text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)] transition-colors"
                      >
                        {'\u2715'} Убрать из проекта
                      </button>
                    )}
                    {projects.map((p) => (
                      <button
                        key={p.id}
                        onClick={() => handleMove(ctxMenu.conv, p.id)}
                        className="w-full text-left px-3 py-1.5 flex items-center gap-2 text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)] transition-colors"
                      >
                        <span>{p.icon}</span>
                        <span className="truncate">{p.name}</span>
                      </button>
                    ))}
                  </div>
                )}
              </>
            )}
            <div className="my-0.5 border-t border-[var(--border)]" />
            <CtxItem
              icon={<Trash2 size={12} />}
              label="Удалить"
              onClick={() => { setDeleteConv(ctxMenu.conv); closeCtx() }}
              danger
            />
          </div>
        </>
      )}
      <ConfirmDialog
        open={deleteConv !== null}
        onClose={() => setDeleteConv(null)}
        onConfirm={async () => {
          if (deleteConv) {
            await handleDelete(deleteConv)
            setDeleteConv(null)
          }
        }}
        title="Удалить чат"
        message={`Чат «${deleteConv?.title ?? ''}» будет удалён. Это действие нельзя отменить.`}
      />
    </div>
  )
}

function CtxItem({
  icon,
  label,
  onClick,
  danger = false,
}: {
  icon: React.ReactNode
  label: string
  onClick: () => void
  danger?: boolean
}) {
  return (
    <button
      onClick={onClick}
      className={[
        'w-full text-left px-3 py-1.5 flex items-center gap-2 transition-colors',
        danger
          ? 'text-red-400 hover:bg-red-500/10'
          : 'text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]',
      ].join(' ')}
    >
      {icon}
      {label}
    </button>
  )
}

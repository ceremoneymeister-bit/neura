import {
  type KeyboardEvent,
  useCallback,
  useEffect,
  useRef,
  useState,
} from 'react'
import { createPortal } from 'react-dom'
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

// Date grouping removed — flat list under "Недавние"

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

  // Close context menu on Escape or any scroll
  useEffect(() => {
    if (!ctxMenu) return
    const onKey = (e: Event) => { if ((e as globalThis.KeyboardEvent).key === 'Escape') closeCtx() }
    const onScroll = () => closeCtx()
    document.addEventListener('keydown', onKey)
    document.addEventListener('scroll', onScroll, true)
    return () => {
      document.removeEventListener('keydown', onKey)
      document.removeEventListener('scroll', onScroll, true)
    }
  }, [ctxMenu, closeCtx])

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
          'group relative flex items-center rounded-xl liquid-glass-nav',
          isActive ? 'active' : '',
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
              className="flex-1 h-5 px-1.5 rounded liquid-glass-input border-[var(--accent)]/50 text-xs text-[var(--text-primary)] focus:outline-none"
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
              className="flex-1 flex items-center gap-2 text-left px-3 py-2.5 min-w-0"
            >
              {isUnread && (
                <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent)] shrink-0" />
              )}
              <p
                className={[
                  'text-[14px] truncate',
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
      {conversations.map(renderConversation)}

      {/* Context menu — Portal to body (escapes sidebar overflow-hidden) */}
      {ctxMenu && createPortal(
        <>
          <div className="fixed inset-0 z-[80]" onClick={closeCtx} onContextMenu={(e) => { e.preventDefault(); closeCtx() }} tabIndex={-1} />
          <div
            className="fixed z-[90] min-w-[180px] rounded-xl py-1.5 text-xs liquid-glass-popup"
            style={{
              position: 'fixed',
              overflow: 'visible',
              left: Math.max(8, Math.min(ctxMenu.x, window.innerWidth - 190)),
              top: Math.max(8, Math.min(ctxMenu.y, window.innerHeight - 280)),
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
        </>,
        document.body,
      )}
      {/* ConfirmDialog — Modal already uses Portal internally */}
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

import {
  type KeyboardEvent,
  useRef,
  useState,
  useCallback,
  useMemo,
} from 'react'
import {
  Check,
  Folder,
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
import { type Project } from '@/api/projects'
import { formatRelativeTime } from '@/utils/time'

interface ConversationListProps {
  conversations: Conversation[]
  projects: Project[]
  activeId?: string
  onNavigate: (id: number) => void
  onReload: () => void
}

interface CtxMenuState {
  conv: Conversation
  x: number
  y: number
}

interface DateGroup {
  label: string
  items: Conversation[]
}

function groupByDate(conversations: Conversation[]): DateGroup[] {
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const yesterday = new Date(today.getTime() - 86400000)
  const weekAgo = new Date(today.getTime() - 7 * 86400000)

  const groups: Record<string, Conversation[]> = {
    '\u0421\u0435\u0433\u043E\u0434\u043D\u044F': [],
    '\u0412\u0447\u0435\u0440\u0430': [],
    '\u041F\u0440\u0435\u0434\u044B\u0434\u0443\u0449\u0438\u0435 7 \u0434\u043D\u0435\u0439': [],
    '\u0420\u0430\u043D\u0435\u0435': [],
  }

  for (const conv of conversations) {
    const date = new Date(conv.updated_at ?? conv.created_at ?? '')
    if (date >= today) groups['\u0421\u0435\u0433\u043E\u0434\u043D\u044F'].push(conv)
    else if (date >= yesterday) groups['\u0412\u0447\u0435\u0440\u0430'].push(conv)
    else if (date >= weekAgo) groups['\u041F\u0440\u0435\u0434\u044B\u0434\u0443\u0449\u0438\u0435 7 \u0434\u043D\u0435\u0439'].push(conv)
    else groups['\u0420\u0430\u043D\u0435\u0435'].push(conv)
  }

  return Object.entries(groups)
    .filter(([, items]) => items.length > 0)
    .map(([label, items]) => ({ label, items }))
}

export function ConversationList({
  conversations,
  projects,
  activeId,
  onNavigate,
  onReload,
}: ConversationListProps) {
  const [ctxMenu, setCtxMenu] = useState<CtxMenuState | null>(null)
  const [showMoveSubmenu, setShowMoveSubmenu] = useState(false)
  const [renamingId, setRenamingId] = useState<number | null>(null)
  const [renameValue, setRenameValue] = useState('')
  const renameRef = useRef<HTMLInputElement>(null)

  const groups = useMemo(() => groupByDate(conversations), [conversations])

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
    }
  }

  const handleDelete = async (conv: Conversation) => {
    closeCtx()
    try {
      await deleteConversation(conv.id)
      onReload()
    } catch (e) {
      console.error(e)
    }
  }

  const renderConversation = (c: Conversation) => {
    const isActive = String(c.id) === activeId
    const isRenaming = renamingId === c.id

    return (
      <div
        key={c.id}
        className={[
          'group relative flex items-center rounded-[6px] transition-colors',
          isActive
            ? 'bg-[#7c3aed]/15 border-l-2 border-[#7c3aed]'
            : 'hover:bg-[#1a1a1a]',
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
              className="flex-1 h-5 px-1.5 rounded bg-[#1a1a1a] border border-[#7c3aed]/50 text-xs text-[#f5f5f5] focus:outline-none"
            />
            <button
              onMouseDown={(e) => e.preventDefault()}
              onClick={handleRenameCommit}
              className="text-emerald-400 hover:text-emerald-300 transition-colors"
            >
              <Check size={11} />
            </button>
            <button
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => { setRenamingId(null); setRenameValue('') }}
              className="text-[#525252] hover:text-red-400 transition-colors"
            >
              <X size={11} />
            </button>
          </div>
        ) : (
          <>
            <button
              onClick={() => onNavigate(c.id)}
              className="flex-1 text-left px-2 py-1.5 min-w-0"
            >
              <p
                className={[
                  'text-xs truncate',
                  isActive
                    ? 'text-[#f5f5f5] font-medium'
                    : 'text-[#a3a3a3] group-hover:text-[#f5f5f5]',
                ].join(' ')}
              >
                {c.title}
              </p>
              <div className="flex items-center gap-1.5 mt-0.5">
                {c.last_message && (
                  <p className="text-[10px] text-[#525252] truncate flex-1">
                    {c.last_message}
                  </p>
                )}
                {c.updated_at && (
                  <span className="text-[10px] text-[#525252] flex-shrink-0">
                    {formatRelativeTime(c.updated_at)}
                  </span>
                )}
              </div>
            </button>

            {/* Actions button */}
            <button
              onClick={(e) => openCtx(e, c)}
              title="Действия"
              className="mr-1 p-0.5 opacity-0 group-hover:opacity-100 text-[#525252] hover:text-[#a3a3a3] transition-all flex-shrink-0"
            >
              <MoreHorizontal size={13} />
            </button>
          </>
        )}
      </div>
    )
  }

  return (
    <div className="mt-2">
      {conversations.length === 0 ? (
        <p className="text-[10px] text-[#525252] px-2 py-2 text-center">Нет чатов</p>
      ) : (
        groups.map((group) => (
          <div key={group.label}>
            <p className="px-2 py-1.5 text-[10px] font-medium text-[#525252] uppercase tracking-wider">
              {group.label}
            </p>
            {group.items.map(renderConversation)}
          </div>
        ))
      )}

      {/* Context menu */}
      {ctxMenu && (
        <>
          {/* Backdrop */}
          <div className="fixed inset-0 z-40" onClick={closeCtx} />

          {/* Menu */}
          <div
            className="fixed z-50 min-w-[168px] bg-[#1e1e1e] border border-[#2a2a2a] rounded-[8px] shadow-2xl py-1 text-xs"
            style={{
              left: Math.min(ctxMenu.x, window.innerWidth - 190),
              top: Math.min(ctxMenu.y, window.innerHeight - 220),
            }}
          >
            {/* Pin / Unpin */}
            <CtxItem
              icon={ctxMenu.conv.pinned ? <PinOff size={12} /> : <Pin size={12} />}
              label={ctxMenu.conv.pinned ? 'Открепить' : 'Закрепить'}
              onClick={() => handlePin(ctxMenu.conv)}
            />

            {/* Rename */}
            <CtxItem
              icon={<Pencil size={12} />}
              label="Переименовать"
              onClick={() => handleRenameStart(ctxMenu.conv)}
            />

            {/* Move to project */}
            {projects.length > 0 && (
              <>
                <CtxItem
                  icon={<Folder size={12} />}
                  label={showMoveSubmenu ? 'Выбери проект \u25BE' : 'В проект \u2192'}
                  onClick={() => setShowMoveSubmenu((v) => !v)}
                />
                {showMoveSubmenu && (
                  <div className="border-t border-[#2a2a2a] mt-0.5 pt-0.5">
                    {ctxMenu.conv.project_id && (
                      <button
                        onClick={() => handleMove(ctxMenu.conv, null)}
                        className="w-full text-left px-3 py-1.5 text-[#a3a3a3] hover:bg-[#262626] hover:text-[#f5f5f5] transition-colors"
                      >
                        {'\u2715'} Убрать из проекта
                      </button>
                    )}
                    {projects.map((p) => (
                      <button
                        key={p.id}
                        onClick={() => handleMove(ctxMenu.conv, p.id)}
                        className="w-full text-left px-3 py-1.5 flex items-center gap-2 text-[#a3a3a3] hover:bg-[#262626] hover:text-[#f5f5f5] transition-colors"
                      >
                        <span>{p.icon}</span>
                        <span className="truncate">{p.name}</span>
                      </button>
                    ))}
                  </div>
                )}
              </>
            )}

            <div className="my-0.5 border-t border-[#2a2a2a]" />

            {/* Delete */}
            <CtxItem
              icon={<Trash2 size={12} />}
              label="Удалить"
              onClick={() => handleDelete(ctxMenu.conv)}
              danger
            />
          </div>
        </>
      )}
    </div>
  )
}

// -- Context menu item ---------------------------------------------------

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
          : 'text-[#a3a3a3] hover:bg-[#262626] hover:text-[#f5f5f5]',
      ].join(' ')}
    >
      {icon}
      {label}
    </button>
  )
}

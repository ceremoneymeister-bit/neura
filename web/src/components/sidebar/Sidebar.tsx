import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  Plus,
  Search,
  PanelLeft,
  Settings,
  Sun,
  Moon,
  FolderOpen,
  ChevronDown,
  ChevronRight,
} from 'lucide-react'
import { type Conversation, listConversations } from '@/api/conversations'
import { type Project, listProjects } from '@/api/projects'
import { useAuth } from '@/hooks/useAuth'
import { Avatar } from '@/components/ui/Avatar'
import { Spinner } from '@/components/ui/Spinner'
import { useTheme } from '@/hooks/useTheme'
import { useBrandTheme } from '@/hooks/useBrandTheme'
import { SearchBar } from './SearchBar'
import { PinnedSection } from './PinnedSection'
import { ConversationList } from './ConversationList'
import { useToast } from '@/components/ui/Toast'

interface SidebarProps {
  onClose?: () => void
}

function closeMobileOnly(onClose?: () => void) {
  if (window.innerWidth < 768) onClose?.()
}

export function Sidebar({ onClose }: SidebarProps) {
  const navigate = useNavigate()
  const { error: showError } = useToast()
  const { id: activeId } = useParams<{ id: string }>()
  const { brandName } = useBrandTheme()

  const [conversations, setConversations] = useState<Conversation[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [search, setSearch] = useState('')
  const [showSearch, setShowSearch] = useState(false)
  const [showProjects, setShowProjects] = useState(false)
  const [loading, setLoading] = useState(true)

  // ── Data loading ──────────────────────────────────────────────

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const loadAll = useCallback(async () => {
    try {
      const [convs, projs] = await Promise.all([listConversations(), listProjects()])
      setConversations(convs)
      setProjects(projs)
    } catch (e) {
      console.error(e)
      showError('Не удалось загрузить данные')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadAll()
  }, [loadAll])

  // ── Unread tracking ───────────────────────────────────────────

  // Track when each conversation was last viewed (by updated_at at view time)
  const lastSeenRef = useRef<Record<number, string>>({})

  // Mark current conversation as seen whenever activeId or conversations change
  useEffect(() => {
    if (!activeId) return
    const conv = conversations.find((c) => String(c.id) === activeId)
    if (conv?.updated_at) {
      lastSeenRef.current[conv.id] = conv.updated_at
    }
  }, [activeId, conversations])

  // Set of conversation IDs that have unread messages
  const unreadIds = useMemo(() => {
    const ids = new Set<number>()
    for (const c of conversations) {
      if (String(c.id) === activeId) continue
      const seen = lastSeenRef.current[c.id]
      if (!seen && c.updated_at) {
        // Never seen — not unread (was there before session started)
        lastSeenRef.current[c.id] = c.updated_at
        continue
      }
      if (c.updated_at && seen && c.updated_at > seen) {
        ids.add(c.id)
      }
    }
    return ids
  }, [conversations, activeId])

  // Poll for updates every 15 seconds
  useEffect(() => {
    const timer = setInterval(loadAll, 15_000)
    return () => clearInterval(timer)
  }, [loadAll])

  // ── New chat ──────────────────────────────────────────────────

  const handleNewChat = useCallback(() => {
    navigate('/chat')
    closeMobileOnly(onClose)
  }, [navigate, onClose])

  useEffect(() => {
    const handler = () => handleNewChat()
    document.addEventListener('neura:new-chat', handler)
    return () => document.removeEventListener('neura:new-chat', handler)
  }, [handleNewChat])

  // ── Filtered & derived data ───────────────────────────────────

  const q = search.toLowerCase().trim()

  const filteredConvs = useMemo(
    () =>
      q
        ? conversations.filter(
            (c) =>
              c.title.toLowerCase().includes(q) ||
              (c.last_message?.toLowerCase().includes(q) ?? false),
          )
        : conversations,
    [conversations, q],
  )

  const pinnedConvs = useMemo(
    () => filteredConvs.filter((c) => c.pinned),
    [filteredConvs],
  )
  const pinnedProjects = useMemo(
    () => projects.filter((p) => p.pinned),
    [projects],
  )
  // Recent = not pinned, not in any project
  const recentConvs = useMemo(
    () => filteredConvs.filter((c) => !c.pinned && c.project_id === null),
    [filteredConvs],
  )

  // ── Keyboard navigation ───────────────────────────────────────

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        const items = document.querySelectorAll<HTMLElement>('[data-conv-nav]')
        if (!items.length) return
        const current = document.activeElement
        const idx = Array.from(items).indexOf(current as HTMLElement)
        if (e.key === 'ArrowDown') {
          const next = items[idx + 1] ?? items[0]
          next?.focus()
          e.preventDefault()
        } else {
          const prev = items[idx - 1] ?? items[items.length - 1]
          prev?.focus()
          e.preventDefault()
        }
      }
      if (e.key === 'Escape') onClose?.()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [onClose])

  useEffect(() => {
    const handler = () => setShowSearch(true)
    document.addEventListener('neura:search-focus', handler)
    return () => document.removeEventListener('neura:search-focus', handler)
  }, [])

  // Reload sidebar on external events (project creation, etc.)
  useEffect(() => {
    const handler = () => loadAll()
    document.addEventListener('neura:reload-sidebar', handler)
    return () => document.removeEventListener('neura:reload-sidebar', handler)
  }, [loadAll])

  const handleNavigate = useCallback((id: number) => {
    navigate(`/chat/${id}`)
    closeMobileOnly(onClose)
  }, [navigate, onClose])

  const handleProjectNavigate = useCallback((projectId: number) => {
    navigate(`/projects/${projectId}`)
    closeMobileOnly(onClose)
  }, [navigate, onClose])

  // ── Render ────────────────────────────────────────────────────

  return (
    <div className="flex flex-col h-full bg-[var(--bg-sidebar)] select-none">
      {/* ── Header ──────────────────────────────────────────── */}
      <div className="px-3 py-3 flex items-center justify-between">
        <span className="text-base font-semibold text-[var(--text-primary)] tracking-tight">
          {brandName}
        </span>
        <button
          onClick={onClose}
          aria-label="Скрыть панель"
          title="Скрыть панель"
          className="p-1 rounded-md text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
        >
          <PanelLeft size={16} />
        </button>
      </div>

      {/* ── Nav items ───────────────────────────────────────── */}
      <nav className="px-3 pb-2 space-y-0.5">
        <NavItem
          icon={<Plus size={18} strokeWidth={1.5} />}
          label="Новый чат"
          onClick={handleNewChat}
        />
        <NavItem
          icon={<Search size={18} strokeWidth={1.5} />}
          label="Поиск"
          onClick={() => setShowSearch((v) => !v)}
        />

        {/* Projects — split button: label → page, arrow → dropdown */}
        <div className="flex items-center rounded-lg hover:bg-[var(--bg-hover)] transition-colors">
          <button
            onClick={() => { navigate('/projects'); closeMobileOnly(onClose) }}
            className="flex-1 flex items-center gap-3 px-3 py-2 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
          >
            <FolderOpen size={18} strokeWidth={1.5} />
            <span>Проекты</span>
          </button>
          <button
            onClick={() => setShowProjects((v) => !v)}
            className="px-2 py-2 text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
            title="Список проектов"
            aria-label="Список проектов"
          >
            {showProjects ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </button>
        </div>

        {/* Projects dropdown list */}
        {showProjects && (
          <div className="ml-4 pl-3 border-l border-[var(--border)]/40 space-y-0.5 py-1">
            {projects.map((p) => {
              const hasUnread = conversations.some(
                (c) => c.project_id === p.id && unreadIds.has(c.id),
              )
              return (
                <button
                  key={p.id}
                  onClick={() => handleProjectNavigate(p.id)}
                  className="w-full flex items-center gap-2 px-2 py-1.5 text-xs text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)] rounded-md transition-colors truncate"
                >
                  {hasUnread && (
                    <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent)] shrink-0 animate-pulse" />
                  )}
                  <span className="truncate">{p.name}</span>
                  {p.chats_count > 0 && (
                    <span className="text-[10px] text-[var(--text-muted)] ml-auto shrink-0">{p.chats_count}</span>
                  )}
                </button>
              )
            })}
            {projects.length === 0 && (
              <p className="text-[10px] text-[var(--text-muted)] px-2 py-1">Нет проектов</p>
            )}
          </div>
        )}
      </nav>

      {/* ── Inline search ───────────────────────────────────── */}
      {showSearch && (
        <div className="px-3 pb-2">
          <SearchBar value={search} onChange={setSearch} />
        </div>
      )}

      {/* ── Scrollable list area ─────────────────────────────── */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden px-1.5 pb-2">
        {loading ? (
          <div className="flex justify-center py-10">
            <Spinner size="sm" />
          </div>
        ) : (
          <>
            {/* Pinned items */}
            {(pinnedConvs.length > 0 || pinnedProjects.length > 0) && (
              <PinnedSection
                conversations={pinnedConvs}
                projects={pinnedProjects}
                activeId={activeId}
                unreadIds={unreadIds}
                onNavigate={handleNavigate}
                onProjectNavigate={handleProjectNavigate}
                onReload={loadAll}
              />
            )}

            {/* Recent conversations (no project, not pinned) */}
            <div id="recents-section">
              <p className="px-2.5 pt-3 pb-1.5 text-[11px] font-medium text-[var(--text-muted)] uppercase tracking-wider">
                Недавние
              </p>
              <ConversationList
                conversations={recentConvs}
                projects={projects}
                activeId={activeId}
                unreadIds={unreadIds}
                onNavigate={handleNavigate}
                onReload={loadAll}
              />
            </div>

            {q && filteredConvs.length === 0 && (
              <p className="text-center text-xs text-[var(--text-muted)] py-8">
                Ничего не найдено
              </p>
            )}
          </>
        )}
      </div>

      {/* ── Footer ──────────────────────────────────────────── */}
      <FooterBar onClose={onClose} />
    </div>
  )
}

function FooterBar({ onClose }: { onClose?: () => void }) {
  const { user } = useAuth()
  const navigate = useNavigate()
  const { theme, toggle } = useTheme()

  return (
    <div className="border-t border-[var(--border)]/40 px-3 py-2.5 flex items-center gap-2">
      <Avatar name={user?.name ?? ''} size="sm" />
      <div className="flex-1 min-w-0">
        <p className="text-sm text-[var(--text-primary)] truncate leading-tight">
          {user?.name ?? user?.email}
        </p>
        <p className="text-[10px] text-[var(--text-muted)] leading-tight">Pro</p>
      </div>
      <button
        onClick={toggle}
        title={theme === 'dark' ? 'Светлая тема' : 'Тёмная тема'}
        aria-label={theme === 'dark' ? 'Светлая тема' : 'Тёмная тема'}
        className="p-1 text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
      >
        {theme === 'dark' ? <Sun size={14} /> : <Moon size={14} />}
      </button>
      <button
        onClick={() => { navigate('/settings'); closeMobileOnly(onClose) }}
        title="Настройки"
        aria-label="Настройки"
        className="p-1 text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
      >
        <Settings size={14} />
      </button>
    </div>
  )
}

function NavItem({
  icon,
  label,
  onClick,
  loading = false,
}: {
  icon: React.ReactNode
  label: string
  onClick: () => void
  loading?: boolean
}) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className="w-full flex items-center gap-3 px-3 py-2 text-sm text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)] rounded-lg transition-colors disabled:opacity-50"
    >
      {loading ? <Spinner size="sm" /> : icon}
      <span>{label}</span>
    </button>
  )
}

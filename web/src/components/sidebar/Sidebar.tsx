import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { LogOut, Settings } from 'lucide-react'
import { type Conversation, createConversation, listConversations } from '@/api/conversations'
import { type Project, listProjects } from '@/api/projects'
import { useAuth } from '@/hooks/useAuth'
import { Avatar } from '@/components/ui/Avatar'
import { Spinner } from '@/components/ui/Spinner'
import { NewChatButton } from './NewChatButton'
import { SearchBar } from './SearchBar'
import { PinnedSection } from './PinnedSection'
import { ProjectList } from './ProjectList'
import { ConversationList } from './ConversationList'
import { AgentPanel } from './AgentPanel'

interface SidebarProps {
  onClose?: () => void
}

export function Sidebar({ onClose }: SidebarProps) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const { id: activeId } = useParams<{ id: string }>()

  const [conversations, setConversations] = useState<Conversation[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)

  // ── Data loading ──────────────────────────────────────────────

  const loadAll = useCallback(async () => {
    try {
      const [convs, projs] = await Promise.all([listConversations(), listProjects()])
      setConversations(convs)
      setProjects(projs)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadAll()
  }, [loadAll])

  // ── New chat ──────────────────────────────────────────────────

  const handleNewChat = useCallback(async () => {
    if (creating) return
    setCreating(true)
    try {
      const conv = await createConversation()
      setConversations((prev) => [conv, ...prev])
      navigate(`/chat/${conv.id}`)
      onClose?.()
    } catch (e) {
      console.error(e)
    } finally {
      setCreating(false)
    }
  }, [creating, navigate, onClose])

  // ── Filtered data ─────────────────────────────────────────────

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

  const filteredProjects = useMemo(
    () =>
      q
        ? projects.filter((p) => p.name.toLowerCase().includes(q))
        : projects,
    [projects, q],
  )

  // Derived views
  const pinnedConvs = filteredConvs.filter((c) => c.pinned)
  const pinnedProjects = filteredProjects.filter((p) => p.pinned)
  const unpinnedProjects = filteredProjects.filter((p) => !p.pinned)
  const recentConvs = filteredConvs.filter((c) => !c.pinned && c.project_id === null)

  // ── Keyboard navigation ───────────────────────────────────────

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // ↑ / ↓ on conversations
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
      // Escape — close sidebar on mobile
      if (e.key === 'Escape') onClose?.()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [onClose])

  // ── Render ────────────────────────────────────────────────────

  return (
    <div className="flex flex-col h-full bg-[#141414] select-none">
      {/* ── Header: new chat + close ────────────────────────────── */}
      <div className="px-3 py-2.5 border-b border-[#1a1a1a] flex items-center gap-2">
        <div className="flex-1">
          <NewChatButton onClick={handleNewChat} loading={creating} />
        </div>
        {/* Mobile close */}
        <button
          onClick={onClose}
          className="md:hidden p-1.5 rounded-[6px] text-[#525252] hover:text-[#f5f5f5] hover:bg-[#1a1a1a] transition-colors"
        >
          ✕
        </button>
      </div>

      {/* ── Search ─────────────────────────────────────────────── */}
      <div className="px-3 py-2">
        <SearchBar value={search} onChange={setSearch} />
      </div>

      {/* ── Scrollable list area ───────────────────────────────── */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden px-1.5 pb-2 space-y-0.5">
        {loading ? (
          <div className="flex justify-center py-10">
            <Spinner size="sm" />
          </div>
        ) : (
          <>
            {/* Pinned section */}
            <PinnedSection
              conversations={pinnedConvs}
              projects={pinnedProjects}
              activeId={activeId}
              onNavigate={(id) => { navigate(`/chat/${id}`); onClose?.() }}
              onReload={loadAll}
            />

            {/* Projects */}
            <ProjectList
              projects={unpinnedProjects}
              conversations={conversations}
              activeId={activeId}
              onNavigate={(id) => { navigate(`/chat/${id}`); onClose?.() }}
              onReload={loadAll}
            />

            {/* Recent (no project, unpinned) */}
            <ConversationList
              conversations={recentConvs}
              projects={projects}
              activeId={activeId}
              onNavigate={(id) => { navigate(`/chat/${id}`); onClose?.() }}
              onReload={loadAll}
            />

            {/* No results */}
            {q &&
              filteredConvs.length === 0 &&
              filteredProjects.length === 0 && (
                <p className="text-center text-xs text-[#525252] py-8">
                  Ничего не найдено
                </p>
              )}
          </>
        )}
      </div>

      {/* ── Agent panel ───────────────────────────────────────── */}
      <AgentPanel />

      {/* ── Footer: user + settings + logout ─────────────────── */}
      <div className="border-t border-[#1a1a1a] px-2 py-2 flex items-center gap-1">
        <div className="flex items-center gap-2 flex-1 min-w-0 px-1">
          <Avatar name={user?.name ?? ''} size="sm" />
          <span className="text-xs text-[#a3a3a3] truncate">
            {user?.name ?? user?.email}
          </span>
        </div>

        <button
          onClick={() => { navigate('/settings'); onClose?.() }}
          title="Настройки"
          className="p-1.5 rounded-[6px] text-[#525252] hover:text-[#f5f5f5] hover:bg-[#1a1a1a] transition-colors"
        >
          <Settings size={14} />
        </button>

        <button
          onClick={logout}
          title="Выйти"
          className="p-1.5 rounded-[6px] text-[#525252] hover:text-red-400 hover:bg-[#1a1a1a] transition-colors"
        >
          <LogOut size={14} />
        </button>
      </div>
    </div>
  )
}

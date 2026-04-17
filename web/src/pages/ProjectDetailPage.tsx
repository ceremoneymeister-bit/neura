import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  ArrowLeft,
  Plus,
  Pencil,
  MessageSquare,
  Search,
  BookOpen,
  Check,
  X,
  Link2,
  Users,
  Trash2,
  ExternalLink,
  Zap,
} from 'lucide-react'
import { ProjectIcon } from '@/components/ui/NeuraIcon'
import {
  type Project,
  type AutoContext,
  type ProjectMember,
  type ProjectLink,
  getProject,
  updateProject,
  getAutoContext,
  listProjectMembers,
  addProjectMember,
  removeProjectMember,
} from '@/api/projects'
import { type Conversation, createConversation } from '@/api/conversations'
import { listProjectConversations } from '@/api/projects'
import { Button } from '@/components/ui/Button'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { Spinner } from '@/components/ui/Spinner'
import { formatRelativeTime } from '@/utils/time'
import { useToast } from '@/components/ui/Toast'

export function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { error: showError } = useToast()
  const projectId = parseInt(id ?? '', 10)

  const [project, setProject] = useState<Project | null>(null)
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [autoContext, setAutoContext] = useState<AutoContext | null>(null)
  const [members, setMembers] = useState<ProjectMember[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [creatingChat, setCreatingChat] = useState(false)

  // Inline editing
  const [editingName, setEditingName] = useState(false)
  const [editingDesc, setEditingDesc] = useState(false)
  const [nameValue, setNameValue] = useState('')
  const [descValue, setDescValue] = useState('')
  const nameRef = useRef<HTMLInputElement>(null)
  const descRef = useRef<HTMLTextAreaElement>(null)

  // Context (instructions)
  const [contextValue, setContextValue] = useState('')
  const [contextSaving, setContextSaving] = useState(false)
  const [contextSaved, setContextSaved] = useState(false)
  const contextTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Links
  const [showAddLink, setShowAddLink] = useState(false)
  const [newLinkUrl, setNewLinkUrl] = useState('')
  const [newLinkTitle, setNewLinkTitle] = useState('')

  // Members
  const [showAddMember, setShowAddMember] = useState(false)
  const [newCapsuleId, setNewCapsuleId] = useState('')
  const [removeMemberId, setRemoveMemberId] = useState<number | null>(null)

  const load = useCallback(async () => {
    if (isNaN(projectId)) return
    try {
      const [proj, convs, ctx, mems] = await Promise.all([
        getProject(projectId),
        listProjectConversations(projectId),
        getAutoContext(projectId).catch(() => null),
        listProjectMembers(projectId).catch(() => []),
      ])
      setProject(proj)
      setConversations(convs)
      setAutoContext(ctx)
      setMembers(mems)
      setContextValue(proj.instructions || '')
    } catch (e) {
      console.error(e)
      showError('Не удалось загрузить проект')
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => { load() }, [load])

  const filtered = useMemo(() => {
    const q = search.toLowerCase().trim()
    if (!q) return conversations
    return conversations.filter(
      (c) =>
        c.title.toLowerCase().includes(q) ||
        (c.last_message?.toLowerCase().includes(q) ?? false),
    )
  }, [conversations, search])

  // ── Inline name edit ──────────────────────────────────────
  const startEditName = () => {
    if (!project) return
    setNameValue(project.name)
    setEditingName(true)
    setTimeout(() => nameRef.current?.select(), 0)
  }

  const saveName = async () => {
    if (!project) return
    const trimmed = nameValue.trim()
    if (trimmed && trimmed !== project.name) {
      const updated = await updateProject(project.id, { name: trimmed })
      setProject(updated)
    }
    setEditingName(false)
  }

  // ── Inline description edit ───────────────────────────────
  const startEditDesc = () => {
    if (!project) return
    setDescValue(project.description || '')
    setEditingDesc(true)
    setTimeout(() => descRef.current?.focus(), 0)
  }

  const saveDesc = async () => {
    if (!project) return
    const trimmed = descValue.trim()
    if (trimmed !== (project.description || '')) {
      const updated = await updateProject(project.id, { description: trimmed })
      setProject(updated)
    }
    setEditingDesc(false)
  }

  // ── Context auto-save ─────────────────────────────────────
  const handleContextChange = (value: string) => {
    setContextValue(value)
    setContextSaved(false)
    if (contextTimerRef.current) clearTimeout(contextTimerRef.current)
    contextTimerRef.current = setTimeout(() => saveContext(value), 1000)
  }

  const saveContext = async (value: string) => {
    if (!project) return
    setContextSaving(true)
    try {
      await updateProject(project.id, { instructions: value })
      setContextSaved(true)
      setTimeout(() => setContextSaved(false), 2000)
    } catch (e) {
      console.error(e)
      showError('Не удалось сохранить контекст')
    } finally {
      setContextSaving(false)
    }
  }

  useEffect(() => () => {
    if (contextTimerRef.current) clearTimeout(contextTimerRef.current)
  }, [])

  // ── Links ─────────────────────────────────────────────────
  const handleAddLink = async () => {
    if (!project || !newLinkUrl.trim()) return
    const link: ProjectLink = { url: newLinkUrl.trim(), title: newLinkTitle.trim() || undefined }
    const updatedLinks = [...(project.links || []), link]
    const updated = await updateProject(project.id, { links: updatedLinks })
    setProject(updated)
    setNewLinkUrl('')
    setNewLinkTitle('')
    setShowAddLink(false)
  }

  const handleRemoveLink = async (index: number) => {
    if (!project) return
    const updatedLinks = project.links.filter((_, i) => i !== index)
    const updated = await updateProject(project.id, { links: updatedLinks })
    setProject(updated)
  }

  // ── Members ───────────────────────────────────────────────
  const handleAddMember = async () => {
    if (!newCapsuleId.trim()) return
    try {
      const member = await addProjectMember(projectId, newCapsuleId.trim())
      setMembers((prev) => [...prev, member])
      setNewCapsuleId('')
      setShowAddMember(false)
    } catch (e) {
      console.error(e)
      showError('Не удалось добавить участника')
    }
  }

  const handleRemoveMember = async (memberId: number) => {
    try {
      await removeProjectMember(projectId, memberId)
      setMembers((prev) => prev.filter((m) => m.id !== memberId))
    } catch (e) {
      console.error(e)
      showError('Не удалось удалить участника')
    }
  }

  // ── New chat ──────────────────────────────────────────────
  const handleNewChat = async () => {
    if (creatingChat) return
    setCreatingChat(true)
    try {
      const conv = await createConversation(undefined, projectId)
      navigate(`/chat/${conv.id}`)
    } catch (e) {
      console.error(e)
      showError('Не удалось создать чат')
    } finally {
      setCreatingChat(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Spinner size="lg" />
      </div>
    )
  }

  if (!project) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3">
        <p className="text-sm text-[var(--text-muted)]">Проект не найден</p>
        <Button size="sm" variant="ghost" onClick={() => navigate('/projects')}>
          Назад к проектам
        </Button>
      </div>
    )
  }

  // Merge manual links + auto-detected links
  const manualLinks = project.links || []
  const autoLinks = autoContext?.auto_links || []
  const manualUrls = new Set(manualLinks.map((l) => l.url))
  const uniqueAutoLinks = autoLinks.filter((l) => !manualUrls.has(l.url))

  return (
    <div className="h-full overflow-y-auto">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="max-w-4xl mx-auto px-4 py-8"
      >
        {/* Back */}
        <button
          onClick={() => navigate('/projects')}
          aria-label="Назад к проектам"
          className="flex items-center gap-1.5 text-sm text-[var(--text-muted)] hover:text-[var(--text-secondary)] transition-colors mb-6"
        >
          <ArrowLeft size={14} />
          Проекты
        </button>

        {/* ── Project Header (compact) ───────────────────────── */}
        <div className="flex items-start gap-4 mb-6">
          <ProjectIcon size={40} />
          <div className="flex-1 min-w-0">
            {editingName ? (
              <div className="flex items-center gap-2">
                <input
                  ref={nameRef}
                  value={nameValue}
                  onChange={(e) => setNameValue(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') saveName()
                    if (e.key === 'Escape') setEditingName(false)
                  }}
                  className="text-xl font-semibold text-[var(--text-primary)] bg-transparent border-b-2 border-[var(--accent)] outline-none w-full"
                />
                <button onClick={saveName} aria-label="Сохранить" title="Сохранить" className="p-1 text-green-500 hover:text-green-400"><Check size={16} /></button>
                <button onClick={() => setEditingName(false)} aria-label="Отмена" title="Отмена" className="p-1 text-[var(--text-muted)] hover:text-[var(--text-secondary)]"><X size={16} /></button>
              </div>
            ) : (
              <div className="flex items-center gap-2 group">
                <h1 className="text-xl font-semibold text-[var(--text-primary)] truncate cursor-pointer" onClick={startEditName}>
                  {project.name}
                </h1>
                <button onClick={startEditName} aria-label="Редактировать название" title="Редактировать название" className="p-1 text-[var(--text-muted)] opacity-0 group-hover:opacity-100 hover:text-[var(--text-secondary)] transition-all rounded">
                  <Pencil size={14} />
                </button>
              </div>
            )}

            {editingDesc ? (
              <div className="mt-2">
                <textarea
                  ref={descRef}
                  value={descValue}
                  onChange={(e) => setDescValue(e.target.value)}
                  placeholder="Описание проекта..."
                  rows={2}
                  className="w-full text-sm text-[var(--text-secondary)] bg-transparent border border-[var(--accent)]/50 rounded-md px-3 py-2 resize-none outline-none focus:border-[var(--accent)]"
                  onKeyDown={(e) => { if (e.key === 'Escape') setEditingDesc(false) }}
                />
                <div className="flex justify-end gap-2 mt-1.5">
                  <button onClick={() => setEditingDesc(false)} className="text-xs text-[var(--text-muted)] hover:text-[var(--text-secondary)]">Отмена</button>
                  <button onClick={saveDesc} className="text-xs text-[var(--accent)] hover:text-[var(--accent-hover)]">Сохранить</button>
                </div>
              </div>
            ) : (
              <div className="mt-1">
                {project.description ? (
                  <p className="text-sm text-[var(--text-secondary)] cursor-pointer hover:text-[var(--text-primary)] transition-colors" onClick={startEditDesc}>
                    {project.description}
                  </p>
                ) : (
                  <button onClick={startEditDesc} className="text-sm text-[var(--text-muted)] hover:text-[var(--text-secondary)] transition-colors">
                    + Добавить описание
                  </button>
                )}
              </div>
            )}

            <div className="flex items-center gap-3 text-xs text-[var(--text-muted)] mt-2">
              <span>{project.chats_count} {pluralChats(project.chats_count)}</span>
              {autoContext && <span>{autoContext.total_messages} сообщений</span>}
              {members.length > 0 && <span>{members.length} участников</span>}
              {project.created_at && (
                <span>создан {formatRelativeTime(project.created_at)}</span>
              )}
            </div>
          </div>
        </div>

        {/* ═══════ CHATS — HERO BLOCK (primary, top) ═══════════ */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2.5">
              <div className="w-1.5 h-5 rounded-full bg-[var(--accent)]" />
              <h2 className="text-base font-semibold text-[var(--text-primary)]">
                Чаты{conversations.length > 0 ? ` (${conversations.length})` : ''}
              </h2>
            </div>
            <Button size="sm" variant="ghost" icon={<Plus size={14} />} onClick={handleNewChat} loading={creatingChat}>
              Новый чат
            </Button>
          </div>

          <div className="liquid-glass border-[var(--accent)]/20 rounded-2xl p-2 shadow-[0_0_0_1px_var(--accent)/5]">
            {conversations.length > 5 && (
              <div className="relative px-2 mb-2">
                <Search size={13} className="absolute left-5 top-1/2 -translate-y-1/2 text-[var(--text-muted)] pointer-events-none" />
                <input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Поиск чатов..."
                  className="w-full h-9 pl-9 pr-3 rounded-xl bg-[var(--bg-primary)] border border-[var(--border)] text-xs text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-[var(--accent)]/50 transition-colors"
                />
              </div>
            )}

            {filtered.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <MessageSquare size={36} className="text-[var(--text-muted)]/20 mb-3" />
                <p className="text-sm text-[var(--text-secondary)] mb-1">
                  {search ? 'Ничего не найдено' : 'Нет чатов в проекте'}
                </p>
                {!search && (
                  <p className="text-xs text-[var(--text-muted)]">
                    Создайте чат или отправьте сообщение в Telegram
                  </p>
                )}
              </div>
            ) : (
              <div className="flex flex-col gap-0.5">
                {filtered.map((c, i) => (
                  <motion.button
                    key={c.id}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.12, delay: i * 0.02 }}
                    onClick={() => navigate(`/chat/${c.id}`)}
                    className="flex items-center gap-3 px-3 py-3 rounded-xl hover:bg-[var(--bg-hover)] transition-all text-left group"
                  >
                    <div className="w-9 h-9 rounded-xl bg-[var(--accent-muted)] flex items-center justify-center shrink-0 group-hover:bg-[var(--accent)]/20 transition-colors">
                      <MessageSquare size={16} className="text-[var(--accent)]" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-[var(--text-primary)] truncate">{c.title}</p>
                      {c.last_message && (
                        <p className="text-xs text-[var(--text-muted)] truncate mt-0.5">{c.last_message}</p>
                      )}
                    </div>
                    {c.updated_at && (
                      <span className="text-[10px] text-[var(--text-muted)] ml-2 shrink-0 opacity-60 group-hover:opacity-100 transition-opacity">
                        {formatRelativeTime(c.updated_at)}
                      </span>
                    )}
                  </motion.button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* ═══════ DETAILS — 2-column grid below chats ═════════ */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

          {/* ── Context (left column) ─────────────────────────── */}
          <Section
            title="Контекст проекта"
            icon={<BookOpen size={14} />}
            badge={
              contextSaving ? (
                <span className="text-[10px] text-[var(--text-muted)]">Сохранение...</span>
              ) : contextSaved ? (
                <span className="text-[10px] text-green-500 flex items-center gap-1"><Check size={10} /> Сохранено</span>
              ) : null
            }
          >
            <textarea
              value={contextValue}
              onChange={(e) => handleContextChange(e.target.value)}
              placeholder="Цели, решения, статус... Или оставьте пустым — контекст сформируется из чатов."
              rows={3}
              className="no-focus-ring w-full rounded-lg bg-[var(--bg-primary)] border border-[var(--border)] text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] px-3 py-2.5 resize-y min-h-[60px] focus:outline-none focus:border-[var(--accent)]/50 transition-colors leading-relaxed"
            />

            {!contextValue && autoContext && autoContext.total_chats > 0 && (
              <div className="mt-2 p-2.5 rounded-lg bg-[var(--accent-muted)] border border-[var(--accent)]/10">
                <div className="flex items-center gap-1.5 mb-1.5">
                  <Zap size={11} className="text-[var(--accent)]" />
                  <span className="text-[10px] font-medium text-[var(--accent)]">Авто-контекст</span>
                </div>
                <div className="flex flex-col gap-0.5">
                  {autoContext.chats.slice(0, 4).map((c) => (
                    <div key={c.id} className="flex items-center gap-2 text-[11px]">
                      <span className="text-[var(--text-secondary)] truncate flex-1">{c.title}</span>
                      <span className="text-[var(--text-muted)] shrink-0">{c.message_count}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </Section>

          {/* ── Links + Members (right column) ────────────────── */}
          <div className="flex flex-col gap-4">
            <Section
              title="Ссылки"
              icon={<Link2 size={14} />}
              action={
                <button
                  onClick={() => setShowAddLink(true)}
                  className="text-xs text-[var(--accent)] hover:text-[var(--accent-hover)] transition-colors"
                >
                  +
                </button>
              }
            >
              {manualLinks.length > 0 && (
                <div className="flex flex-col gap-0.5 mb-1">
                  {manualLinks.map((link, i) => (
                    <div key={i} className="flex items-center gap-2 group/link px-2 py-1 rounded-md hover:bg-[var(--bg-hover)] transition-colors">
                      <ExternalLink size={11} className="text-[var(--accent)] shrink-0" />
                      <a href={link.url} target="_blank" rel="noopener noreferrer" className="text-xs text-[var(--accent)] hover:underline truncate flex-1">
                        {link.title || link.url}
                      </a>
                      <button onClick={() => handleRemoveLink(i)} aria-label="Удалить ссылку" title="Удалить ссылку" className="p-0.5 text-[var(--text-muted)] opacity-0 group-hover/link:opacity-100 hover:text-red-400 transition-all">
                        <X size={11} />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {uniqueAutoLinks.length > 0 && (
                <div className="flex flex-col gap-0.5">
                  {uniqueAutoLinks.slice(0, 5).map((link, i) => (
                    <a key={i} href={link.url} target="_blank" rel="noopener noreferrer" className="text-[11px] text-[var(--text-muted)] hover:text-[var(--accent)] truncate px-2 py-0.5 rounded hover:bg-[var(--bg-hover)] transition-colors">
                      {link.url}
                    </a>
                  ))}
                </div>
              )}

              {manualLinks.length === 0 && uniqueAutoLinks.length === 0 && !showAddLink && (
                <p className="text-[11px] text-[var(--text-muted)] text-center py-3">Появятся из чатов</p>
              )}

              {showAddLink && (
                <div className="mt-1.5 p-2.5 rounded-lg bg-[var(--bg-primary)] border border-[var(--border)]">
                  <input value={newLinkUrl} onChange={(e) => setNewLinkUrl(e.target.value)} placeholder="https://..." className="w-full h-7 px-2.5 rounded-md liquid-glass-input text-xs text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-[var(--accent)]/50 transition-colors mb-1.5" autoFocus />
                  <input value={newLinkTitle} onChange={(e) => setNewLinkTitle(e.target.value)} placeholder="Название" className="w-full h-7 px-2.5 rounded-md liquid-glass-input text-xs text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-[var(--accent)]/50 transition-colors mb-1.5" />
                  <div className="flex justify-end gap-2">
                    <button onClick={() => { setShowAddLink(false); setNewLinkUrl(''); setNewLinkTitle('') }} className="text-[11px] text-[var(--text-muted)]">Отмена</button>
                    <button onClick={handleAddLink} disabled={!newLinkUrl.trim()} className="text-[11px] text-[var(--accent)] disabled:opacity-40">Добавить</button>
                  </div>
                </div>
              )}
            </Section>

            <Section
              title="Участники"
              icon={<Users size={14} />}
              action={
                <button onClick={() => setShowAddMember(true)} className="text-xs text-[var(--accent)] hover:text-[var(--accent-hover)] transition-colors">
                  +
                </button>
              }
            >
              {members.length > 0 ? (
                <div className="flex flex-col gap-0.5">
                  {members.map((m) => (
                    <div key={m.id} className="flex items-center gap-2.5 px-2 py-1.5 rounded-md hover:bg-[var(--bg-hover)] transition-colors group/member">
                      <div className="w-6 h-6 rounded-full bg-[var(--accent-muted)] flex items-center justify-center">
                        <span className="text-[10px] font-medium text-[var(--accent)]">{m.capsule_id.charAt(0).toUpperCase()}</span>
                      </div>
                      <p className="text-xs text-[var(--text-primary)] truncate flex-1">{m.capsule_id}</p>
                      <button onClick={() => setRemoveMemberId(m.id)} aria-label="Удалить участника" title="Удалить участника" className="p-0.5 text-[var(--text-muted)] opacity-0 group-hover/member:opacity-100 hover:text-red-400 transition-all">
                        <Trash2 size={11} />
                      </button>
                    </div>
                  ))}
                </div>
              ) : !showAddMember ? (
                <p className="text-[11px] text-[var(--text-muted)] text-center py-3">Подключите капсулы</p>
              ) : null}

              {showAddMember && (
                <div className="mt-1.5 p-2.5 rounded-lg bg-[var(--bg-primary)] border border-[var(--border)]">
                  <input value={newCapsuleId} onChange={(e) => setNewCapsuleId(e.target.value)} placeholder="ID капсулы" className="w-full h-7 px-2.5 rounded-md liquid-glass-input text-xs text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-[var(--accent)]/50 transition-colors mb-1.5" autoFocus onKeyDown={(e) => { if (e.key === 'Enter') handleAddMember() }} />
                  <div className="flex justify-end gap-2">
                    <button onClick={() => { setShowAddMember(false); setNewCapsuleId('') }} className="text-[11px] text-[var(--text-muted)]">Отмена</button>
                    <button onClick={handleAddMember} disabled={!newCapsuleId.trim()} className="text-[11px] text-[var(--accent)] disabled:opacity-40">Подключить</button>
                  </div>
                </div>
              )}
            </Section>
          </div>
        </div>
        <ConfirmDialog
          open={removeMemberId !== null}
          onClose={() => setRemoveMemberId(null)}
          onConfirm={async () => {
            if (removeMemberId !== null) {
              await handleRemoveMember(removeMemberId)
              setRemoveMemberId(null)
            }
          }}
          title="Удалить участника"
          message="Участник будет отключён от проекта."
        />
      </motion.div>
    </div>
  )
}

// ── Helpers ──────────────────────────────────────────────────

function Section({
  title,
  icon,
  badge,
  action,
  children,
}: {
  title: string
  icon?: React.ReactNode
  badge?: React.ReactNode
  action?: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <div className="mb-6">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {icon && <span className="text-[var(--text-muted)]">{icon}</span>}
          <h2 className="text-sm font-semibold text-[var(--text-primary)]">{title}</h2>
          {badge}
        </div>
        {action}
      </div>
      <div className="liquid-glass rounded-xl p-4">
        {children}
      </div>
    </div>
  )
}

function pluralChats(n: number): string {
  if (n === 1) return 'чат'
  if (n >= 2 && n <= 4) return 'чата'
  return 'чатов'
}

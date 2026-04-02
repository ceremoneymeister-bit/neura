import {
  type KeyboardEvent,
  useEffect,
  useRef,
  useState,
} from 'react'
import { Check, ChevronDown, ChevronRight, Pencil, Plus, Trash2, X } from 'lucide-react'
import {
  type Project,
  createProject,
  deleteProject,
  updateProject,
} from '@/api/projects'
import { type Conversation } from '@/api/conversations'

interface ProjectListProps {
  projects: Project[]
  conversations: Conversation[]
  activeId?: string
  onNavigate: (id: number) => void
  onReload: () => void
}

export function ProjectList({
  projects,
  conversations,
  activeId,
  onNavigate,
  onReload,
}: ProjectListProps) {
  const [expanded, setExpanded] = useState<Set<number>>(new Set())
  const [creating, setCreating] = useState(false)
  const [newName, setNewName] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editName, setEditName] = useState('')
  const [deletingId, setDeletingId] = useState<number | null>(null)

  const createRef = useRef<HTMLInputElement>(null)
  const editRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (creating) createRef.current?.focus()
  }, [creating])

  useEffect(() => {
    if (editingId !== null) editRef.current?.focus()
  }, [editingId])

  const toggle = (id: number) =>
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })

  const handleCreate = async () => {
    const name = newName.trim()
    setCreating(false)
    setNewName('')
    if (!name) return
    try {
      await createProject(name)
      onReload()
    } catch (e) {
      console.error(e)
    }
  }

  const handleCreateKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') handleCreate()
    if (e.key === 'Escape') { setCreating(false); setNewName('') }
  }

  const startEdit = (p: Project) => {
    setEditingId(p.id)
    setEditName(p.name)
  }

  const commitEdit = async () => {
    const id = editingId
    const name = editName.trim()
    setEditingId(null)
    setEditName('')
    if (!id || !name) return
    try {
      await updateProject(id, { name })
      onReload()
    } catch (e) {
      console.error(e)
    }
  }

  const handleEditKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') commitEdit()
    if (e.key === 'Escape') { setEditingId(null); setEditName('') }
  }

  const handleDelete = async (id: number) => {
    setDeletingId(null)
    try {
      await deleteProject(id)
      onReload()
    } catch (e) {
      console.error(e)
    }
  }

  const projectConvs = (pid: number) =>
    conversations.filter((c) => c.project_id === pid)

  return (
    <div className="mt-2">
      {/* Section header */}
      <div className="flex items-center px-2 mb-1">
        <p className="flex-1 text-[10px] font-semibold uppercase tracking-wider text-[#525252]">
          📁 Проекты
        </p>
        <button
          onClick={() => setCreating(true)}
          title="Создать проект"
          className="text-[#525252] hover:text-[#a3a3a3] transition-colors p-0.5"
        >
          <Plus size={12} />
        </button>
      </div>

      {/* Inline create */}
      {creating && (
        <div className="px-2 mb-1 flex items-center gap-1">
          <input
            ref={createRef}
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={handleCreateKey}
            onBlur={handleCreate}
            placeholder="Название проекта"
            className="flex-1 h-6 px-2 rounded-[4px] bg-[#1a1a1a] border border-[#7c3aed]/50 text-xs text-[#f5f5f5] placeholder-[#525252] focus:outline-none"
          />
          <button
            onMouseDown={(e) => e.preventDefault()}
            onClick={handleCreate}
            className="text-emerald-400 hover:text-emerald-300 transition-colors"
          >
            <Check size={12} />
          </button>
          <button
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => { setCreating(false); setNewName('') }}
            className="text-[#525252] hover:text-red-400 transition-colors"
          >
            <X size={12} />
          </button>
        </div>
      )}

      {/* Project list */}
      {projects.map((p) => {
        const isOpen = expanded.has(p.id)
        const isEditing = editingId === p.id
        const isDeleting = deletingId === p.id
        const convs = projectConvs(p.id)

        return (
          <div key={p.id}>
            {/* Project header row */}
            <div
              className="group flex items-center gap-1 px-1 py-1 rounded-[6px] hover:bg-[#1a1a1a] transition-colors cursor-pointer"
            >
              {/* Expand toggle */}
              <button
                onClick={() => toggle(p.id)}
                className="text-[#525252] hover:text-[#a3a3a3] flex-shrink-0 p-0.5 transition-colors"
              >
                {isOpen
                  ? <ChevronDown size={11} />
                  : <ChevronRight size={11} />}
              </button>

              <span className="text-sm flex-shrink-0 leading-none">{p.icon}</span>

              {/* Name or inline edit */}
              {isEditing ? (
                <input
                  ref={editRef}
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  onKeyDown={handleEditKey}
                  onBlur={commitEdit}
                  className="flex-1 h-5 px-1 rounded bg-[#1a1a1a] border border-[#7c3aed]/50 text-xs text-[#f5f5f5] focus:outline-none"
                />
              ) : (
                <button
                  onClick={() => toggle(p.id)}
                  onDoubleClick={() => startEdit(p)}
                  className="flex-1 text-left text-xs text-[#a3a3a3] group-hover:text-[#f5f5f5] truncate transition-colors"
                >
                  {p.name}
                </button>
              )}

              {/* Chats count badge */}
              {!isEditing && convs.length > 0 && (
                <span className="text-[10px] text-[#525252] group-hover:opacity-0 transition-opacity ml-1">
                  {convs.length}
                </span>
              )}

              {/* Action buttons (hover) */}
              {!isEditing && !isDeleting && (
                <div className="opacity-0 group-hover:opacity-100 flex items-center gap-0.5 transition-opacity">
                  <button
                    onClick={(e) => { e.stopPropagation(); startEdit(p) }}
                    title="Переименовать"
                    className="p-0.5 text-[#525252] hover:text-[#a3a3a3] transition-colors"
                  >
                    <Pencil size={10} />
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); setDeletingId(p.id) }}
                    title="Удалить"
                    className="p-0.5 text-[#525252] hover:text-red-400 transition-colors"
                  >
                    <Trash2 size={10} />
                  </button>
                </div>
              )}
            </div>

            {/* Delete confirmation */}
            {isDeleting && (
              <div className="mx-2 mb-1 px-2 py-1.5 rounded-[6px] bg-red-500/10 border border-red-500/20">
                <p className="text-[10px] text-red-400 mb-1.5">
                  Удалить «{p.name}»? Чаты останутся.
                </p>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleDelete(p.id)}
                    className="text-[10px] text-red-400 hover:text-red-300 font-medium transition-colors"
                  >
                    Удалить
                  </button>
                  <button
                    onClick={() => setDeletingId(null)}
                    className="text-[10px] text-[#525252] hover:text-[#a3a3a3] transition-colors"
                  >
                    Отмена
                  </button>
                </div>
              </div>
            )}

            {/* Conversations inside project */}
            {isOpen && (
              <div className="ml-5 border-l border-[#262626] pl-1.5 mb-0.5">
                {convs.length === 0 ? (
                  <p className="text-[10px] text-[#525252] py-1 px-1">Нет чатов</p>
                ) : (
                  convs.map((c) => {
                    const isActive = String(c.id) === activeId
                    return (
                      <button
                        key={c.id}
                        onClick={() => onNavigate(c.id)}
                        className={[
                          'w-full text-left px-2 py-1 rounded-[4px] text-xs truncate transition-colors',
                          isActive
                            ? 'bg-[#7c3aed]/15 text-[#f5f5f5] border-l-2 border-[#7c3aed]'
                            : 'text-[#a3a3a3] hover:bg-[#1a1a1a] hover:text-[#f5f5f5]',
                        ].join(' ')}
                      >
                        {c.title}
                      </button>
                    )
                  })
                )}
              </div>
            )}
          </div>
        )
      })}

      {/* Empty state */}
      {projects.length === 0 && !creating && (
        <button
          onClick={() => setCreating(true)}
          className="w-full text-left px-2 py-1 text-[10px] text-[#525252] hover:text-[#a3a3a3] transition-colors"
        >
          + Создать первый проект
        </button>
      )}
    </div>
  )
}

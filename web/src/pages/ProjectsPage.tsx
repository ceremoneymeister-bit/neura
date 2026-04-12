import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Plus, Search, FolderOpen, Trash2, Pin, PinOff } from 'lucide-react'
import { ProjectIcon } from '@/components/ui/NeuraIcon'
import {
  type Project,
  listProjects,
  createProject,
  updateProject,
  deleteProject,
} from '@/api/projects'
import { Modal } from '@/components/ui/Modal'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { formatRelativeTime } from '@/utils/time'
import { useToast } from '@/components/ui/Toast'

// Icon picker removed — using unified brand ProjectIcon

export function ProjectsPage() {
  const navigate = useNavigate()
  const { error: showError } = useToast()
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [createName, setCreateName] = useState('')
  const [createIcon, setCreateIcon] = useState('')
  const [createDesc, setCreateDesc] = useState('')
  const [creating, setCreating] = useState(false)
  const [deleteId, setDeleteId] = useState<number | null>(null)

  const load = useCallback(async () => {
    try {
      const data = await listProjects()
      setProjects(data)
    } catch (e) {
      console.error(e)
      showError('Не удалось загрузить проекты')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const filtered = useMemo(() => {
    const q = search.toLowerCase().trim()
    if (!q) return projects
    return projects.filter(
      (p) => p.name.toLowerCase().includes(q) || p.description.toLowerCase().includes(q),
    )
  }, [projects, search])

  const handleCreate = async () => {
    const name = createName.trim()
    if (!name || creating) return
    setCreating(true)
    try {
      const proj = await createProject(name, createIcon, createDesc.trim())
      setProjects((prev) => [proj, ...prev])
      document.dispatchEvent(new Event('neura:reload-sidebar'))
      setShowCreate(false)
      setCreateName('')
      setCreateIcon('')
      setCreateDesc('')
    } catch (e) {
      console.error(e)
      showError('Не удалось создать проект')
    } finally {
      setCreating(false)
    }
  }

  const handlePin = async (p: Project) => {
    try {
      await updateProject(p.id, { pinned: !p.pinned })
      load()
    } catch (e) {
      console.error(e)
      showError('Не удалось обновить проект')
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await deleteProject(id)
      setProjects((prev) => prev.filter((p) => p.id !== id))
      document.dispatchEvent(new Event('neura:reload-sidebar'))
    } catch (e) {
      console.error(e)
      showError('Не удалось удалить проект')
    }
  }

  return (
    <div className="h-full overflow-y-auto">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="max-w-4xl mx-auto px-4 py-8"
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-lg font-semibold text-[var(--text-primary)]">Проекты</h1>
          <Button
            icon={<Plus size={14} />}
            size="sm"
            onClick={() => setShowCreate(true)}
          >
            Создать
          </Button>
        </div>

        {/* Search */}
        {projects.length > 0 && (
          <div className="relative mb-6">
            <Search
              size={14}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)] pointer-events-none"
            />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Поиск проектов..."
              className="w-full h-9 pl-9 pr-4 rounded-lg bg-[var(--bg-card)] border border-[var(--border)] text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-[var(--accent)]/50 transition-colors"
            />
          </div>
        )}

        {/* Grid */}
        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="rounded-xl border border-[var(--border)] p-4">
                <div className="skeleton h-7 w-7 rounded-lg mb-3" />
                <div className="skeleton h-4 w-3/4 rounded mb-2" />
                <div className="skeleton h-3 w-full rounded mb-1.5" />
                <div className="skeleton h-3 w-1/2 rounded" />
              </div>
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <FolderOpen size={48} className="text-[var(--text-muted)]/30 mb-4" />
            <p className="text-sm text-[var(--text-secondary)] mb-1">
              {search ? 'Ничего не найдено' : 'Нет проектов'}
            </p>
            {!search && (
              <p className="text-xs text-[var(--text-muted)] mb-4">
                Создайте первый проект для организации чатов
              </p>
            )}
            {!search && (
              <Button size="sm" icon={<Plus size={14} />} onClick={() => setShowCreate(true)}>
                Создать проект
              </Button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4 gap-4">
            {filtered.map((p, i) => (
              <motion.div
                key={p.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2, delay: i * 0.04 }}
              >
                <ProjectCard
                  project={p}
                  onClick={() => navigate(`/projects/${p.id}`)}
                  onPin={() => handlePin(p)}
                  onDelete={() => setDeleteId(p.id)}
                />
              </motion.div>
            ))}
          </div>
        )}
      </motion.div>

      {/* Create Modal */}
      <Modal
        open={showCreate}
        onClose={() => setShowCreate(false)}
        title="Новый проект"
      >
        <div className="flex flex-col gap-4">
          <Input
            label="Название"
            value={createName}
            onChange={(e) => setCreateName(e.target.value)}
            placeholder="Например: Neura v2"
            autoFocus
          />

          <div>
            <p className="text-xs font-medium text-[var(--text-secondary)] mb-1.5">Описание</p>
            <textarea
              value={createDesc}
              onChange={(e) => setCreateDesc(e.target.value)}
              placeholder="О чём этот проект? (необязательно)"
              rows={2}
              className="w-full rounded-md bg-[var(--bg-input)] border border-[var(--border)] text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] px-3 py-2 resize-none focus:outline-none focus:border-[var(--accent)]/50 transition-colors"
            />
          </div>

          <div className="flex justify-end gap-2 mt-2">
            <Button variant="ghost" size="sm" onClick={() => setShowCreate(false)}>
              Отмена
            </Button>
            <Button
              size="sm"
              loading={creating}
              onClick={handleCreate}
              disabled={!createName.trim()}
            >
              Создать
            </Button>
          </div>
        </div>
      </Modal>

      <ConfirmDialog
        open={deleteId !== null}
        onClose={() => setDeleteId(null)}
        onConfirm={async () => {
          if (deleteId !== null) {
            await handleDelete(deleteId)
            setDeleteId(null)
          }
        }}
        title="Удалить проект"
        message="Проект и все его чаты будут удалены. Это действие нельзя отменить."
      />
    </div>
  )
}

function ProjectCard({
  project,
  onClick,
  onPin,
  onDelete,
}: {
  project: Project
  onClick: () => void
  onPin: () => void
  onDelete: () => void
}) {
  return (
    <button
      onClick={onClick}
      className="group w-full text-left p-4 rounded-xl bg-[var(--bg-card)] border border-[var(--border)] hover:border-[var(--text-muted)]/20 transition-all"
    >
      <div className="flex items-start justify-between mb-3">
        <ProjectIcon size={28} />
        <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={(e) => { e.stopPropagation(); onPin() }}
            title={project.pinned ? 'Открепить' : 'Закрепить'}
            aria-label={project.pinned ? 'Открепить' : 'Закрепить'}
            className="p-1 text-[var(--text-muted)] hover:text-[var(--text-secondary)] transition-colors rounded"
          >
            {project.pinned ? <PinOff size={12} /> : <Pin size={12} />}
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); onDelete() }}
            title="Удалить"
            aria-label="Удалить"
            className="p-1 text-[var(--text-muted)] hover:text-red-400 transition-colors rounded"
          >
            <Trash2 size={12} />
          </button>
        </div>
      </div>

      <p className="text-sm font-medium text-[var(--text-primary)] truncate mb-1">
        {project.name}
      </p>
      {project.description && (
        <p className="text-xs text-[var(--text-muted)] line-clamp-2 mb-2 leading-relaxed">
          {project.description}
        </p>
      )}
      <div className="flex items-center gap-2 text-[10px] text-[var(--text-muted)]">
        <span>{project.chats_count} {project.chats_count === 1 ? 'чат' : 'чатов'}</span>
        {project.created_at && (
          <>
            <span>·</span>
            <span>{formatRelativeTime(project.created_at)}</span>
          </>
        )}
      </div>
    </button>
  )
}

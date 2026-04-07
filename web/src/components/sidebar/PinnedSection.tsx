import { X } from 'lucide-react'
import { type Conversation, updateConversation } from '@/api/conversations'
import { type Project, updateProject } from '@/api/projects'
import { PinIcon } from '@/components/ui/NeuraIcon'

interface PinnedSectionProps {
  conversations: Conversation[]
  projects: Project[]
  activeId?: string
  unreadIds?: Set<number>
  onNavigate: (id: number) => void
  onProjectNavigate?: (projectId: number) => void
  onReload: () => void
}

export function PinnedSection({
  conversations,
  projects,
  activeId,
  unreadIds,
  onNavigate,
  onProjectNavigate,
  onReload,
}: PinnedSectionProps) {
  if (conversations.length === 0 && projects.length === 0) return null

  const handleUnpinConv = async (id: number) => {
    try {
      await updateConversation(id, { pinned: false })
      onReload()
    } catch (e) {
      console.error(e)
    }
  }

  const handleUnpinProject = async (id: number) => {
    try {
      await updateProject(id, { pinned: false })
      onReload()
    } catch (e) {
      console.error(e)
    }
  }

  return (
    <div className="mt-2">
      <p className="px-2 mb-1 text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)] flex items-center gap-1">
        <PinIcon size={10} /> Закреплённые
      </p>

      {projects.map((p) => (
        <PinnedItem
          key={`project-${p.id}`}
          label={`${p.icon} ${p.name}`}
          active={false}
          onNavigate={() => onProjectNavigate?.(p.id)}
          onUnpin={() => handleUnpinProject(p.id)}
        />
      ))}

      {conversations.map((c) => (
        <PinnedItem
          key={`conv-${c.id}`}
          label={c.title}
          active={String(c.id) === activeId}
          unread={!!(unreadIds?.has(c.id) && String(c.id) !== activeId)}
          onNavigate={() => onNavigate(c.id)}
          onUnpin={() => handleUnpinConv(c.id)}
        />
      ))}
    </div>
  )
}

function PinnedItem({
  label,
  active,
  unread = false,
  onNavigate,
  onUnpin,
}: {
  label: string
  active: boolean
  unread?: boolean
  onNavigate: () => void
  onUnpin: () => void
}) {
  return (
    <div
      className={[
        'group flex items-center gap-1 px-2 py-1 rounded-[6px] transition-colors',
        active ? 'bg-[var(--accent)]/15' : 'hover:bg-[var(--bg-hover)]',
      ].join(' ')}
    >
      {unread && (
        <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent)] shrink-0" />
      )}
      <button
        onClick={onNavigate}
        className={[
          'flex-1 text-left text-xs truncate transition-colors',
          active
            ? 'text-[var(--text-primary)] font-medium'
            : unread
              ? 'text-[var(--text-primary)] font-medium'
              : 'text-[var(--text-secondary)] group-hover:text-[var(--text-primary)]',
        ].join(' ')}
      >
        {label}
      </button>
      <button
        onClick={(e) => {
          e.stopPropagation()
          onUnpin()
        }}
        title="Открепить"
        className="opacity-0 group-hover:opacity-100 p-0.5 text-[var(--text-muted)] hover:text-red-400 transition-all"
      >
        <X size={11} />
      </button>
    </div>
  )
}

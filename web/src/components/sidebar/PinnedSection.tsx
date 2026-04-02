import { X } from 'lucide-react'
import { type Conversation, updateConversation } from '@/api/conversations'
import { type Project, updateProject } from '@/api/projects'

interface PinnedSectionProps {
  conversations: Conversation[]
  projects: Project[]
  activeId?: string
  onNavigate: (id: number) => void
  onReload: () => void
}

export function PinnedSection({
  conversations,
  projects,
  activeId,
  onNavigate,
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
      <p className="px-2 mb-1 text-[10px] font-semibold uppercase tracking-wider text-[#525252]">
        📌 Закреплённые
      </p>

      {projects.map((p) => (
        <PinnedItem
          key={`project-${p.id}`}
          label={`${p.icon} ${p.name}`}
          active={false}
          onNavigate={() => {}}
          onUnpin={() => handleUnpinProject(p.id)}
        />
      ))}

      {conversations.map((c) => (
        <PinnedItem
          key={`conv-${c.id}`}
          label={c.title}
          active={String(c.id) === activeId}
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
  onNavigate,
  onUnpin,
}: {
  label: string
  active: boolean
  onNavigate: () => void
  onUnpin: () => void
}) {
  return (
    <div
      className={[
        'group flex items-center gap-1 px-2 py-1 rounded-[6px] transition-colors',
        active ? 'bg-[#7c3aed]/15' : 'hover:bg-[#1a1a1a]',
      ].join(' ')}
    >
      <button
        onClick={onNavigate}
        className={[
          'flex-1 text-left text-xs truncate transition-colors',
          active
            ? 'text-[#f5f5f5] font-medium'
            : 'text-[#a3a3a3] group-hover:text-[#f5f5f5]',
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
        className="opacity-0 group-hover:opacity-100 p-0.5 text-[#525252] hover:text-red-400 transition-all"
      >
        <X size={11} />
      </button>
    </div>
  )
}

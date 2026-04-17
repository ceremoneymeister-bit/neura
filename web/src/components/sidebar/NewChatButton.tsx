import { useEffect } from 'react'
import { Plus } from 'lucide-react'
import { Spinner } from '@/components/ui/Spinner'

interface NewChatButtonProps {
  onClick: () => void
  loading?: boolean
}

export function NewChatButton({ onClick, loading = false }: NewChatButtonProps) {
  // Listen for global keyboard shortcut dispatched from App.tsx
  useEffect(() => {
    const handler = () => onClick()
    document.addEventListener('neura:new-chat', handler)
    return () => document.removeEventListener('neura:new-chat', handler)
  }, [onClick])

  return (
    <button
      onClick={onClick}
      disabled={loading}
      title="Новый чат (Ctrl+Shift+N)"
      className="w-full flex items-center gap-2 h-8 px-4 rounded-full bg-[var(--accent)]/80 text-white text-sm font-medium backdrop-blur-lg border border-white/15 shadow-[inset_0_1px_0_rgba(255,255,255,0.2),0_2px_8px_rgba(0,0,0,0.12)] hover:bg-[var(--accent)]/90 active:scale-[0.97] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
    >
      {loading ? <Spinner size="sm" /> : <Plus size={14} />}
      <span className="flex-1 text-left text-xs">Новый чат</span>
      <kbd className="hidden sm:inline text-[9px] opacity-40 font-mono bg-white/10 px-1 py-0.5 rounded">
        ⇧⌘N
      </kbd>
    </button>
  )
}

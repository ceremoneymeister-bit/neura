import { useState, useCallback, useEffect } from 'react'
import { Outlet, useParams } from 'react-router-dom'
import { PanelLeft } from 'lucide-react'
import { StatusBar } from './StatusBar'
import { Sidebar } from '@/components/sidebar/Sidebar'
import { motion, AnimatePresence } from 'framer-motion'

export function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const { id: chatId } = useParams<{ id?: string }>()
  const [chatTitle, setChatTitle] = useState<string | null>(null)

  const toggleSidebar = useCallback(() => setSidebarOpen((v) => !v), [])

  // Keyboard shortcut: Ctrl+B
  useEffect(() => {
    const handler = () => toggleSidebar()
    document.addEventListener('neura:toggle-sidebar', handler)
    return () => document.removeEventListener('neura:toggle-sidebar', handler)
  }, [toggleSidebar])

  // Listen for conversation title updates from ChatView
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail
      setChatTitle(detail?.title ?? null)
    }
    document.addEventListener('neura:set-chat-title', handler)
    return () => document.removeEventListener('neura:set-chat-title', handler)
  }, [])

  // Reset title when leaving chat
  useEffect(() => {
    if (!chatId) setChatTitle(null)
  }, [chatId])

  return (
    <div className="flex h-full bg-[var(--bg-primary)] overflow-hidden">
      {/* Sidebar — desktop */}
      <AnimatePresence initial={false}>
        {sidebarOpen && (
          <motion.div
            key="sidebar"
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 260, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: 'easeInOut' }}
            className="hidden md:flex flex-col overflow-hidden shrink-0 border-r border-[var(--border)]/40"
            style={{ minWidth: 0, maxWidth: 260 }}
          >
            <Sidebar onClose={() => setSidebarOpen(false)} />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Mobile sidebar overlay */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.div
            key="mobile-sidebar"
            className="fixed inset-0 z-40 flex md:hidden"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
          >
            <div
              className="absolute inset-0 bg-black/50"
              onClick={() => setSidebarOpen(false)}
            />
            <motion.div
              className="relative z-50 flex flex-col w-[260px] bg-[var(--bg-sidebar)] border-r border-[var(--border)]/40"
              initial={{ x: -260 }}
              animate={{ x: 0 }}
              exit={{ x: -260 }}
              transition={{ duration: 0.2, ease: 'easeInOut' }}
            >
              <Sidebar onClose={() => setSidebarOpen(false)} />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main area */}
      <div className="flex flex-col flex-1 min-w-0">
        {/* Top bar */}
        <div className="flex items-center gap-2 px-3 h-11 shrink-0">
          {/* Show sidebar toggle ONLY when sidebar is hidden */}
          {!sidebarOpen && (
            <button
              onClick={toggleSidebar}
              className="p-1.5 rounded-md text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition-colors shrink-0"
              title="Открыть панель (Ctrl+B)"
            >
              <PanelLeft size={16} />
            </button>
          )}

          {/* Conversation title — dynamic, only in chat */}
          {chatId && (
            <span className="text-sm text-[var(--text-secondary)] truncate select-none">
              {chatTitle || 'Новый чат'}
            </span>
          )}
        </div>

        {/* Page content */}
        <div className="flex-1 overflow-hidden">
          <Outlet />
        </div>

        <StatusBar />
      </div>
    </div>
  )
}

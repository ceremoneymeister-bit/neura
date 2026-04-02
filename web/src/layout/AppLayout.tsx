import { useState, useCallback, useEffect, useRef } from 'react'
import { Outlet } from 'react-router-dom'
import { PanelLeft, ChevronDown, Sparkles } from 'lucide-react'
import { StatusBar } from './StatusBar'
import { Sidebar } from '@/components/sidebar/Sidebar'
import { motion, AnimatePresence } from 'framer-motion'

const MODEL_OPTIONS = [
  { id: 'sonnet-4-6', label: 'Sonnet 4.6', desc: 'Быстрый и умный' },
  { id: 'opus-4-6', label: 'Opus 4.6', desc: 'Максимальный интеллект' },
  { id: 'haiku-4-5', label: 'Haiku 4.5', desc: 'Сверхбыстрый' },
]

export function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [selectedModel, setSelectedModel] = useState(MODEL_OPTIONS[0])
  const [modelDropdownOpen, setModelDropdownOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  const toggleSidebar = useCallback(() => setSidebarOpen((v) => !v), [])

  // Keyboard shortcut: Ctrl+B — wired via global listener in App.tsx
  useEffect(() => {
    const handler = () => toggleSidebar()
    document.addEventListener('neura:toggle-sidebar', handler)
    return () => document.removeEventListener('neura:toggle-sidebar', handler)
  }, [toggleSidebar])

  // Close model dropdown on outside click
  useEffect(() => {
    if (!modelDropdownOpen) return
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setModelDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [modelDropdownOpen])

  return (
    <div className="flex h-full bg-[#0a0a0a] overflow-hidden">
      {/* Sidebar — desktop */}
      <AnimatePresence initial={false}>
        {sidebarOpen && (
          <motion.div
            key="sidebar"
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 280, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: 'easeInOut' }}
            className="hidden md:flex flex-col overflow-hidden shrink-0 border-r border-[#1a1a1a]"
            style={{ minWidth: 0 }}
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
              className="relative z-50 flex flex-col w-72 bg-[#141414] border-r border-[#1a1a1a]"
              initial={{ x: -280 }}
              animate={{ x: 0 }}
              exit={{ x: -280 }}
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
        <div className="flex items-center gap-2 px-3 h-11 border-b border-[#1a1a1a] shrink-0">
          {/* Left: toggle + title */}
          <button
            onClick={toggleSidebar}
            className="p-1.5 rounded-[6px] text-[#525252] hover:text-[#f5f5f5] hover:bg-[#1a1a1a] transition-colors shrink-0"
            title="Toggle sidebar (Ctrl+B)"
          >
            <PanelLeft size={16} />
          </button>

          <span className="text-sm text-[#a3a3a3] truncate select-none">
            Новый чат
          </span>

          {/* Spacer */}
          <div className="flex-1" />

          {/* Right: model selector pill */}
          <div className="relative hidden sm:block" ref={dropdownRef}>
            <button
              onClick={() => setModelDropdownOpen((v) => !v)}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-[#262626] bg-[#141414] hover:border-[#7c3aed]/40 hover:bg-[#7c3aed]/5 transition-all text-xs text-[#a3a3a3] hover:text-[#f5f5f5]"
            >
              <Sparkles size={12} className="text-[#7c3aed]" />
              <span>{selectedModel.label}</span>
              <ChevronDown
                size={12}
                className={`transition-transform duration-150 ${modelDropdownOpen ? 'rotate-180' : ''}`}
              />
            </button>

            <AnimatePresence>
              {modelDropdownOpen && (
                <motion.div
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -4 }}
                  transition={{ duration: 0.12 }}
                  className="absolute right-0 top-full mt-1.5 w-56 rounded-[10px] border border-[#262626] bg-[#141414] shadow-lg shadow-black/40 z-50 overflow-hidden"
                >
                  {MODEL_OPTIONS.map((model) => (
                    <button
                      key={model.id}
                      onClick={() => {
                        setSelectedModel(model)
                        setModelDropdownOpen(false)
                      }}
                      className={`flex flex-col w-full px-3 py-2.5 text-left transition-colors ${
                        selectedModel.id === model.id
                          ? 'bg-[#7c3aed]/10'
                          : 'hover:bg-[#1a1a1a]'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <Sparkles
                          size={12}
                          className={
                            selectedModel.id === model.id
                              ? 'text-[#7c3aed]'
                              : 'text-[#525252]'
                          }
                        />
                        <span
                          className={`text-xs font-medium ${
                            selectedModel.id === model.id
                              ? 'text-[#f5f5f5]'
                              : 'text-[#a3a3a3]'
                          }`}
                        >
                          {model.label}
                        </span>
                      </div>
                      <span className="text-[11px] text-[#525252] ml-5">
                        {model.desc}
                      </span>
                    </button>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
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

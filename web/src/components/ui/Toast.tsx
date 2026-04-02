import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { CheckCircle, XCircle, Info, X } from 'lucide-react'

type ToastType = 'success' | 'error' | 'info'

interface Toast {
  id: string
  type: ToastType
  message: string
  duration?: number
}

interface ToastContextValue {
  toast: (message: string, type?: ToastType, duration?: number) => void
  success: (message: string) => void
  error: (message: string) => void
  info: (message: string) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

const icons: Record<ToastType, ReactNode> = {
  success: <CheckCircle size={15} className="text-emerald-400 shrink-0" />,
  error:   <XCircle    size={15} className="text-red-400 shrink-0" />,
  info:    <Info       size={15} className="text-blue-400 shrink-0" />,
}

function ToastItem({ t, onDismiss }: { t: Toast; onDismiss: (id: string) => void }) {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    timerRef.current = setTimeout(() => onDismiss(t.id), t.duration ?? 4000)
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [t.id, t.duration, onDismiss])

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 12, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -8, scale: 0.95 }}
      transition={{ duration: 0.15 }}
      className="flex items-start gap-2.5 min-w-[260px] max-w-[360px] rounded-[8px] bg-[#1e1e1e] border border-[#262626] px-4 py-3 shadow-lg"
    >
      {icons[t.type]}
      <p className="flex-1 text-sm text-[#f5f5f5] leading-snug">{t.message}</p>
      <button
        onClick={() => onDismiss(t.id)}
        className="text-[#525252] hover:text-[#f5f5f5] transition-colors shrink-0 mt-0.5"
      >
        <X size={13} />
      </button>
    </motion.div>
  )
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const toast = useCallback((message: string, type: ToastType = 'info', duration?: number) => {
    const id = `${Date.now()}-${Math.random()}`
    setToasts((prev) => [...prev, { id, type, message, duration }])
  }, [])

  const value: ToastContextValue = {
    toast,
    success: (m) => toast(m, 'success'),
    error:   (m) => toast(m, 'error'),
    info:    (m) => toast(m, 'info'),
  }

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 pointer-events-none">
        <AnimatePresence initial={false}>
          {toasts.map((t) => (
            <div key={t.id} className="pointer-events-auto">
              <ToastItem t={t} onDismiss={dismiss} />
            </div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  )
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within ToastProvider')
  return ctx
}

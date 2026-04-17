import { type ReactNode, Component, useEffect } from 'react'
import { BrowserRouter, Navigate, Outlet, Route, Routes, useLocation } from 'react-router-dom'
import { AuthProvider, useAuth } from '@/hooks/useAuth'
import { ThemeProvider } from '@/hooks/useTheme'
import { useBrandTheme } from '@/hooks/useBrandTheme'
import { ToastProvider } from '@/components/ui/Toast'
import { AppLayout } from '@/layout/AppLayout'
import { LoginPage } from '@/pages/LoginPage'
import { RegisterPage } from '@/pages/RegisterPage'
import { ChatPage } from '@/pages/ChatPage'
import { SettingsPage } from '@/pages/SettingsPage'
import { ProjectsPage } from '@/pages/ProjectsPage'
import { ProjectDetailPage } from '@/pages/ProjectDetailPage'
import { NotFoundPage } from '@/pages/NotFoundPage'
import { HeartbeatPage } from '@/pages/HeartbeatPage'
import { DiaryPage } from '@/pages/DiaryPage'
import { MemoryPage } from '@/pages/MemoryPage'
import { Spinner } from '@/components/ui/Spinner'

// ── Error Boundary ───────────────────────────────────────────────

interface ErrorState {
  error: Error | null
}

class ErrorBoundary extends Component<{ children: ReactNode }, ErrorState> {
  state: ErrorState = { error: null }

  static getDerivedStateFromError(error: Error): ErrorState {
    return { error }
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex flex-col items-center justify-center min-h-screen gap-4 text-center px-4 bg-[var(--bg-primary)]">
          <div className="text-4xl text-[var(--accent)]">!</div>
          <h1 className="text-lg font-semibold text-[var(--text-primary)]">Что-то пошло не так</h1>
          <p className="text-sm text-[var(--text-muted)] max-w-xs font-mono">{this.state.error.message}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-2 px-5 py-2 rounded-full bg-[var(--accent)]/80 text-white text-sm backdrop-blur-lg border border-white/15 shadow-[inset_0_1px_0_rgba(255,255,255,0.2)] hover:bg-[var(--accent)]/90 transition-all"
          >
            Перезагрузить
          </button>
        </div>
      )
    }
    return this.props.children
  }
}

// ── Protected Route ──────────────────────────────────────────────

function ProtectedRoute() {
  const { user, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-[var(--bg-primary)]">
        <Spinner size="lg" />
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return <Outlet />
}

// ── Title manager ─────────────────────────────────────────────────

function TitleManager() {
  const location = useLocation()
  const { brandName } = useBrandTheme()
  useEffect(() => {
    const path = location.pathname
    const name = brandName || 'Neura'
    let title = name
    if (path.startsWith('/chat/')) title = `Чат — ${name}`
    else if (path === '/chat') title = `Новый чат — ${name}`
    else if (path === '/projects') title = `Проекты — ${name}`
    else if (path.startsWith('/projects/')) title = `Проект — ${name}`
    else if (path === '/settings') title = `Настройки — ${name}`
    else if (path === '/heartbeat') title = `Автоматизации — ${name}`
    else if (path === '/diary') title = `Дневник — ${name}`
    else if (path === '/memory') title = `Память — ${name}`
    else if (path === '/login') title = `Войти — ${name}`
    else if (path === '/register') title = `Регистрация — ${name}`
    document.title = title
  }, [location, brandName])
  return null
}

// ── Keyboard shortcuts ───────────────────────────────────────────

function KeyboardShortcuts() {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // Ctrl+K — focus search (custom event)
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault()
        document.dispatchEvent(new CustomEvent('neura:search-focus'))
      }
      // Ctrl+Shift+N — new chat
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'N') {
        e.preventDefault()
        document.dispatchEvent(new CustomEvent('neura:new-chat'))
      }
      // Ctrl+B — toggle sidebar
      if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
        e.preventDefault()
        document.dispatchEvent(new CustomEvent('neura:toggle-sidebar'))
      }
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [])
  return null
}

// ── Brand Theme Loader ──────────────────────────────────────────

function BrandThemeLoader() {
  useBrandTheme()
  return null
}

// ── App ──────────────────────────────────────────────────────────

export default function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <BrowserRouter>
          <AuthProvider>
            <ToastProvider>
            <TitleManager />
            <KeyboardShortcuts />
            <Routes>
              <Route path="/login"    element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />

              <Route element={<ProtectedRoute />}>
                <Route element={<><BrandThemeLoader /><AppLayout /></>}>
                  <Route index element={<Navigate to="/chat" replace />} />
                  <Route path="/chat"         element={<ChatPage />} />
                  <Route path="/chat/:id"     element={<ChatPage />} />
                  <Route path="/projects"     element={<ProjectsPage />} />
                  <Route path="/projects/:id" element={<ProjectDetailPage />} />
                  <Route path="/settings"     element={<SettingsPage />} />
                  <Route path="/heartbeat"    element={<HeartbeatPage />} />
                  <Route path="/diary"        element={<DiaryPage />} />
                  <Route path="/memory"       element={<MemoryPage />} />
                </Route>
              </Route>

              <Route path="*" element={<NotFoundPage />} />
            </Routes>
            </ToastProvider>
          </AuthProvider>
        </BrowserRouter>
      </ThemeProvider>
    </ErrorBoundary>
  )
}

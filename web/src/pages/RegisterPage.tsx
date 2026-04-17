import { type FormEvent, useState } from 'react'
import { Link } from 'react-router-dom'
import { Mail, Lock, User } from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { ApiError } from '@/api/client'

export function RegisterPage() {
  const { register } = useAuth()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    if (password.length < 6) {
      setError('Пароль должен быть минимум 6 символов')
      return
    }
    setLoading(true)
    try {
      await register(email, password, name)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Ошибка регистрации')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex items-center justify-center min-h-full bg-[var(--bg-primary)] px-4">
      <div className="w-full max-w-sm animate-fade-in">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-[var(--accent)]/80 backdrop-blur-lg border border-white/15 shadow-[inset_0_1px_0_rgba(255,255,255,0.2)] mb-4">
            <span className="text-white text-xl font-bold">N</span>
          </div>
          <h1 className="text-xl font-semibold text-[var(--text-primary)]">Создать аккаунт</h1>
          <p className="text-sm text-[var(--text-muted)] mt-1">Neura AI Platform</p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <Input
            label="Имя"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Ваше имя"
            autoComplete="name"
            required
            leftIcon={<User size={14} />}
          />
          <Input
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            autoComplete="email"
            required
            leftIcon={<Mail size={14} />}
          />
          <Input
            label="Пароль"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Минимум 6 символов"
            autoComplete="new-password"
            required
            leftIcon={<Lock size={14} />}
            hint="Минимум 6 символов"
          />

          {error && (
            <p className="text-sm text-red-400 text-center bg-red-500/10 border border-red-500/20 rounded-md px-3 py-2">
              {error}
            </p>
          )}

          <Button type="submit" loading={loading} className="w-full mt-1">
            Зарегистрироваться
          </Button>
        </form>

        <p className="text-center text-sm text-[var(--text-muted)] mt-6">
          Уже есть аккаунт?{' '}
          <Link to="/login" className="text-[var(--accent)] hover:text-[var(--accent-light)] transition-colors">
            Войти
          </Link>
        </p>
      </div>
    </div>
  )
}

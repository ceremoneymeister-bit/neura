import { type FormEvent, useState } from 'react'
import { Link } from 'react-router-dom'
import { Mail, Lock } from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { ApiError } from '@/api/client'

export function LoginPage() {
  const { login } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await login(email, password)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Ошибка входа')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex items-center justify-center min-h-full bg-[#0a0a0a] px-4">
      <div className="w-full max-w-sm animate-fade-in">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-[12px] bg-[#7c3aed] mb-4">
            <span className="text-white text-xl font-bold">N</span>
          </div>
          <h1 className="text-xl font-semibold text-[#f5f5f5]">Neura</h1>
          <p className="text-sm text-[#525252] mt-1">Войдите в свой аккаунт</p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
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
            placeholder="••••••"
            autoComplete="current-password"
            required
            leftIcon={<Lock size={14} />}
          />

          {error && (
            <p className="text-sm text-red-400 text-center bg-red-500/10 border border-red-500/20 rounded-[6px] px-3 py-2">
              {error}
            </p>
          )}

          <Button type="submit" loading={loading} className="w-full mt-1">
            Войти
          </Button>
        </form>

        <p className="text-center text-sm text-[#525252] mt-6">
          Нет аккаунта?{' '}
          <Link to="/register" className="text-[#7c3aed] hover:text-[#a78bfa] transition-colors">
            Зарегистрироваться
          </Link>
        </p>
      </div>
    </div>
  )
}

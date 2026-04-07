import { type FormEvent, useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { Mail, Lock } from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { ApiError } from '@/api/client'
import { motion } from 'framer-motion'

/* ── Typing demo conversations ─────────────────────────── */
const DEMO_CONVERSATIONS = [
  [
    { role: 'user', text: 'Напиши КП для клиента — квартира 80м\u00B2, современный стиль' },
    { role: 'agent', text: 'Готово! Коммерческое предложение на 2 страницы с расч\u0451том и визуализацией.' },
  ],
  [
    { role: 'user', text: 'Проанализируй продажи за март' },
    { role: 'agent', text: 'Выручка +23% к февралю. Топ-продукт: консультация (42%). Рекомендую увеличить слоты.' },
  ],
  [
    { role: 'user', text: 'Сделай пост для канала из этого голосового' },
    { role: 'agent', text: 'Пост готов, 280 символов. Добавила хештеги и CTA. Опубликовать?' },
  ],
]

const TAGS = ['Понимает контекст', 'Работает с файлами', '24/7']

/* ── Animated fluid orbs (Canvas) ──────────────────────── */
function useOrbCanvas(canvasRef: React.RefObject<HTMLCanvasElement | null>) {
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let animId = 0
    let t = 0
    const mouse = { x: 0.5, y: 0.5 }

    const orbs = [
      { cx: 0.35, cy: 0.4, rx: 0.2, ry: 0.15, phX: 0, phY: 1.2, spX: 0.3, spY: 0.2, rr: 0.4, r: 99, g: 102, b: 241, a: 0.25 },
      { cx: 0.65, cy: 0.6, rx: 0.15, ry: 0.2, phX: 2.1, phY: 0, spX: 0.25, spY: 0.35, rr: 0.35, r: 139, g: 92, b: 246, a: 0.2 },
      { cx: 0.5, cy: 0.3, rx: 0.22, ry: 0.12, phX: 1.0, phY: 3.0, spX: 0.2, spY: 0.3, rr: 0.28, r: 79, g: 70, b: 229, a: 0.15 },
      { cx: 0.3, cy: 0.7, rx: 0.12, ry: 0.18, phX: 3.5, phY: 1.8, spX: 0.35, spY: 0.22, rr: 0.25, r: 167, g: 139, b: 250, a: 0.18 },
    ]

    const resize = () => {
      const dpr = window.devicePixelRatio || 1
      const rect = canvas.getBoundingClientRect()
      canvas.width = rect.width * dpr
      canvas.height = rect.height * dpr
      ctx.scale(dpr, dpr)
    }
    resize()
    window.addEventListener('resize', resize)

    const onMouse = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect()
      mouse.x = (e.clientX - rect.left) / rect.width
      mouse.y = (e.clientY - rect.top) / rect.height
    }
    canvas.addEventListener('mousemove', onMouse)

    const render = () => {
      t += 0.012
      const w = canvas.getBoundingClientRect().width
      const h = canvas.getBoundingClientRect().height
      ctx.clearRect(0, 0, w, h)

      for (const o of orbs) {
        const x = (o.cx + Math.sin(t * o.spX + o.phX) * o.rx + (mouse.x - 0.5) * 0.04) * w
        const y = (o.cy + Math.cos(t * o.spY + o.phY) * o.ry + (mouse.y - 0.5) * 0.04) * h
        const rad = o.rr * Math.min(w, h)

        const grad = ctx.createRadialGradient(x, y, 0, x, y, rad)
        grad.addColorStop(0, `rgba(${o.r},${o.g},${o.b},${o.a})`)
        grad.addColorStop(0.5, `rgba(${o.r},${o.g},${o.b},${o.a * 0.4})`)
        grad.addColorStop(1, `rgba(${o.r},${o.g},${o.b},0)`)
        ctx.fillStyle = grad
        ctx.beginPath()
        ctx.arc(x, y, rad, 0, Math.PI * 2)
        ctx.fill()
      }
      animId = requestAnimationFrame(render)
    }
    render()

    return () => {
      cancelAnimationFrame(animId)
      window.removeEventListener('resize', resize)
      canvas.removeEventListener('mousemove', onMouse)
    }
  }, [canvasRef])
}

/* ── Typing demo component ─────────────────────────────── */
function TypingDemo() {
  const [msgs, setMsgs] = useState<{ role: string; text: string; typed: string }[]>([])
  const convRef = useRef(0)
  const msgRef = useRef(0)
  const charRef = useRef(0)

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>

    const tick = () => {
      const conv = DEMO_CONVERSATIONS[convRef.current % DEMO_CONVERSATIONS.length]
      const msg = conv[msgRef.current]
      if (!msg) {
        // Next conversation
        convRef.current++
        msgRef.current = 0
        charRef.current = 0
        setMsgs([])
        timer = setTimeout(tick, 1500)
        return
      }

      charRef.current++
      const typed = msg.text.slice(0, charRef.current)

      setMsgs((prev) => {
        const existing = prev.findIndex(
          (m) => m.role === msg.role && m.text === msg.text,
        )
        if (existing >= 0) {
          const updated = [...prev]
          updated[existing] = { ...msg, typed }
          return updated
        }
        return [...prev, { ...msg, typed }]
      })

      if (charRef.current >= msg.text.length) {
        // Next message
        msgRef.current++
        charRef.current = 0
        timer = setTimeout(tick, 1200)
      } else {
        timer = setTimeout(tick, 25)
      }
    }
    timer = setTimeout(tick, 800)
    return () => clearTimeout(timer)
  }, [])

  return (
    <div className="w-full max-w-sm rounded-xl border border-white/10 bg-white/5 backdrop-blur-sm overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-white/10">
        <span className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_6px_#34d399]" />
        <span className="text-xs text-white/50 font-medium">Neura Agent</span>
      </div>
      <div className="px-4 py-3 space-y-2.5 min-h-[100px]">
        {msgs.map((m, i) => (
          <div
            key={`${convRef.current}-${i}`}
            className={`text-xs leading-relaxed ${
              m.role === 'user' ? 'text-white/40' : 'text-white/70'
            }`}
          >
            <span className="text-[10px] text-white/25 mr-1.5">
              {m.role === 'user' ? 'Вы' : 'AI'}
            </span>
            {m.typed}
            {m.typed.length < m.text.length && (
              <span className="inline-block w-[2px] h-3.5 bg-[var(--accent-light)] ml-0.5 animate-pulse align-middle" />
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

/* ── Login Page ────────────────────────────────────────── */
export function LoginPage() {
  const { login } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useOrbCanvas(canvasRef)

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
    <div className="flex min-h-screen">
      {/* ── Left: Hero panel ── */}
      <div className="hidden md:flex w-1/2 relative bg-[#0a0a14] flex-col items-center justify-center p-12 overflow-hidden">
        <canvas
          ref={canvasRef}
          className="absolute inset-0 w-full h-full"
          style={{ zIndex: 0 }}
        />

        <div className="relative z-10 flex flex-col items-center text-center max-w-md">
          <motion.h1
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: [0.4, 0, 0.2, 1] }}
            className="text-5xl font-extrabold tracking-tight mb-5"
            style={{
              background: 'linear-gradient(135deg, #fff 20%, #c4b5fd 60%, #818cf8 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            Neura
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.15, ease: [0.4, 0, 0.2, 1] }}
            className="text-base text-white/50 leading-relaxed mb-6"
          >
            AI-агент, который знает ваш бизнес
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.3, ease: [0.4, 0, 0.2, 1] }}
            className="flex flex-wrap gap-2 justify-center mb-8"
          >
            {TAGS.map((tag) => (
              <span
                key={tag}
                className="px-3 py-1 rounded-full text-xs font-medium bg-[var(--accent)]/10 border border-[var(--accent)]/20 text-white/60"
              >
                {tag}
              </span>
            ))}
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.45, ease: [0.4, 0, 0.2, 1] }}
          >
            <TypingDemo />
          </motion.div>
        </div>
      </div>

      {/* ── Right: Auth form ── */}
      <div className="flex-1 flex items-center justify-center bg-[var(--bg-primary)] px-6">
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.1 }}
          className="w-full max-w-sm"
        >
          {/* Logo (mobile only — desktop has hero) */}
          <div className="text-center mb-8">
            <div className="md:hidden inline-flex items-center justify-center w-12 h-12 rounded-xl bg-[var(--accent)] mb-4">
              <span className="text-white text-xl font-bold">N</span>
            </div>
            <h1 className="text-xl font-semibold text-[var(--text-primary)]">
              <span className="hidden md:inline">Вход в Neura</span>
              <span className="md:hidden">Neura</span>
            </h1>
            <p className="text-sm text-[var(--text-muted)] mt-1">Войдите в свой аккаунт</p>
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
              placeholder="Введите пароль"
              autoComplete="current-password"
              required
              leftIcon={<Lock size={14} />}
            />

            {error && (
              <p className="text-sm text-red-400 text-center bg-red-500/10 border border-red-500/20 rounded-md px-3 py-2">
                {error}
              </p>
            )}

            <Button type="submit" loading={loading} className="w-full mt-1 !rounded-xl !py-3">
              Войти
            </Button>
          </form>

          <p className="text-center text-sm text-[var(--text-muted)] mt-6">
            Нет аккаунта?{' '}
            <Link to="/register" className="text-[var(--accent)] hover:text-[var(--accent-light)] transition-colors">
              Зарегистрироваться
            </Link>
          </p>

          <p className="text-center text-[10px] text-[var(--text-muted)]/50 mt-8">
            Neura v2.0 &middot; AI Agent Platform
          </p>
        </motion.div>
      </div>
    </div>
  )
}

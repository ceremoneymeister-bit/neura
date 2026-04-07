import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/Button'
import { Home } from 'lucide-react'

export function NotFoundPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-full gap-4 text-center px-4">
      <p className="text-6xl font-bold text-[var(--bg-card)]">404</p>
      <h1 className="text-xl font-semibold text-[var(--text-primary)]">Страница не найдена</h1>
      <p className="text-sm text-[var(--text-muted)]">Возможно, ссылка устарела или страница была удалена</p>
      <Link to="/">
        <Button icon={<Home size={14} />}>На главную</Button>
      </Link>
    </div>
  )
}

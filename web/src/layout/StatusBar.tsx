import { useBrandTheme } from '@/hooks/useBrandTheme'

export function StatusBar() {
  const { brandName } = useBrandTheme()
  return (
    <div className="flex items-center justify-center px-4 h-7 text-xs text-[var(--text-muted)] shrink-0 select-none">
      {brandName} — AI-помощник. Проверяйте ответы.
    </div>
  )
}

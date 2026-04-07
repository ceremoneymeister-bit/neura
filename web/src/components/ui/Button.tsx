import { type ButtonHTMLAttributes, type ReactNode } from 'react'
import { Spinner } from './Spinner'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger'
type Size = 'sm' | 'md' | 'lg'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  loading?: boolean
  icon?: ReactNode
  children?: ReactNode
}

const base =
  'inline-flex items-center justify-center gap-2 font-medium transition-all duration-150 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed select-none cursor-pointer active:scale-[0.97]'

const variants: Record<Variant, string> = {
  primary:   'bg-[var(--accent)] text-white hover:bg-[var(--accent-hover)] active:bg-[#5b21b6]',
  secondary: 'bg-[var(--bg-input)] text-[var(--text-primary)] border border-[var(--border)] hover:bg-[var(--bg-hover)] active:bg-[var(--bg-card)]',
  ghost:     'text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)] active:bg-[var(--border)]',
  danger:    'bg-red-600/15 text-red-400 border border-red-600/30 hover:bg-red-600/25 active:bg-red-600/35',
}

const sizes: Record<Size, string> = {
  sm: 'h-7 px-3 text-xs',
  md: 'h-9 px-4 text-sm',
  lg: 'h-11 px-6 text-base',
}

export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  icon,
  children,
  disabled,
  className = '',
  ...rest
}: ButtonProps) {
  return (
    <button
      {...rest}
      disabled={disabled ?? loading}
      className={`${base} ${variants[variant]} ${sizes[size]} ${className}`}
    >
      {loading ? <Spinner size="sm" /> : icon}
      {children}
    </button>
  )
}

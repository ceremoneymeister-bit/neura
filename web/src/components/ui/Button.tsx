import { type ButtonHTMLAttributes, type ReactNode } from 'react'
import { Spinner } from './Spinner'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'glass'
type Size = 'sm' | 'md' | 'lg'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  loading?: boolean
  icon?: ReactNode
  children?: ReactNode
}

const base =
  'inline-flex items-center justify-center gap-2 font-medium transition-all duration-150 rounded-full disabled:opacity-50 disabled:cursor-not-allowed select-none cursor-pointer active:scale-[0.97]'

const variants: Record<Variant, string> = {
  primary:   'relative overflow-hidden bg-[var(--accent)]/80 text-white backdrop-blur-lg border border-white/15 shadow-[inset_0_1px_0_rgba(255,255,255,0.2),0_2px_8px_rgba(0,0,0,0.12)] hover:bg-[var(--accent)]/90 hover:shadow-[inset_0_1px_0_rgba(255,255,255,0.25),0_4px_12px_rgba(0,0,0,0.15)] active:bg-[var(--accent)]',
  secondary: 'liquid-glass-btn text-[var(--text-primary)]',
  ghost:     'text-[var(--text-secondary)] hover:text-[var(--text-primary)] liquid-glass-nav',
  danger:    'relative overflow-hidden bg-red-600/15 text-red-400 backdrop-blur-lg border border-red-400/20 shadow-[inset_0_1px_0_rgba(255,255,255,0.05)] hover:bg-red-600/25 active:bg-red-600/35',
  glass:     'liquid-glass-btn text-[var(--text-primary)]',
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

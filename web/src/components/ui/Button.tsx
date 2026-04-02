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
  'inline-flex items-center justify-center gap-2 font-medium transition-all duration-150 rounded-[6px] disabled:opacity-50 disabled:cursor-not-allowed select-none cursor-pointer'

const variants: Record<Variant, string> = {
  primary:   'bg-[#7c3aed] text-white hover:bg-[#6d28d9] active:bg-[#5b21b6]',
  secondary: 'bg-[#1e1e1e] text-[#f5f5f5] border border-[#262626] hover:bg-[#2a2a2a] active:bg-[#333]',
  ghost:     'text-[#a3a3a3] hover:bg-[#1a1a1a] hover:text-[#f5f5f5] active:bg-[#262626]',
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

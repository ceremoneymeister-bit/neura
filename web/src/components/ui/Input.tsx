import { type InputHTMLAttributes, type ReactNode, forwardRef } from 'react'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  hint?: string
  leftIcon?: ReactNode
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  function Input({ label, error, hint, leftIcon, className = '', id, ...rest }, ref) {
    const inputId = id ?? (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined)
    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label htmlFor={inputId} className="text-xs font-medium text-[#a3a3a3]">
            {label}
          </label>
        )}
        <div className="relative">
          {leftIcon && (
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-[#525252]">
              {leftIcon}
            </span>
          )}
          <input
            {...rest}
            ref={ref}
            id={inputId}
            className={[
              'w-full rounded-[6px] bg-[#1e1e1e] border border-[#262626] text-[#f5f5f5]',
              'placeholder-[#525252] px-3 py-2 text-sm transition-all duration-150',
              'focus:outline-none focus:border-[#7c3aed] focus:ring-1 focus:ring-[#7c3aed]/30',
              error ? 'border-red-500/70 focus:border-red-500 focus:ring-red-500/20' : '',
              leftIcon ? 'pl-9' : '',
              className,
            ].join(' ')}
          />
        </div>
        {error && <p className="text-xs text-red-400">{error}</p>}
        {hint && !error && <p className="text-xs text-[#525252]">{hint}</p>}
      </div>
    )
  },
)

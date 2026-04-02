import { useEffect, useRef } from 'react'
import { Search, X } from 'lucide-react'

interface SearchBarProps {
  value: string
  onChange: (v: string) => void
  placeholder?: string
}

export function SearchBar({ value, onChange, placeholder = 'Поиск...' }: SearchBarProps) {
  const inputRef = useRef<HTMLInputElement>(null)

  // Listen for Ctrl+K custom event dispatched from App.tsx
  useEffect(() => {
    const handler = () => inputRef.current?.focus()
    document.addEventListener('neura:search-focus', handler)
    return () => document.removeEventListener('neura:search-focus', handler)
  }, [])

  return (
    <div className="relative">
      <Search
        size={12}
        className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[#525252] pointer-events-none"
      />
      <input
        ref={inputRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full h-7 pl-7 pr-6 rounded-[6px] bg-[#1a1a1a] border border-[#262626] text-xs text-[#f5f5f5] placeholder-[#525252] focus:outline-none focus:border-[#7c3aed]/50 transition-colors"
      />
      {value && (
        <button
          onClick={() => onChange('')}
          className="absolute right-2 top-1/2 -translate-y-1/2 text-[#525252] hover:text-[#a3a3a3] transition-colors"
          title="Очистить"
        >
          <X size={11} />
        </button>
      )}
    </div>
  )
}

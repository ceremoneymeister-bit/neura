type Size = 'sm' | 'md' | 'lg'

const sizes: Record<Size, string> = {
  sm: 'w-3.5 h-3.5 border-2',
  md: 'w-5 h-5 border-2',
  lg: 'w-8 h-8 border-3',
}

export function Spinner({ size = 'md', className = '' }: { size?: Size; className?: string }) {
  return (
    <span
      className={`inline-block rounded-full border-[#7c3aed] border-t-transparent animate-spin ${sizes[size]} ${className}`}
      role="status"
      aria-label="Loading"
    />
  )
}

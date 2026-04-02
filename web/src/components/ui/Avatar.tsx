interface AvatarProps {
  name?: string
  src?: string
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

const sizes = {
  sm: 'w-6 h-6 text-[10px]',
  md: 'w-8 h-8 text-xs',
  lg: 'w-10 h-10 text-sm',
}

function initials(name: string): string {
  return name
    .split(' ')
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? '')
    .join('')
}

function colorFromName(name: string): string {
  const colors = [
    'bg-violet-600', 'bg-blue-600', 'bg-emerald-600',
    'bg-orange-600', 'bg-pink-600', 'bg-cyan-600',
  ]
  let hash = 0
  for (const c of name) hash = (hash * 31 + c.charCodeAt(0)) % colors.length
  return colors[hash] ?? 'bg-violet-600'
}

export function Avatar({ name = '', src, size = 'md', className = '' }: AvatarProps) {
  if (src) {
    return (
      <img
        src={src}
        alt={name}
        className={`rounded-full object-cover ${sizes[size]} ${className}`}
      />
    )
  }
  return (
    <span
      className={`inline-flex items-center justify-center rounded-full font-semibold text-white ${colorFromName(name)} ${sizes[size]} ${className}`}
      title={name}
    >
      {initials(name) || '?'}
    </span>
  )
}

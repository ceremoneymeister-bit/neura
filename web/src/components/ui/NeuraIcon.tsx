interface IconProps {
  size?: number
  className?: string
}

export function NeuraIcon({ size = 28 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none">
      <defs>
        <linearGradient id="neura-grad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#7c3aed" />
          <stop offset="100%" stopColor="#a78bfa" />
        </linearGradient>
      </defs>
      <rect width="32" height="32" rx="8" fill="url(#neura-grad)" opacity="0.15" />
      <text
        x="16"
        y="22"
        textAnchor="middle"
        fill="url(#neura-grad)"
        fontSize="18"
        fontWeight="700"
        fontFamily="Inter, sans-serif"
      >
        N
      </text>
    </svg>
  )
}

/** Animated thinking indicator — pulsing orbital dots */
export function NeuraThinking({ size = 28 }: IconProps) {
  const r = size / 2
  const dotR = size * 0.06
  const orbit = size * 0.3
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} fill="none">
      <defs>
        <linearGradient id="neura-think-grad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#7c3aed" />
          <stop offset="100%" stopColor="#a78bfa" />
        </linearGradient>
      </defs>
      {/* Center glow */}
      <circle cx={r} cy={r} r={size * 0.15} fill="url(#neura-think-grad)" opacity="0.2">
        <animate attributeName="opacity" values="0.15;0.35;0.15" dur="2s" repeatCount="indefinite" />
      </circle>
      {/* Orbiting dots */}
      {[0, 1, 2].map((i) => (
        <circle key={i} cx={r} cy={r} r={dotR} fill="url(#neura-think-grad)">
          <animateTransform
            attributeName="transform"
            type="rotate"
            from={`${i * 120} ${r} ${r}`}
            to={`${i * 120 + 360} ${r} ${r}`}
            dur="2s"
            repeatCount="indefinite"
          />
          <animate
            attributeName="cx"
            values={`${r};${r + orbit};${r}`}
            dur="2s"
            repeatCount="indefinite"
            begin={`${i * 0.66}s`}
          />
          <animate
            attributeName="opacity"
            values="0.4;1;0.4"
            dur="2s"
            repeatCount="indefinite"
            begin={`${i * 0.66}s`}
          />
        </circle>
      ))}
    </svg>
  )
}

/** Project folder icon — minimalist with brand gradient */
export function ProjectIcon({ size = 16 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none">
      <defs>
        <linearGradient id="proj-grad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#7c3aed" />
          <stop offset="100%" stopColor="#a78bfa" />
        </linearGradient>
      </defs>
      <path
        d="M2 4.5A1.5 1.5 0 013.5 3h3l1.5 1.5h4.5A1.5 1.5 0 0114 6v5.5a1.5 1.5 0 01-1.5 1.5h-9A1.5 1.5 0 012 11.5V4.5z"
        stroke="url(#proj-grad)"
        strokeWidth="1.2"
        fill="url(#proj-grad)"
        fillOpacity="0.1"
      />
    </svg>
  )
}

/** Pin icon — brand gradient */
export function PinIcon({ size = 12 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none">
      <defs>
        <linearGradient id="pin-grad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#7c3aed" />
          <stop offset="100%" stopColor="#a78bfa" />
        </linearGradient>
      </defs>
      <path
        d="M9.828 2.172a2 2 0 012.828 0l1.172 1.172a2 2 0 010 2.828L11 9l-1 4-2-2-4.5 4.5L2 14l4.5-4.5-2-2 4-1 2.828-2.828z"
        stroke="url(#pin-grad)"
        strokeWidth="1"
        fill="url(#pin-grad)"
        fillOpacity="0.15"
      />
    </svg>
  )
}

export function NeuraSparkle({ size = 32 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none">
      <defs>
        <linearGradient id="neura-sparkle-grad" x1="0.2" y1="0" x2="0.8" y2="1">
          <stop offset="0%" stopColor="#7c3aed" />
          <stop offset="100%" stopColor="#a78bfa" />
        </linearGradient>
      </defs>
      <path
        d="M16 2 C16.5 10 17 12 22 13.5 C17 15 16.5 17 16 30 C15.5 17 15 15 10 13.5 C15 12 15.5 10 16 2Z"
        fill="url(#neura-sparkle-grad)"
      />
    </svg>
  )
}

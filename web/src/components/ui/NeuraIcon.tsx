interface NeuraIconProps {
  size?: number
}

export function NeuraIcon({ size = 28 }: NeuraIconProps) {
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

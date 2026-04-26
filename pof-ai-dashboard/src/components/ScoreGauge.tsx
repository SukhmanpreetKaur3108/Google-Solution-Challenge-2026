interface Props { score: number; label: string; size?: 'sm' | 'md' | 'lg' }

export default function ScoreGauge({ score, label, size = 'md' }: Props) {
  const pct  = Math.round(score * 100)
  const color = pct >= 80 ? '#22c55e' : pct >= 60 ? '#f59e0b' : '#ef4444'
  const dim   = size === 'sm' ? 72 : size === 'lg' ? 120 : 96
  const r     = dim * 0.38
  const circ  = 2 * Math.PI * r
  const dash  = (pct / 100) * circ

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={dim} height={dim} viewBox={`0 0 ${dim} ${dim}`}>
        <circle cx={dim/2} cy={dim/2} r={r} fill="none" stroke="#374151" strokeWidth={size==='sm'?6:8} />
        <circle
          cx={dim/2} cy={dim/2} r={r} fill="none"
          stroke={color} strokeWidth={size==='sm'?6:8}
          strokeDasharray={`${dash} ${circ - dash}`}
          strokeLinecap="round"
          transform={`rotate(-90 ${dim/2} ${dim/2})`}
          style={{ transition: 'stroke-dasharray 0.8s ease' }}
        />
        <text x="50%" y="50%" textAnchor="middle" dy="0.35em"
          fill={color} fontSize={size==='sm'?16:22} fontWeight="700">
          {pct}%
        </text>
      </svg>
      <span className="text-xs text-gray-400 text-center">{label}</span>
    </div>
  )
}

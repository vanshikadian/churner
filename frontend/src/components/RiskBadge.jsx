export default function RiskBadge({ score }) {
  if (score === null || score === undefined) {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-700 text-slate-400">
        —
      </span>
    )
  }

  let label, colorClass
  if (score < 0.25) {
    label = 'LOW'
    colorClass = 'bg-emerald-900/60 text-emerald-400 ring-1 ring-emerald-700'
  } else if (score < 0.5) {
    label = 'MEDIUM'
    colorClass = 'bg-amber-900/60 text-amber-400 ring-1 ring-amber-700'
  } else if (score < 0.75) {
    label = 'HIGH'
    colorClass = 'bg-orange-900/60 text-orange-400 ring-1 ring-orange-700'
  } else {
    label = 'CRITICAL'
    colorClass = 'bg-red-900/60 text-red-400 ring-1 ring-red-700'
  }

  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-semibold ${colorClass}`}>
      <span className="tabular-nums">{(score * 100).toFixed(0)}%</span>
      <span className="opacity-75">{label}</span>
    </span>
  )
}

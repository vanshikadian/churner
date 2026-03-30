const FEATURE_LABELS = {
  engagement_decay:    'Engagement Decay',
  login_recency:       'Login Recency',
  feature_adoption:    'Feature Adoption',
  support_intensity:   'Support Load',
  payment_reliability: 'Payment Issues',
  plan_value:          'Plan Value',
  engagement_velocity: 'Engagement Trend',
}

const FEATURE_COLORS = {
  engagement_decay:    '#f87171',
  login_recency:       '#fb923c',
  feature_adoption:    '#60a5fa',
  support_intensity:   '#f59e0b',
  payment_reliability: '#e879f9',
  plan_value:          '#34d399',
  engagement_velocity: '#94a3b8',
}

export default function FeatureBreakdown({ riskFactors }) {
  if (!riskFactors || Object.keys(riskFactors).length === 0) return null

  // Top 4 by contribution
  const sorted = Object.entries(riskFactors)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 4)

  const maxVal = sorted[0]?.[1] || 1

  return (
    <div className="mb-4">
      <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider mb-2">
        Risk Factors
      </p>
      <div className="space-y-2">
        {sorted.map(([key, val]) => {
          const pct = Math.round((val / maxVal) * 100)
          const label = FEATURE_LABELS[key] || key.replace(/_/g, ' ')
          const color = FEATURE_COLORS[key] || '#64748b'
          return (
            <div key={key}>
              <div className="flex justify-between items-center mb-0.5">
                <span className="text-xs text-slate-300">{label}</span>
                <span className="text-xs text-slate-400 tabular-nums">{Math.round(val * 100)}%</span>
              </div>
              <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-300"
                  style={{ width: `${pct}%`, backgroundColor: color }}
                />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

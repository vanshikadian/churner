import { useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from 'recharts'

const CONFIDENCE_STYLES = {
  low:    'bg-slate-700 text-slate-400',
  medium: 'bg-amber-900/50 text-amber-400',
  high:   'bg-emerald-900/50 text-emerald-400',
}

const chartTooltipStyle = {
  backgroundColor: '#1e293b',
  border: '1px solid #334155',
  borderRadius: '8px',
  color: '#f1f5f9',
  fontSize: '11px',
}

function SegmentPanel({ segment, offers }) {
  const sorted = [...offers].sort((a, b) => b.estimated_success_rate - a.estimated_success_rate)
  const chartData = sorted.map((o) => ({
    name: o.offer_type.replace(/_/g, ' '),
    rate: Math.round(o.estimated_success_rate * 100),
    trials: o.total_trials,
    confidence: o.confidence,
  }))

  return (
    <div className="bg-slate-900/50 rounded-xl p-4 border border-slate-700/50">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold text-slate-200 capitalize">
          {segment.replace(/_/g, ' ')}
        </h4>
        <span className="text-xs text-slate-500">
          {offers.reduce((s, o) => s + o.total_trials, 0)} trials
        </span>
      </div>

      {chartData.length > 0 && (
        <ResponsiveContainer width="100%" height={100}>
          <BarChart data={chartData} margin={{ top: 0, right: 0, left: -25, bottom: 0 }}>
            <XAxis
              dataKey="name"
              tick={{ fill: '#64748b', fontSize: 9 }}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              tick={{ fill: '#64748b', fontSize: 9 }}
              tickLine={false}
              axisLine={false}
              domain={[0, 100]}
              tickFormatter={(v) => `${v}%`}
            />
            <Tooltip
              contentStyle={chartTooltipStyle}
              formatter={(v, _, props) => [
                `${v}% success (${props.payload.trials} trials)`,
                'Est. Rate',
              ]}
              cursor={{ fill: 'rgba(255,255,255,0.04)' }}
            />
            <ReferenceLine y={50} stroke="#334155" strokeDasharray="3 3" />
            <Bar dataKey="rate" radius={[3, 3, 0, 0]} maxBarSize={30}>
              {chartData.map((entry, i) => (
                <Cell
                  key={i}
                  fill={i === 0 ? '#34d399' : '#475569'}
                  opacity={entry.trials === 0 ? 0.4 : 1}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}

      <div className="mt-2 flex flex-wrap gap-1">
        {sorted.map((o) => (
          <span
            key={o.offer_type}
            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs ${CONFIDENCE_STYLES[o.confidence] || CONFIDENCE_STYLES.low}`}
          >
            {o.offer_type.replace(/_/g, ' ')}
            <span className="opacity-60">· {o.total_trials}t</span>
          </span>
        ))}
      </div>
    </div>
  )
}

export default function BanditInsights({ banditState }) {
  const [open, setOpen] = useState(false)

  if (!banditState || Object.keys(banditState).length === 0) return null

  const segments = Object.entries(banditState).filter(([, offers]) => offers.length > 0)
  const totalTrials = segments.reduce(
    (sum, [, offers]) => sum + offers.reduce((s, o) => s + o.total_trials, 0),
    0
  )

  return (
    <div className="bg-slate-800 rounded-xl border border-slate-700 mb-6">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full px-6 py-4 flex items-center justify-between text-left hover:bg-slate-700/30 transition-colors rounded-xl"
      >
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-purple-400 animate-pulse" />
          <div>
            <h3 className="text-sm font-semibold text-white">Thompson Sampling — Bandit Insights</h3>
            <p className="text-xs text-slate-400 mt-0.5">
              {totalTrials === 0
                ? 'No trials yet — bandit is in exploration mode'
                : `${totalTrials} trials · bandit learning which offers work best`}
            </p>
          </div>
        </div>
        <span className="text-slate-500 text-lg">{open ? '−' : '+'}</span>
      </button>

      {open && (
        <div className="px-6 pb-6">
          <p className="text-xs text-slate-500 mb-4">
            Each bar shows estimated success rate for that offer in this segment. The bandit samples from Beta distributions —
            early on all offers get equal exploration; over time winning offers get exploited more.
            Green bar = current best estimate.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {segments.map(([segment, offers]) => (
              <SegmentPanel key={segment} segment={segment} offers={offers} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

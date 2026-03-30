import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from 'recharts'
import BanditInsights from './BanditInsights'

const chartTooltipStyle = {
  backgroundColor: '#1e293b',
  border: '1px solid #334155',
  borderRadius: '8px',
  color: '#f1f5f9',
  fontSize: '12px',
}

const SEGMENT_COLORS = [
  '#f59e0b', '#60a5fa', '#f87171', '#94a3b8', '#fb923c',
  '#34d399', '#e879f9', '#a78bfa',
]

const OFFER_COLORS = [
  '#60a5fa', '#34d399', '#f59e0b', '#f87171', '#a78bfa',
  '#fb923c', '#94a3b8', '#e879f9',
]

function StatCard({ label, value, sub, accent }) {
  const accentClass = {
    emerald: 'text-emerald-400',
    amber:   'text-amber-400',
    blue:    'text-blue-400',
    purple:  'text-purple-400',
    green:   'text-green-400',
    orange:  'text-orange-400',
  }[accent] || 'text-white'

  return (
    <div className="bg-slate-800 rounded-xl border border-slate-700 p-5">
      <p className="text-sm text-slate-400 mb-1">{label}</p>
      <p className={`text-3xl font-bold ${accentClass}`}>{value}</p>
      {sub && <p className="text-xs text-slate-500 mt-1">{sub}</p>}
    </div>
  )
}

export default function AnalyticsDashboard({ analytics, vertical }) {
  if (!analytics) {
    return (
      <div className="grid grid-cols-4 gap-4 mb-6">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="bg-slate-800 rounded-xl border border-slate-700 p-5 animate-pulse">
            <div className="h-3 bg-slate-700 rounded w-24 mb-3" />
            <div className="h-8 bg-slate-700 rounded w-16" />
          </div>
        ))}
      </div>
    )
  }

  const accentColor = vertical?.accent_color || 'emerald'
  const retentionPct = (analytics.retention_rate * 100).toFixed(1)
  const revenueSaved = analytics.total_revenue_saved.toLocaleString('en-US', {
    style: 'currency', currency: 'USD', maximumFractionDigits: 0,
  })
  const revenueAtRisk = analytics.total_revenue_at_risk.toLocaleString('en-US', {
    style: 'currency', currency: 'USD', maximumFractionDigits: 0,
  })

  const segmentData = Object.entries(analytics.by_segment || {}).map(([seg, stats], i) => ({
    name: seg.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
    key: seg,
    rate: stats.count > 0 ? Math.round((stats.retained / stats.count) * 100) : 0,
    color: SEGMENT_COLORS[i % SEGMENT_COLORS.length],
  }))

  const offerData = Object.entries(analytics.by_offer_type || {}).map(([type, stats], i) => ({
    name: type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
    key: type,
    rate: Math.round(stats.acceptance_rate * 100),
    count: stats.count,
    color: OFFER_COLORS[i % OFFER_COLORS.length],
  }))

  return (
    <div className="mb-6 space-y-4">
      {/* Stat cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="Total Interventions"
          value={analytics.total_interventions}
          sub={`${analytics.total_users} users tracked`}
          accent="blue"
        />
        <StatCard
          label="Retention Rate"
          value={`${retentionPct}%`}
          sub="of responded interventions"
          accent={accentColor}
        />
        <StatCard
          label="Revenue Saved"
          value={revenueSaved}
          sub="6-month projected"
          accent={accentColor}
        />
        <StatCard
          label="Active Users"
          value={analytics.active_users}
          sub={`${revenueAtRisk} at risk`}
          accent="amber"
        />
      </div>

      {/* Bandit insights */}
      <BanditInsights banditState={analytics.bandit_state} />

      {/* Charts */}
      {(segmentData.length > 0 || offerData.length > 0) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-slate-800 rounded-xl border border-slate-700 p-5">
            <h3 className="text-sm font-semibold text-slate-300 mb-4">Retention Rate by Segment</h3>
            {segmentData.length === 0 ? (
              <p className="text-slate-500 text-sm text-center py-8">No interventions yet</p>
            ) : (
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={segmentData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                  <XAxis
                    dataKey="name"
                    tick={{ fill: '#94a3b8', fontSize: 9 }}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis
                    tick={{ fill: '#94a3b8', fontSize: 10 }}
                    tickLine={false}
                    axisLine={false}
                    domain={[0, 100]}
                    tickFormatter={(v) => `${v}%`}
                  />
                  <Tooltip
                    contentStyle={chartTooltipStyle}
                    formatter={(v) => [`${v}%`, 'Retention Rate']}
                    cursor={{ fill: 'rgba(255,255,255,0.04)' }}
                  />
                  <Bar dataKey="rate" radius={[4, 4, 0, 0]} maxBarSize={40}>
                    {segmentData.map((entry) => (
                      <Cell key={entry.key} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>

          <div className="bg-slate-800 rounded-xl border border-slate-700 p-5">
            <h3 className="text-sm font-semibold text-slate-300 mb-4">Offer Acceptance Rate</h3>
            {offerData.length === 0 ? (
              <p className="text-slate-500 text-sm text-center py-8">No interventions yet</p>
            ) : (
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={offerData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                  <XAxis
                    dataKey="name"
                    tick={{ fill: '#94a3b8', fontSize: 9 }}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis
                    tick={{ fill: '#94a3b8', fontSize: 10 }}
                    tickLine={false}
                    axisLine={false}
                    domain={[0, 100]}
                    tickFormatter={(v) => `${v}%`}
                  />
                  <Tooltip
                    contentStyle={chartTooltipStyle}
                    formatter={(v, _, props) => [`${v}% (${props.payload.count} trials)`, 'Accept Rate']}
                    cursor={{ fill: 'rgba(255,255,255,0.04)' }}
                  />
                  <Bar dataKey="rate" radius={[4, 4, 0, 0]} maxBarSize={40}>
                    {offerData.map((entry) => (
                      <Cell key={entry.key} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

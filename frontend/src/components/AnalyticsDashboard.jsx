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

function RecentInterventions({ items = [] }) {
  if (items.length === 0) {
    return (
      <div className="bg-slate-800 rounded-xl border border-slate-700 p-5">
        <h3 className="text-sm font-semibold text-slate-300 mb-3">Recent Interventions</h3>
        <p className="text-slate-500 text-sm">No interventions yet</p>
      </div>
    )
  }

  const outcomeStyle = {
    pending: 'bg-amber-900/40 text-amber-300 border-amber-700/50',
    accepted: 'bg-emerald-900/40 text-emerald-300 border-emerald-700/50',
    rejected: 'bg-red-900/40 text-red-300 border-red-700/50',
  }

  return (
    <div className="bg-slate-800 rounded-xl border border-slate-700 p-5">
      <div className="flex items-center justify-between mb-3 gap-3">
        <h3 className="text-sm font-semibold text-slate-300">Recent Interventions</h3>
        <span className="text-xs text-slate-500">Pending shows up immediately after simulate</span>
      </div>
      <div className="space-y-2">
        {items.map((item) => (
          <div
            key={item.id}
            className="flex items-center justify-between gap-3 rounded-lg border border-slate-700/60 bg-slate-900/40 px-3 py-2"
          >
            <div className="min-w-0">
              <p className="text-sm text-white truncate">{item.user_name}</p>
              <p className="text-xs text-slate-400 truncate">
                {item.segment.replace(/_/g, ' ')} · {item.offer_type.replace(/_/g, ' ')}
              </p>
            </div>
            <span className={`shrink-0 rounded-full border px-2 py-0.5 text-xs capitalize ${outcomeStyle[item.outcome] || 'bg-slate-700 text-slate-300 border-slate-600'}`}>
              {item.outcome}
            </span>
          </div>
        ))}
      </div>
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
      <div className="grid grid-cols-2 xl:grid-cols-6 gap-4">
        <StatCard
          label="Total Interventions"
          value={analytics.total_interventions}
          sub={`${analytics.total_users} users tracked`}
          accent="blue"
        />
        <StatCard
          label="Pending"
          value={analytics.pending_interventions}
          sub="awaiting accept/reject"
          accent="amber"
        />
        <StatCard
          label="Responded"
          value={analytics.responded_interventions}
          sub={`${analytics.accepted_interventions} accepted`}
          accent="purple"
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
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <RecentInterventions items={analytics.recent_interventions} />
        {(segmentData.length > 0 || offerData.length > 0) && (
          <>
          <div className="bg-slate-800 rounded-xl border border-slate-700 p-5">
            <h3 className="text-sm font-semibold text-slate-300 mb-4">Retention Rate by Segment</h3>
            <p className="text-xs text-slate-500 mb-3">
              These charts move after you accept or reject the offer. Pending cancels are tracked above.
            </p>
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
          </>
        )}
      </div>
    </div>
  )
}

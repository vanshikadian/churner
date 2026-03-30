import { useState } from 'react'
import RiskBadge from './RiskBadge'

const STATUS_STYLES = {
  active:   'bg-emerald-900/50 text-emerald-400',
  retained: 'bg-blue-900/50 text-blue-400',
  churned:  'bg-red-900/50 text-red-400',
  paused:   'bg-slate-700 text-slate-400',
}

const PLAN_COLORS = {
  free:         'text-slate-400',
  starter:      'text-blue-400',
  basic:        'text-slate-400',
  basic_ads:    'text-slate-400',
  pro:          'text-purple-400',
  plus:         'text-purple-400',
  standard:     'text-blue-400',
  premium:      'text-amber-400',
  enterprise:   'text-amber-400',
  family:       'text-emerald-400',
  dash_pass:    'text-blue-400',
}

function EngagementTrend({ prev, curr }) {
  if (prev === 0 && curr === 0) return <span className="text-slate-600 text-xs">—</span>
  const arrow = curr > prev ? '↑' : curr < prev ? '↓' : '→'
  const color = curr > prev ? 'text-emerald-400' : curr < prev ? 'text-red-400' : 'text-slate-400'
  return (
    <span className="tabular-nums text-sm">
      <span className="text-slate-500">{prev}</span>
      <span className="text-slate-600 mx-1 text-xs">→</span>
      <span className={color}>{curr} {arrow}</span>
    </span>
  )
}

export default function UserTable({ users, onSimulateCancel, loadingUserId, vertical }) {
  const [sortKey, setSortKey] = useState('id')
  const [sortDir, setSortDir] = useState('asc')
  const [search, setSearch] = useState('')

  const handleSort = (key) => {
    if (sortKey === key) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    else { setSortKey(key); setSortDir('asc') }
  }

  const filtered = users.filter((u) =>
    u.name.toLowerCase().includes(search.toLowerCase()) ||
    u.email.toLowerCase().includes(search.toLowerCase()) ||
    (u.plan_tier || '').toLowerCase().includes(search.toLowerCase())
  )

  const sorted = [...filtered].sort((a, b) => {
    let av = a[sortKey] ?? -Infinity
    let bv = b[sortKey] ?? -Infinity
    if (typeof av === 'string') av = av.toLowerCase()
    if (typeof bv === 'string') bv = bv.toLowerCase()
    if (av < bv) return sortDir === 'asc' ? -1 : 1
    if (av > bv) return sortDir === 'asc' ? 1 : -1
    return 0
  })

  const SortIcon = ({ col }) =>
    sortKey !== col
      ? <span className="text-slate-600 ml-1">↕</span>
      : <span className="text-emerald-400 ml-1">{sortDir === 'asc' ? '↑' : '↓'}</span>

  const Th = ({ col, children, className = '' }) => (
    <th
      className={`px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider cursor-pointer hover:text-white select-none ${className}`}
      onClick={() => handleSort(col)}
    >
      {children}<SortIcon col={col} />
    </th>
  )

  const accentBtnClass = {
    emerald: 'bg-red-600 hover:bg-red-500',
    purple:  'bg-red-600 hover:bg-red-500',
    green:   'bg-red-600 hover:bg-red-500',
    orange:  'bg-red-600 hover:bg-red-500',
  }[vertical?.accent_color] || 'bg-red-600 hover:bg-red-500'

  return (
    <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
      <div className="px-6 py-4 border-b border-slate-700 flex items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-white">
            {vertical?.display_name || 'Users'}
          </h2>
          <p className="text-sm text-slate-400">{filtered.length} of {users.length} users</p>
        </div>
        <input
          type="text"
          placeholder="Search name, email, plan..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 w-64"
        />
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-slate-900/50">
            <tr>
              <Th col="name">Name</Th>
              <Th col="plan_tier">Plan</Th>
              <Th col="risk_score">Risk Score</Th>
              <Th col="sessions_last_30d">Sessions</Th>
              <Th col="segment">Segment</Th>
              <Th col="status">Status</Th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-slate-400 uppercase tracking-wider">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700/50">
            {sorted.map((user) => (
              <tr key={user.id} className="hover:bg-slate-700/30 transition-colors">
                <td className="px-4 py-3">
                  <div className="font-medium text-white">{user.name}</div>
                  <div className="text-xs text-slate-500">{user.email}</div>
                </td>
                <td className="px-4 py-3">
                  <span className={`font-medium capitalize ${PLAN_COLORS[user.plan_tier] || 'text-white'}`}>
                    {user.plan_tier}
                  </span>
                  {user.monthly_spend > 0 && (
                    <div className="text-xs text-slate-500">${user.monthly_spend}/mo</div>
                  )}
                </td>
                <td className="px-4 py-3">
                  <RiskBadge score={user.risk_score} />
                </td>
                <td className="px-4 py-3">
                  <EngagementTrend prev={user.sessions_prev_30d} curr={user.sessions_last_30d} />
                </td>
                <td className="px-4 py-3">
                  {user.segment ? (
                    <span className="text-xs font-medium text-amber-400">
                      {user.segment.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                    </span>
                  ) : (
                    <span className="text-slate-600 text-xs">—</span>
                  )}
                </td>
                <td className="px-4 py-3">
                  <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium capitalize ${STATUS_STYLES[user.status] || 'bg-slate-700 text-slate-300'}`}>
                    {user.status}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  {user.status === 'active' ? (
                    <button
                      onClick={() => onSimulateCancel(user)}
                      disabled={loadingUserId === user.id}
                      className={`px-3 py-1.5 ${accentBtnClass} disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-medium rounded-lg transition-colors`}
                    >
                      {loadingUserId === user.id ? 'Analyzing...' : 'Simulate Cancel'}
                    </button>
                  ) : (
                    <span className={`text-xs capitalize ${STATUS_STYLES[user.status]?.split(' ')[1] || 'text-slate-500'}`}>
                      {user.status}
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {sorted.length === 0 && (
          <div className="text-center py-12 text-slate-500">No users found</div>
        )}
      </div>
    </div>
  )
}

import { useState, useEffect, useCallback } from 'react'
import { api } from './api'
import UserTable from './components/UserTable'
import InterventionModal from './components/InterventionModal'
import AnalyticsDashboard from './components/AnalyticsDashboard'
import VerticalSwitcher from './components/VerticalSwitcher'

const DEFAULT_VERTICALS = [
  { name: 'b2b_saas',      display_name: 'B2B SaaS',    accent_color: 'emerald' },
  { name: 'entertainment',  display_name: 'Streaming',   accent_color: 'purple' },
  { name: 'lifestyle',     display_name: 'Fitness',      accent_color: 'green' },
  { name: 'marketplace',   display_name: 'Marketplace',  accent_color: 'orange' },
]

export default function App() {
  const [vertical, setVertical] = useState('b2b_saas')
  const [verticals, setVerticals] = useState(DEFAULT_VERTICALS)
  const [users, setUsers] = useState([])
  const [analytics, setAnalytics] = useState(null)
  const [selectedUser, setSelectedUser] = useState(null)
  const [intervention, setIntervention] = useState(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [loadingUserId, setLoadingUserId] = useState(null)
  const [resetting, setResetting] = useState(false)
  const [error, setError] = useState(null)

  const loadData = useCallback(async (v) => {
    const activeVertical = v || vertical
    try {
      const [usersData, analyticsData] = await Promise.all([
        api.getUsers({ vertical: activeVertical }),
        api.getAnalytics(activeVertical),
      ])
      setUsers(usersData)
      setAnalytics(analyticsData)
      setError(null)
    } catch (e) {
      setError('Could not connect to backend. Is the server running?')
    }
  }, [vertical])

  // Load verticals list on mount
  useEffect(() => {
    api.getVerticals().then(setVerticals).catch(() => {})
  }, [])

  useEffect(() => {
    loadData(vertical)
  }, [vertical])

  const handleVerticalChange = (v) => {
    setVertical(v)
  }

  const handleSimulateCancel = async (user) => {
    setSelectedUser(user)
    setIntervention(null)
    setModalOpen(true)
    setLoadingUserId(user.id)
    try {
      const data = await api.cancelUser(user.id)
      setIntervention(data)
      await loadData(user.vertical || vertical)
    } catch (e) {
      console.error('Cancel failed:', e)
      setError(e.message || 'Failed to simulate cancellation.')
      setModalOpen(false)
    } finally {
      setLoadingUserId(null)
    }
  }

  const handleRespond = async (interventionId, outcome) => {
    await api.respondIntervention(interventionId, outcome)
    await loadData(vertical)
  }

  const handleCloseModal = () => {
    setModalOpen(false)
    setSelectedUser(null)
    setIntervention(null)
  }

  const handleReset = async () => {
    if (!confirm('Reset demo? This will re-seed all 4 verticals and clear all interventions.')) return
    setResetting(true)
    try {
      await api.resetDemo()
      await loadData(vertical)
    } catch (e) {
      console.error('Reset failed:', e)
    } finally {
      setResetting(false)
    }
  }

  const currentVertical = verticals.find((v) => v.name === vertical) || DEFAULT_VERTICALS[0]

  return (
    <div className="min-h-screen bg-slate-900 text-white">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 py-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-emerald-500 rounded-lg flex items-center justify-center text-white font-bold text-sm shrink-0">
              CS
            </div>
            <div>
              <h1 className="text-lg font-bold text-white leading-none">ChurnShield</h1>
              <p className="text-xs text-slate-500 leading-none mt-0.5">Autonomous Churn Intervention Engine</p>
            </div>
          </div>

          <div className="flex items-center gap-3 flex-wrap">
            <VerticalSwitcher
              current={vertical}
              onChange={handleVerticalChange}
              verticals={verticals}
            />
            {analytics && (
              <span className="text-xs text-slate-500 hidden lg:block">
                {analytics.active_users} active
              </span>
            )}
            <button
              onClick={handleReset}
              disabled={resetting}
              className="px-4 py-2 bg-slate-700 hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed text-slate-300 text-sm rounded-lg transition-colors border border-slate-600 shrink-0"
            >
              {resetting ? 'Resetting...' : 'Reset Demo'}
            </button>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {error && (
          <div className="bg-red-900/30 border border-red-700 rounded-xl p-6 text-center mb-6">
            <p className="text-red-400 font-medium">{error}</p>
            <button
              onClick={() => loadData(vertical)}
              className="mt-3 px-4 py-2 bg-red-800 hover:bg-red-700 text-white text-sm rounded-lg transition-colors"
            >
              Retry
            </button>
          </div>
        )}

        <AnalyticsDashboard analytics={analytics} vertical={currentVertical} />
        <UserTable
          users={users}
          onSimulateCancel={handleSimulateCancel}
          loadingUserId={loadingUserId}
          vertical={currentVertical}
        />
      </main>

      {modalOpen && (
        <InterventionModal
          user={selectedUser}
          intervention={intervention}
          loading={loadingUserId !== null}
          onRespond={handleRespond}
          onClose={handleCloseModal}
        />
      )}
    </div>
  )
}

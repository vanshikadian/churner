import { useState } from 'react'
import RiskBadge from './RiskBadge'
import FeatureBreakdown from './FeatureBreakdown'

const OFFER_ICONS = {
  // B2B
  discount_30: '💰', discount_50: '💸', annual_lock_in: '🔒',
  plan_downgrade: '📉', feature_unlock_trial: '🔓', onboarding_session: '🤝',
  use_case_guide: '📖', priority_support: '🎧', account_manager: '👔',
  bug_fix_guarantee: '🔧', pause_2mo: '⏸️', pause_1mo: '⏸️', reactivation_discount: '🔄',
  // Entertainment
  coming_soon_preview: '🎬', personalized_recs: '✨', ad_tier_downgrade: '📺',
  annual_discount: '💳', new_genre_spotlight: '🎭', premium_trial: '⭐',
  // Lifestyle
  lite_plan: '🏃', pause_with_challenges: '💪', fresh_start_program: '🌱',
  new_program_unlock: '🏋️', coach_session: '🧑‍💼', goal_reset: '🎯',
  beginner_restart: '🔰', buddy_match: '👥', reduced_commitment: '📊',
  seasonal_pause: '🍂', off_season_lite: '❄️',
  // Marketplace
  service_credit: '💳', free_delivery_pass: '🚀', priority_redelivery: '⚡',
  favorites_discount: '❤️', free_delivery_week: '🎁', loyalty_tier_up: '🏆',
  reactivation_credit: '🎁', exclusive_deal: '🌟', free_month_pass: '🎟️',
  loyalty_program: '⭐', bulk_deal: '📦', annual_pass_discount: '🔒',
}

function formatOfferType(s) {
  return s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

export default function InterventionModal({ user, intervention, loading, onRespond, onClose }) {
  const [responding, setResponding] = useState(false)
  const [result, setResult] = useState(null)

  const handleRespond = async (outcome) => {
    setResponding(true)
    try {
      await onRespond(intervention.id, outcome)
      setResult(outcome)
    } finally {
      setResponding(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={!responding && !loading ? onClose : undefined} />

      <div className="relative bg-slate-800 rounded-2xl border border-slate-700 w-full max-w-lg shadow-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700 sticky top-0 bg-slate-800 z-10">
          <div>
            <h2 className="text-lg font-semibold text-white">Churn Intervention</h2>
            <p className="text-sm text-slate-400">{user?.name}</p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-500 hover:text-white transition-colors text-xl leading-none"
            disabled={responding}
          >
            ×
          </button>
        </div>

        <div className="px-6 py-5">
          {loading && (
            <div className="flex flex-col items-center justify-center py-12 gap-4">
              <div className="w-10 h-10 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
              <p className="text-slate-400 text-sm">Computing real-time risk score...</p>
            </div>
          )}

          {!loading && intervention && !result && (
            <>
              {/* Risk + Segment + Revenue row */}
              <div className="grid grid-cols-3 gap-3 mb-4">
                <div className="bg-slate-700/50 rounded-xl p-3">
                  <p className="text-xs text-slate-500 mb-1">Churn Risk</p>
                  <RiskBadge score={intervention.churn_risk_score} />
                </div>
                <div className="bg-slate-700/50 rounded-xl p-3">
                  <p className="text-xs text-slate-500 mb-1">Segment</p>
                  <p className="text-xs font-semibold text-amber-400 leading-tight">
                    {intervention.segment?.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                  </p>
                </div>
                <div className="bg-slate-700/50 rounded-xl p-3">
                  <p className="text-xs text-slate-500 mb-1">At Risk</p>
                  <p className="text-sm font-semibold text-white">
                    ${intervention.revenue_at_risk?.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                  </p>
                  <p className="text-xs text-slate-500">annual</p>
                </div>
              </div>

              {/* Feature breakdown */}
              <FeatureBreakdown riskFactors={intervention.risk_factors} />

              {/* Offer */}
              <div className="flex items-center gap-2 mb-3">
                <span className="text-xl">{OFFER_ICONS[intervention.offer_type] || '🎁'}</span>
                <div>
                  <span className="text-sm font-semibold text-white">
                    {formatOfferType(intervention.offer_type)}
                  </span>
                  <span className="ml-2 inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs bg-purple-900/50 text-purple-400 border border-purple-700/50">
                    AI Selected
                  </span>
                </div>
              </div>

              {/* Offer message */}
              <div className="relative bg-slate-900/70 rounded-xl p-4 mb-4 border border-slate-700">
                <div className="absolute -top-2.5 left-4 bg-slate-800 px-2 text-xs text-slate-500">
                  Personalized Message
                </div>
                <p className="text-slate-200 text-sm leading-relaxed">{intervention.offer_message}</p>
                <div className="flex justify-end mt-3">
                  {intervention.message_source === 'llm' ? (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-purple-900/50 text-purple-400 border border-purple-700/50">
                      ✦ AI Generated
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-slate-700 text-slate-500 border border-slate-600">
                      Template
                    </span>
                  )}
                </div>
              </div>

              {/* Offer details */}
              {intervention.offer_details && Object.keys(intervention.offer_details).length > 0 && (
                <div className="flex flex-wrap gap-2 mb-5">
                  {Object.entries(intervention.offer_details).map(([k, v]) => (
                    <span key={k} className="px-2.5 py-1 bg-slate-700/60 rounded-lg text-xs text-slate-300">
                      <span className="text-slate-500">{k.replace(/_/g, ' ')}: </span>{String(v)}
                    </span>
                  ))}
                </div>
              )}

              {/* Action buttons */}
              <div className="grid grid-cols-2 gap-3">
                <button
                  onClick={() => handleRespond('accepted')}
                  disabled={responding}
                  className="py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold rounded-xl transition-colors"
                >
                  {responding ? '...' : 'Accept Offer'}
                </button>
                <button
                  onClick={() => handleRespond('rejected')}
                  disabled={responding}
                  className="py-2.5 bg-red-700 hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold rounded-xl transition-colors"
                >
                  {responding ? '...' : 'Reject & Churn'}
                </button>
              </div>
            </>
          )}

          {/* Result state */}
          {result && (
            <div className="flex flex-col items-center justify-center py-10 gap-4">
              {result === 'accepted' ? (
                <>
                  <div className="text-5xl">🎉</div>
                  <div className="text-center">
                    <p className="text-lg font-semibold text-emerald-400">User Retained!</p>
                    <p className="text-sm text-slate-400 mt-1">
                      ${(intervention.revenue_saved || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })} in estimated revenue saved
                    </p>
                    <p className="text-xs text-slate-500 mt-1">
                      Bandit updated · offer performance recorded
                    </p>
                  </div>
                </>
              ) : (
                <>
                  <div className="text-5xl">😞</div>
                  <div className="text-center">
                    <p className="text-lg font-semibold text-red-400">User Churned</p>
                    <p className="text-sm text-slate-400 mt-1">Offer declined · bandit updated</p>
                  </div>
                </>
              )}
              <button
                onClick={onClose}
                className="mt-2 px-6 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-xl text-sm transition-colors"
              >
                Close
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

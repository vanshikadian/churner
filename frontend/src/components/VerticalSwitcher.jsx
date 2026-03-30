const ACCENT = {
  emerald: { tab: 'border-emerald-500 text-emerald-400', dot: 'bg-emerald-500' },
  purple:  { tab: 'border-purple-500 text-purple-400',   dot: 'bg-purple-500' },
  green:   { tab: 'border-green-500 text-green-400',     dot: 'bg-green-500' },
  orange:  { tab: 'border-orange-500 text-orange-400',   dot: 'bg-orange-500' },
}

const DEFAULT_VERTICALS = [
  { name: 'b2b_saas',     display_name: 'B2B SaaS',    accent_color: 'emerald' },
  { name: 'entertainment', display_name: 'Streaming',   accent_color: 'purple' },
  { name: 'lifestyle',    display_name: 'Fitness',      accent_color: 'green' },
  { name: 'marketplace',  display_name: 'Marketplace',  accent_color: 'orange' },
]

export default function VerticalSwitcher({ current, onChange, verticals = DEFAULT_VERTICALS }) {
  return (
    <div className="flex items-center gap-1 bg-slate-800/60 rounded-xl border border-slate-700 p-1">
      {verticals.map((v) => {
        const isActive = current === v.name
        const accent = ACCENT[v.accent_color] || ACCENT.emerald
        return (
          <button
            key={v.name}
            onClick={() => onChange(v.name)}
            className={[
              'px-4 py-2 rounded-lg text-sm font-medium transition-all duration-150 flex items-center gap-2',
              isActive
                ? `bg-slate-700 ${accent.tab} border border-slate-600`
                : 'text-slate-400 hover:text-slate-200 border border-transparent',
            ].join(' ')}
          >
            {isActive && (
              <span className={`w-1.5 h-1.5 rounded-full ${accent.dot} inline-block`} />
            )}
            {v.display_name}
          </button>
        )
      })}
    </div>
  )
}

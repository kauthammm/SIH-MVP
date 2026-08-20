import { getGuestSessionId } from '../../utils/guestSession'

export default function GuestProfileBar({ profile, completeness, onDailyBriefing, loadingBriefing }) {
  if (!profile || Object.keys(profile).length === 0) {
    return (
      <div className="mx-4 mb-3 px-4 py-3 rounded-xl bg-kv-sageLight/40 border border-kv-sage/30 text-xs text-kv-forest">
        <p className="font-semibold">🎤 Voice profile building…</p>
        <p className="text-gray-600 mt-1">Tell me your crop and land type — I learn from your voice automatically.</p>
      </div>
    )
  }

  const chips = []
  if (profile.crop) chips.push(`🌾 ${profile.crop}`)
  if (profile.land_type) chips.push(`🏞 ${profile.land_type}`)
  if (profile.irrigation_source) chips.push(`💧 ${profile.irrigation_source}`)
  if (profile.district) chips.push(`📍 ${profile.district}`)
  if (profile.growth_stage) chips.push(`📈 ${profile.growth_stage}`)

  return (
    <div className="mx-4 mb-3 px-4 py-3 rounded-xl bg-white border border-kv-beige shadow-sm">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div>
          <p className="text-xs font-semibold text-kv-forest">
            Your farm profile
            <span className="text-gray-400 font-normal ml-2">{Math.round((completeness || 0) * 100)}% complete</span>
          </p>
          <div className="flex flex-wrap gap-1.5 mt-1.5">
            {chips.map((c) => (
              <span key={c} className="text-[10px] px-2 py-0.5 rounded-full bg-kv-creamDark text-gray-700">{c}</span>
            ))}
          </div>
        </div>
        <button
          type="button"
          onClick={onDailyBriefing}
          disabled={loadingBriefing}
          className="text-[11px] font-semibold px-3 py-1.5 rounded-lg bg-kv-sage text-white hover:bg-kv-forest disabled:opacity-50 shrink-0"
        >
          {loadingBriefing ? 'Loading…' : "Today's report"}
        </button>
      </div>
      <div className="mt-2 h-1 rounded-full bg-kv-creamDark overflow-hidden">
        <div
          className="h-full bg-kv-sage transition-all"
          style={{ width: `${Math.round((completeness || 0) * 100)}%` }}
        />
      </div>
      <p className="text-[10px] text-gray-400 mt-1.5">Session: {getGuestSessionId()?.slice(0, 8) || '…'} · Login anytime to save permanently</p>
    </div>
  )
}

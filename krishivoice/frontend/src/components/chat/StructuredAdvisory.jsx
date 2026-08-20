const INTENT_META = {
  irrigation_query: { label: 'Irrigation', icon: '💧', color: 'bg-sky-50 text-sky-700 border-sky-200' },
  weather_query: { label: 'Weather', icon: '🌦', color: 'bg-indigo-50 text-indigo-700 border-indigo-200' },
  crop_status: { label: 'Crop status', icon: '🌱', color: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  disease_risk: { label: 'Disease risk', icon: '🦠', color: 'bg-rose-50 text-rose-700 border-rose-200' },
  pest_risk: { label: 'Pest risk', icon: '🐛', color: 'bg-orange-50 text-orange-700 border-orange-200' },
  yield_prediction: { label: 'Yield', icon: '📊', color: 'bg-violet-50 text-violet-700 border-violet-200' },
  general_agriculture: { label: 'General', icon: '🌾', color: 'bg-gray-50 text-gray-700 border-gray-200' },
}

const RISK_STYLE = {
  low: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  medium: 'bg-amber-100 text-amber-800 border-amber-200',
  high: 'bg-red-100 text-red-800 border-red-200',
}

const EVIDENCE_LABELS = {
  soil_moisture: 'Soil moisture',
  soil_moisture_pct: 'Soil moisture',
  rainfall_mm: 'Rainfall',
  rainfall_forecast_mm: 'Rain forecast',
  temperature: 'Temperature',
  humidity: 'Humidity',
  crop: 'Crop',
  growth_stage: 'Growth stage',
  ph: 'pH',
  nitrogen: 'Nitrogen',
  phosphorus: 'Phosphorus',
  potassium: 'Potassium',
  district: 'District',
  village: 'Village',
  profile_customized: 'Custom profile',
  weather_source: 'Weather source',
  mode: 'Mode',
}

function formatEvidenceKey(key) {
  return EVIDENCE_LABELS[key] || key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

function formatEvidenceValue(value) {
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (typeof value === 'number') return Number.isInteger(value) ? String(value) : value.toFixed(1)
  if (value && typeof value === 'object') return null
  return String(value)
}

function ConfidenceBar({ value }) {
  const pct = Math.round((value || 0) * 100)
  const color = pct >= 75 ? 'bg-emerald-500' : pct >= 50 ? 'bg-amber-500' : 'bg-gray-400'
  return (
    <div className="flex items-center gap-3">
      <div className="confidence-track flex-1">
        <div className={`confidence-fill ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-semibold text-gray-600 tabular-nums w-9 text-right">{pct}%</span>
    </div>
  )
}

export default function StructuredAdvisory({ advisory, intent, guest, language }) {
  if (!advisory) return null

  const meta = INTENT_META[intent] || INTENT_META.general_agriculture
  const risk = (advisory.risk_level || 'low').toLowerCase()
  const riskStyle = RISK_STYLE[risk] || RISK_STYLE.low
  const isGuest = guest || advisory.evidence?.mode === 'guest'

  const evidenceEntries = Object.entries(advisory.evidence || {}).filter(
    ([k, v]) => v != null && formatEvidenceValue(v) != null && !['hint', 'personalized', 'detected_language', 'tasks', 'advisory_dataset', 'convo_dataset'].includes(k) && !k.includes('detected'),
  )

  const primaryLabel = language === 'Tamil' ? 'பரிந்துரை' : 'Recommendation'
  const whyLabel = language === 'Tamil' ? 'ஏன் இந்த ஆலோசனை?' : 'Why this advice'
  const evidenceLabel = language === 'Tamil' ? 'வயல் தரவு' : 'Field evidence'
  const actionLabel = language === 'Tamil' ? 'செயல் நேரம்' : 'When to act'
  const confidenceLabel = language === 'Tamil' ? 'நம்பகத்தன்மை' : 'Confidence'

  return (
    <div className="mt-4 space-y-3 animate-slide-up">
      {/* Intent + mode header */}
      <div className="flex flex-wrap items-center gap-2">
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${meta.color}`}>
          <span>{meta.icon}</span>
          {meta.label}
        </span>
        {isGuest ? (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200">
            General guidance
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
            ✦ Personalized
          </span>
        )}
        <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold border capitalize ${riskStyle}`}>
          {risk} risk
        </span>
      </div>

      {/* Main recommendation card */}
      <div className="kv-card">
        <div className="kv-card-header bg-gray-50/80">
          <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">{primaryLabel}</span>
        </div>
        <div className="p-4">
          <div className={`kv-highlight ${isGuest ? 'kv-highlight-guest' : ''}`}>
            <p className="text-[15px] leading-[1.75] text-gray-900 font-medium">{advisory.recommendation}</p>
          </div>
        </div>
      </div>

      {/* Action + confidence row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {advisory.action_time && (
          <div className="kv-card p-4">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-400 mb-1.5">{actionLabel}</p>
            <p className="text-sm font-semibold text-gray-900 flex items-center gap-2">
              <span className="text-base">⏱</span>
              {advisory.action_time}
            </p>
          </div>
        )}
        <div className="kv-card p-4">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-400 mb-2">{confidenceLabel}</p>
          <ConfidenceBar value={advisory.confidence} />
        </div>
      </div>

      {/* Reason */}
      {advisory.reason && (
        <div className="kv-card">
          <div className="kv-card-header">
            <span className="text-xs font-semibold text-gray-600">{whyLabel}</span>
          </div>
          <div className="px-4 py-3.5">
            <p className="text-sm leading-relaxed text-gray-600">{advisory.reason}</p>
          </div>
        </div>
      )}

      {/* Evidence grid */}
      {evidenceEntries.length > 0 && (
        <div className="kv-card">
          <div className="kv-card-header">
            <span className="text-xs font-semibold text-gray-600">{evidenceLabel}</span>
          </div>
          <div className="px-4 py-3.5 flex flex-wrap gap-2">
            {evidenceEntries.map(([k, v]) => (
              <span key={k} className="evidence-chip">
                <span className="text-gray-500">{formatEvidenceKey(k)}</span>
                <span className="evidence-chip-value">{formatEvidenceValue(v)}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {advisory.evidence?.hint && isGuest && (
        <div className="rounded-xl border border-amber-200/80 bg-amber-50/60 px-4 py-3 text-sm text-amber-800 leading-relaxed">
          <span className="font-semibold">Tip: </span>
          {advisory.evidence.hint}
        </div>
      )}
    </div>
  )
}

import { useCallback, useState } from 'react'
import { fetchFarmReport } from '../../api'

const PERIODS = [
  { id: 'daily', en: 'Today', ta: 'இன்னைக்கு' },
  { id: 'weekly', en: 'Weekly', ta: 'வாரம்' },
  { id: 'monthly', en: 'Monthly', ta: 'மாதம்' },
  { id: 'yearly', en: 'Yearly', ta: 'வருடம்' },
]

export default function FarmReportsPanel({ open, farmerId, parcelId, sessionId, language, onSpeak, onClose }) {
  const [period, setPeriod] = useState('weekly')
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const isTa = language === 'Tamil'

  const load = useCallback(async (p) => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchFarmReport({ period: p, farmerId, parcelId, sessionId, language })
      setReport(data)
    } catch (e) {
      setError(e.message || 'Failed to load report')
    } finally {
      setLoading(false)
    }
  }, [farmerId, parcelId, sessionId, language])

  const handlePeriod = (p) => {
    setPeriod(p)
    load(p)
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/40 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[85vh] flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-kv-sage/20">
          <h2 className="font-semibold text-kv-forest">
            {isTa ? 'Farm அறிக்கை (Live Weather)' : 'Farm Reports (Live Weather)'}
          </h2>
          <button type="button" onClick={onClose} className="text-kv-muted hover:text-kv-forest text-xl leading-none">×</button>
        </div>

        <div className="flex gap-2 p-3 border-b border-kv-sage/10 overflow-x-auto">
          {PERIODS.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => handlePeriod(p.id)}
              className={`px-3 py-1.5 rounded-full text-sm whitespace-nowrap ${
                period === p.id
                  ? 'bg-kv-forest text-white'
                  : 'bg-kv-sageLight text-kv-forest hover:bg-kv-sage/30'
              }`}
            >
              {isTa ? p.ta : p.en}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto p-4 text-sm text-kv-forest space-y-3">
          {!report && !loading && !error && (
            <p className="text-kv-muted">
              {isTa
                ? 'வாரம் / மாதம் / வருடம் select pannunga — Open-Meteo live weather + உங்க farm data.'
                : 'Select a period — live Open-Meteo weather + your farm data.'}
            </p>
          )}
          {loading && <p className="text-kv-muted">{isTa ? 'Loading…' : 'Loading report…'}</p>}
          {error && <p className="text-red-600">{error}</p>}
          {report && (
            <>
              <p className="text-xs text-kv-muted">
                Source: {report.weather_source} · {report.location} · {report.date}
              </p>
              {report.high_alert_count > 0 && (
                <div className="bg-amber-50 border border-amber-200 rounded-lg p-2 text-amber-900">
                  ⚠ {report.high_alert_count} {isTa ? 'முக்கிய weather alert' : 'high weather alerts'}
                </div>
              )}
              {report.weather_summary && (
                <div className="grid grid-cols-2 gap-2">
                  <Stat label={isTa ? 'மழை (total)' : 'Rain (total)'} value={`${report.weather_summary.total_rainfall_mm ?? 0} mm`} />
                  <Stat label={isTa ? 'Avg temp' : 'Avg temp'} value={`${report.weather_summary.avg_temperature_c ?? '—'}°C`} />
                  <Stat label={isTa ? 'Max wind gust' : 'Max wind gust'} value={`${report.weather_summary.max_wind_gust_kmh ?? '—'} km/h`} />
                  <Stat label={isTa ? 'Rain days' : 'Rain days'} value={report.weather_summary.rain_days ?? 0} />
                </div>
              )}
              <p className="leading-relaxed whitespace-pre-wrap">{report.text}</p>
            </>
          )}
        </div>

        <div className="flex gap-2 p-3 border-t border-kv-sage/10">
          <button
            type="button"
            onClick={() => load(period)}
            disabled={loading}
            className="flex-1 py-2 rounded-xl bg-kv-sageLight text-kv-forest font-medium hover:bg-kv-sage/30 disabled:opacity-50"
          >
            {loading ? '…' : isTa ? 'Load report' : 'Load report'}
          </button>
          {report && onSpeak && (
            <button
              type="button"
              onClick={() => onSpeak(report.text, report.language)}
              className="flex-1 py-2 rounded-xl bg-kv-forest text-white font-medium hover:bg-kv-forest/90"
            >
              {isTa ? '🔊 கேளுங்க' : '🔊 Listen'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

function Stat({ label, value }) {
  return (
    <div className="bg-kv-sageLight/50 rounded-lg p-2">
      <div className="text-xs text-kv-muted">{label}</div>
      <div className="font-semibold">{value}</div>
    </div>
  )
}

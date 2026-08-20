import { useEffect, useRef, useState } from 'react'
import { checkCropSuitability, fetchSoilModelMetrics, uploadSoilReport } from '../api'

export default function SoilReportPanel({ farmerId, parcelId, district, onApplied }) {
  const fileRef = useRef(null)
  const [uploading, setUploading] = useState(false)
  const [checking, setChecking] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)
  const [variety, setVariety] = useState('')
  const [suitability, setSuitability] = useState(null)
  const [metrics, setMetrics] = useState(null)

  const handleUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    setError(null)
    setResult(null)
    setSuitability(null)
    try {
      const data = await uploadSoilReport(farmerId, parcelId, file)
      setResult(data)
      onApplied?.(data)
    } catch (err) {
      setError(err.message || 'Upload failed')
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  const handleCheckVariety = async () => {
    if (!variety.trim()) return
    setChecking(true)
    setError(null)
    try {
      const soil = result?.ocr || {}
      const res = await checkCropSuitability({
        farmerId,
        parcelId,
        district: district || soil.district,
        cropOrVariety: variety.trim(),
        pH: soil.pH,
        nitrogen: soil.N_kg_ha || soil.nitrogen,
        phosphorus: soil.P_kg_ha || soil.phosphorus,
        potassium: soil.K_kg_ha || soil.potassium,
        organicCarbon: soil.OC_percent || soil.organic_carbon,
        electricalConductivity: soil.EC_dS_m || soil.electrical_conductivity,
        soilType: soil.soil_type,
      })
      setSuitability(res)
    } catch (err) {
      setError(err.message || 'Check failed')
    } finally {
      setChecking(false)
    }
  }

  useEffect(() => {
    fetchSoilModelMetrics().then(setMetrics).catch(() => {})
  }, [])

  const ocr = result?.ocr
  const recs = result?.recommendations || []

  return (
    <div className="space-y-4">
      <section className="rounded-xl border border-kv-beige bg-white p-4 space-y-3">
        <h3 className="text-sm font-semibold text-kv-forest">Upload soil test report (PDF)</h3>
        <p className="text-xs text-gray-500">
          Upload your lab PDF — pH, N, P, K, OC and soil type will be read automatically and saved to your farm profile.
        </p>
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.png,.jpg,.jpeg"
          onChange={handleUpload}
          className="block w-full text-sm text-gray-600 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-kv-sageLight file:text-kv-forest file:font-semibold"
        />
        {uploading && <p className="text-xs text-kv-sage animate-pulse">Reading report…</p>}
      </section>

      {metrics?.f1_macro != null && (
        <p className="text-[10px] text-gray-400">
          Model test F1 (held-out districts): {(metrics.f1_macro * 100).toFixed(1)}% · {metrics.test_rows?.toLocaleString()} test samples
        </p>
      )}

      {ocr && (
        <section className="rounded-xl border border-kv-sage/30 bg-kv-sageLight/20 p-4 space-y-2">
          <p className="text-xs font-semibold text-kv-forest">Extracted from report</p>
          <div className="grid grid-cols-2 gap-2 text-xs">
            {ocr.pH != null && <span>pH: <b>{ocr.pH}</b></span>}
            {(ocr.N_kg_ha ?? ocr.nitrogen) != null && <span>N: <b>{ocr.N_kg_ha ?? ocr.nitrogen}</b> kg/ha</span>}
            {(ocr.P_kg_ha ?? ocr.phosphorus) != null && <span>P: <b>{ocr.P_kg_ha ?? ocr.phosphorus}</b> kg/ha</span>}
            {(ocr.K_kg_ha ?? ocr.potassium) != null && <span>K: <b>{ocr.K_kg_ha ?? ocr.potassium}</b> kg/ha</span>}
            {(ocr.OC_percent ?? ocr.organic_carbon) != null && <span>OC: <b>{ocr.OC_percent ?? ocr.organic_carbon}%</b></span>}
            {ocr.soil_type && <span>Soil: <b>{ocr.soil_type}</b></span>}
          </div>
          <p className="text-[10px] text-gray-500">Confidence: {Math.round((ocr.confidence || 0) * 100)}% · Fields: {ocr.fields_found?.join(', ')}</p>
        </section>
      )}

      {recs.length > 0 && (
        <section className="rounded-xl border border-kv-beige p-4 space-y-2">
          <p className="text-xs font-semibold text-kv-forest">Best crops for your soil</p>
          <ul className="space-y-2">
            {recs.map((r) => (
              <li key={r.crop} className="flex items-start justify-between gap-2 text-xs">
                <div>
                  <span className="font-semibold text-kv-forest">{r.crop}</span>
                  {r.reasons?.[0] && <p className="text-gray-500 mt-0.5">{r.reasons[0]}</p>}
                </div>
                <span className="shrink-0 px-2 py-0.5 rounded-full bg-kv-sageLight text-kv-forest font-semibold">
                  {(r.score * 100).toFixed(0)}%
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="rounded-xl border border-kv-beige p-4 space-y-3">
        <h3 className="text-sm font-semibold text-kv-forest">Check your crop / variety choice</h3>
        <p className="text-xs text-gray-500">
          e.g. ADT 43, Ponni, BPT 5204, Groundnut VBN 2, Kuruvai rice
        </p>
        <div className="flex gap-2">
          <input
            value={variety}
            onChange={(e) => setVariety(e.target.value)}
            placeholder="Crop or variety name"
            className="flex-1 px-3 py-2 rounded-xl border text-sm"
          />
          <button
            type="button"
            onClick={handleCheckVariety}
            disabled={checking || !variety.trim()}
            className="px-4 py-2 rounded-xl bg-kv-forest text-white text-sm font-semibold disabled:opacity-50"
          >
            {checking ? '…' : 'Check'}
          </button>
        </div>
        {suitability && (
          <div className={`rounded-lg p-3 text-sm ${suitability.suitable ? 'bg-emerald-50 text-emerald-900 border border-emerald-200' : 'bg-amber-50 text-amber-900 border border-amber-200'}`}>
            <p className="font-semibold">{suitability.suitable ? '✓ Suitable' : '✗ Not ideal'} — {suitability.matched_variety} ({suitability.parent_crop})</p>
            <p className="text-xs mt-1">{suitability.verdict_en}</p>
            {suitability.reasons?.length > 0 && (
              <ul className="mt-2 text-xs list-disc pl-4 space-y-0.5">
                {suitability.reasons.map((r, i) => <li key={i}>{r}</li>)}
              </ul>
            )}
          </div>
        )}
      </section>

      {error && <p className="text-sm text-red-600 bg-red-50 rounded-xl px-3 py-2">{error}</p>}
    </div>
  )
}

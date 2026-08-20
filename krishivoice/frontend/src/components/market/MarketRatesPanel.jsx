import { useCallback, useEffect, useState } from 'react'
import { fetchMarketCatalog, fetchMarketPrices } from '../../api'

const CATEGORIES = [
  { id: 'vegetables', en: 'Vegetables', ta: 'காய்கறி' },
  { id: 'pulses', en: 'Pulses', ta: 'பருப்பு' },
  { id: 'cereals', en: 'Cereals', ta: 'தானியம்' },
  { id: 'fruits', en: 'Fruits', ta: 'பழம்' },
  { id: 'spices', en: 'Spices', ta: 'மசாலா' },
  { id: 'oilseeds', en: 'Oilseeds', ta: 'எண்ணெய் விதை' },
]

export default function MarketRatesPanel({ open, language, onClose, onAskInChat }) {
  const [category, setCategory] = useState('vegetables')
  const [commodity, setCommodity] = useState('')
  const [district, setDistrict] = useState('')
  const [catalog, setCatalog] = useState(null)
  const [prices, setPrices] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const isTa = language === 'Tamil'

  useEffect(() => {
    if (!open) return
    fetchMarketCatalog()
      .then(setCatalog)
      .catch(() => setCatalog(null))
  }, [open])

  const loadPrices = useCallback(async (opts = {}) => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchMarketPrices({
        category: opts.category ?? category,
        commodity: opts.commodity ?? commodity,
        district: district || undefined,
      })
      setPrices(data)
    } catch (e) {
      setError(e.message || 'Failed to load mandi prices')
      setPrices(null)
    } finally {
      setLoading(false)
    }
  }, [category, commodity, district])

  useEffect(() => {
    if (open) loadPrices({ category, commodity: commodity || undefined })
  }, [open, category]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!open) return null

  const catItems = catalog?.categories?.[category] || []
  const priceRows = prices?.prices || (prices?.summary ? [prices.summary] : [])

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/40 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[85vh] flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-kv-sage/20">
          <div>
            <h2 className="font-semibold text-kv-forest">
              {isTa ? 'AGMARKNET சந்தை விலை' : 'AGMARKNET Market Rates'}
            </h2>
            <p className="text-xs text-kv-muted mt-0.5">
              {isTa ? 'Tamil Nadu live mandi (data.gov.in)' : 'Tamil Nadu live mandi (data.gov.in)'}
            </p>
          </div>
          <button type="button" onClick={onClose} className="text-kv-muted hover:text-kv-forest text-xl leading-none">×</button>
        </div>

        <div className="flex gap-2 p-3 border-b border-kv-sage/10 overflow-x-auto">
          {CATEGORIES.map((c) => (
            <button
              key={c.id}
              type="button"
              onClick={() => { setCategory(c.id); setCommodity('') }}
              className={`px-3 py-1.5 rounded-full text-sm whitespace-nowrap ${
                category === c.id
                  ? 'bg-kv-forest text-white'
                  : 'bg-kv-sageLight text-kv-forest hover:bg-kv-sage/30'
              }`}
            >
              {isTa ? c.ta : c.en}
            </button>
          ))}
        </div>

        <div className="p-3 border-b border-kv-sage/10 flex flex-wrap gap-2">
          <select
            value={commodity}
            onChange={(e) => setCommodity(e.target.value)}
            className="flex-1 min-w-[140px] text-sm border border-kv-sage/30 rounded-lg px-2 py-2 bg-white"
          >
            <option value="">{isTa ? 'அனைத்து crop' : 'All in category'}</option>
            {catItems.map((item) => (
              <option key={item.name} value={item.name}>
                {item.name}{item.tamil ? ` · ${item.tamil}` : ''}
              </option>
            ))}
          </select>
          <input
            type="text"
            value={district}
            onChange={(e) => setDistrict(e.target.value)}
            placeholder={isTa ? 'District (Madurai)' : 'District (Madurai)'}
            className="flex-1 min-w-[120px] text-sm border border-kv-sage/30 rounded-lg px-2 py-2"
          />
          <button
            type="button"
            onClick={() => loadPrices()}
            disabled={loading}
            className="px-4 py-2 rounded-lg bg-kv-forest text-white text-sm disabled:opacity-50"
          >
            {loading ? (isTa ? 'Loading…' : 'Loading…') : (isTa ? 'Refresh' : 'Refresh')}
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 text-sm text-kv-forest space-y-3">
          {error && (
            <p className="text-red-600">
              {error}
              <span className="block text-xs text-kv-muted mt-1">
                {isTa
                  ? 'AGMARKNET slow-a irundha konjam wait pannitu try pannunga.'
                  : 'If AGMARKNET is slow, wait and try again.'}
              </span>
            </p>
          )}

          {prices?.stale && (
            <p className="text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 text-xs">
              {isTa ? 'Cached mandi data — live API timeout.' : 'Showing cached mandi data — live API timed out.'}
            </p>
          )}

          {prices && !loading && !error && (
            <p className="text-xs text-kv-muted">
              {prices.english || prices.tamil}
            </p>
          )}

          {priceRows.length > 0 && (
            <ul className="space-y-2">
              {priceRows.map((row, i) => (
                <li
                  key={`${row.commodity}-${row.market}-${i}`}
                  className="flex items-start justify-between gap-3 p-3 rounded-xl bg-kv-sageLight/40 border border-kv-sage/15"
                >
                  <div>
                    <p className="font-medium">{row.commodity}</p>
                    <p className="text-xs text-kv-muted">
                      {[row.market, row.district].filter(Boolean).join(' · ')}
                    </p>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="font-semibold text-kv-forest">₹{Math.round(row.modal_price || 0)}</p>
                    <p className="text-xs text-kv-muted">
                      {row.min_price != null && row.max_price != null
                        ? `₹${Math.round(row.min_price)} – ₹${Math.round(row.max_price)}`
                        : row.price_unit || 'Rs./Quintal'}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          )}

          {!loading && !error && priceRows.length === 0 && prices && (
            <p className="text-kv-muted">
              {isTa ? 'Innikki live rate kidaikal — chat-la kelunga.' : 'No live rates found — try asking in chat.'}
            </p>
          )}
        </div>

        <div className="p-3 border-t border-kv-sage/10 flex gap-2">
          <button
            type="button"
            onClick={() => {
              const q = commodity
                ? (isTa ? `${commodity} vilai enna?` : `What is ${commodity} mandi price today?`)
                : (isTa ? NAV_TA[category] : NAV_EN[category])
              onAskInChat?.(q)
              onClose()
            }}
            className="flex-1 py-2.5 rounded-xl bg-kv-sage text-kv-forest text-sm font-medium"
          >
            {isTa ? 'Chat-la kelu' : 'Ask in chat'}
          </button>
        </div>
      </div>
    </div>
  )
}

const NAV_EN = {
  vegetables: 'What are vegetable mandi rates in Tamil Nadu?',
  pulses: 'What are pulse mandi rates today?',
  cereals: 'What is paddy mandi price today?',
  fruits: 'Fruit market rates Tamil Nadu',
  spices: 'Spice mandi rates today',
  oilseeds: 'Oilseed mandi rates Tamil Nadu',
}

const NAV_TA = {
  vegetables: 'காய்கறி mandi rate என்ன?',
  pulses: 'பருப்பு vilai enna?',
  cereals: 'நெல் market rate என்ற?',
  fruits: 'பழம் market rate',
  spices: 'மசாலா mandi rate',
  oilseeds: 'எண்ணெய் விதை vilai',
}

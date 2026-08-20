import { useCallback, useEffect, useState } from 'react'

import {
  createFarmLand, deleteFarmLand, fetchFarmMap, fetchFarmerProfile,
  saveParcelCustom,
} from '../api'
import { reverseGeocodeClient } from '../utils/geocode'

import FarmMapView from './farm/FarmMapView'
import SoilReportPanel from './SoilReportPanel'

import { CloseIcon } from './icons'

import { polygonAreaHa, polygonCentroid } from '../utils/geo'
import { buildLandList, parcelLabel } from '../utils/lands'

const DISTRICTS = ['Thanjavur', 'Cuddalore', 'Nagapattinam', 'Tiruvarur', 'Ariyalur', 'Perambalur']

const CROPS = ['Rice', 'Blackgram', 'Groundnut', 'Sugarcane', 'Cotton']

const CROP_LABELS = {
  Rice: { en: 'Rice (Nell)', ta: 'நெல்' },
  Blackgram: { en: 'Blackgram (Ulundu)', ta: 'உளுந்து' },
  Groundnut: { en: 'Groundnut (Nilakadalai)', ta: 'நிலக்கடலை' },
  Sugarcane: { en: 'Sugarcane (Karumbu)', ta: 'கரும்பு' },
  Cotton: { en: 'Cotton (Paruthi)', ta: 'பருத்தி' },
}

/** Plain-language crop stage — farmers pick what they see in the field */
const GROWTH_STAGES = [
  { value: 'Nursery', en: 'Just planted / seedlings', ta: 'இப்பதான் விதைச்சேன்' },
  { value: 'Tillering', en: 'Growing well / young plants', ta: 'செடி வளருது' },
  { value: 'Panicle Initiation', en: 'Panicle forming', ta: 'பூ வர போகுது' },
  { value: 'Flowering', en: 'Flowering now', ta: 'பூ பூத்தது' },
  { value: 'Maturity', en: 'Ready to harvest', ta: 'அறுவடைக்கு ready' },
  { value: 'Harvest', en: 'Harvesting', ta: 'அறுவடை பண்றேன்' },
]

const MOISTURE_OPTIONS = [
  { value: 12, en: 'Very dry — needs water now', ta: 'மிக வறண்டது — தண்ணீர் வேணும்' },
  { value: 20, en: 'Dry — should irrigate soon', ta: 'வறண்டது — விரைவில் பாய்ச்சுங்க' },
  { value: 28, en: 'OK — normal moisture', ta: 'சரி — normal ஈரம்' },
  { value: 38, en: 'Wet — enough water', ta: 'நனை — தண்ணீர் போதும்' },
]

const SOIL_TYPES = [
  { value: 'Clay Loam', en: 'Sticky / black-red mix (Clay Loam)', ta: 'சேறு மண்' },
  { value: 'Clay', en: 'Heavy sticky soil (Clay)', ta: 'களி மண்' },
  { value: 'Loam', en: 'Good mixed soil (Loam)', ta: 'நல்ல மண்' },
  { value: 'Sandy Loam', en: 'Sandy / light soil', ta: 'மணல் மண்' },
  { value: 'Alluvial', en: 'River / delta soil', ta: 'ஆற்று மண்' },
  { value: 'Red Soil', en: 'Red soil (Sempu mann)', ta: 'சிகப்பு மண்' },
  { value: 'Black Cotton Soil', en: 'Black cotton soil', ta: 'கருப்பு cotton மண்' },
]

const LAND_TYPES = [
  { value: 'Wetland', en: 'Wet field (Nanjei — canal/tank water)', ta: 'நன்செய் நிலம்' },
  { value: 'Dryland', en: 'Dry field (Punjei — rain-fed)', ta: 'புஞ்சை நிலம்' },
  { value: 'Garden land', en: 'Garden land', ta: 'தோட்ட நிலம்' },
  { value: 'Horticulture', en: 'Fruits / vegetables', ta: 'காய்கறி / பழம்' },
  { value: 'Mixed', en: 'Mixed use', ta: 'கலப்பு' },
]

const IRRIGATION_SOURCES = [
  { value: 'Canal', en: 'Canal water (Kaalvai)', ta: 'கால்வாய் தண்ணீர்' },
  { value: 'Borewell', en: 'Borewell / well', ta: 'போர்வெல் / கிணறு' },
  { value: 'Rain-fed', en: 'Rain only', ta: 'மழை தண்ணீர் மட்டும்' },
  { value: 'Tank', en: 'Tank / lake (Eri)', ta: 'ஏரி / குளம்' },
  { value: 'Drip', en: 'Drip irrigation', ta: 'DRIP' },
  { value: 'Sprinkler', en: 'Sprinkler', ta: 'Sprinkler' },
]

const LAND_SLOPES = ['Flat', 'Gentle slope', 'Moderate slope', 'Steep']

const DRAINAGE = ['Good', 'Moderate', 'Poor', 'Waterlogged']

const WATER_TABLE = ['High', 'Medium', 'Low']

const FIELD_CONDITIONS = ['Excellent', 'Good', 'Average', 'Needs improvement', 'Degraded']

const SEGMENT_COLORS = ['#40916c', '#d4a373', '#4895ef', '#f72585', '#7209b7']

const EMPTY_SOIL = { ph: '', nitrogen: '', phosphorus: '', potassium: '', organic_carbon: '', soil_type: 'Clay Loam' }



const TABS = [

  { id: 'soil', label: 'Soil test' },

  { id: 'details', label: 'My crop' },

  { id: 'land', label: 'My land' },

  { id: 'map', label: 'Map & area' },

  { id: 'segments', label: 'Plots' },

]






function newSegment(i, lat, lng) {

  return {

    segment_id: `S${i + 1}`,

    name: `Plot ${i + 1}`,

    crop: 'Rice',

    growth_stage: 'Tillering',

    area_ha: 0.5,

    soil_type: 'Clay Loam',

    soil_moisture: '',

    soil: { ...EMPTY_SOIL, soil_type: 'Clay Loam' },

    latitude: lat,

    longitude: lng,

    color: SEGMENT_COLORS[i % SEGMENT_COLORS.length],

  }

}



const EMPTY_LAND = {

  land_type: 'Wetland',

  irrigation_source: 'Canal',

  land_slope: 'Flat',

  drainage: 'Moderate',

  water_table: 'Medium',

  soil_texture: 'Clay Loam',

  field_condition: 'Good',

}



export default function ProfilePanel({ open, onClose, farmerId, parcelId, onParcelChange, onSaved }) {

  const [tab, setTab] = useState('map')

  const [loading, setLoading] = useState(true)

  const [saving, setSaving] = useState(false)

  const [error, setError] = useState(null)

  const [success, setSuccess] = useState(false)

  const [profile, setProfile] = useState(null)

  const [selectedParcel, setSelectedParcel] = useState(parcelId || '')

  const [activeSeg, setActiveSeg] = useState(0)

  const [segments, setSegments] = useState([])

  const [boundary, setBoundary] = useState([])
  const [placeLabel, setPlaceLabel] = useState('')
  const [geocoding, setGeocoding] = useState(false)
  const [addingLand, setAddingLand] = useState(false)

  const [form, setForm] = useState({
    land_name: '',
    district: '', taluk: '', village: '', latitude: '', longitude: '', area: '',
    crop: 'Rice', growth_stage: 'Tillering', soil_moisture: '', soil: { ...EMPTY_SOIL },
    ...EMPTY_LAND,
  })



  const loadProfile = useCallback(async () => {

    if (!farmerId) return

    setLoading(true)

    setError(null)

    try {

      const data = await fetchFarmerProfile(farmerId)

      setProfile(data)

      const pid = parcelId || data.active_parcel_id || data.parcels?.[0]?.parcel_id

      if (pid) setSelectedParcel(pid)

    } catch (e) {

      setError(e.message)

    } finally {

      setLoading(false)

    }

  }, [farmerId, parcelId])



  const loadMap = useCallback(async (pid) => {
    if (!farmerId || !pid) return
    try {
      const map = await fetchFarmMap(farmerId, pid)
      if (map.boundary?.length) setBoundary(map.boundary)
      else setBoundary([])
      if (map.segments?.length) setSegments(map.segments)
      else {
        const lat = map.centroid?.lat || 10.787
        const lng = map.centroid?.lng || 79.137
        setSegments([newSegment(0, lat, lng)])
      }
    } catch {
      const custom = profile?.parcels_custom?.[pid] || {}
      const base = profile?.parcels?.find((p) => p.parcel_id === pid)
      const lat = custom.latitude ?? base?.latitude ?? 10.787
      const lng = custom.longitude ?? base?.longitude ?? 79.137
      if (custom.boundary?.length) setBoundary(custom.boundary)
      else setBoundary([])
      setSegments(custom.segments?.length ? custom.segments : [newSegment(0, lat, lng)])
    }
  }, [farmerId, profile])



  useEffect(() => {

    if (open && farmerId) loadProfile()

  }, [open, farmerId, loadProfile])



  useEffect(() => {

    if (!profile || !selectedParcel) return

    const merged = buildLandList(profile).find((p) => p.parcel_id === selectedParcel)
    const base = merged || profile.parcels?.find((p) => p.parcel_id === selectedParcel)

    const custom = profile.parcels_custom?.[selectedParcel] || {}

    const soil = custom.soil || {}

    setForm({
      land_name: custom.land_name || custom.village || '',
      district: custom.district || base?.district || '',
      taluk: custom.taluk || base?.taluk || '',
      village: custom.village || base?.village || '',

      latitude: custom.latitude ?? base?.latitude ?? '',

      longitude: custom.longitude ?? base?.longitude ?? '',

      area: custom.area ?? base?.area ?? '',

      crop: custom.crop || 'Rice',

      growth_stage: custom.growth_stage || 'Tillering',

      soil_moisture: custom.soil_moisture ?? '',

      soil: {

        ph: soil.ph ?? '', nitrogen: soil.nitrogen ?? '', phosphorus: soil.phosphorus ?? '',

        potassium: soil.potassium ?? '', organic_carbon: soil.organic_carbon ?? '',

        soil_type: soil.soil_type || base?.soil_type || 'Clay Loam',

      },

      land_type: custom.land_type || EMPTY_LAND.land_type,

      irrigation_source: custom.irrigation_source || base?.irrigation_source || EMPTY_LAND.irrigation_source,

      land_slope: custom.land_slope || EMPTY_LAND.land_slope,

      drainage: custom.drainage || EMPTY_LAND.drainage,

      water_table: custom.water_table || EMPTY_LAND.water_table,

      soil_texture: custom.soil_texture || soil.soil_type || 'Clay Loam',

      field_condition: custom.field_condition || EMPTY_LAND.field_condition,

    })

    const labelName = custom.land_name || custom.village || merged?.land_name || merged?.village
    if (labelName) {
      setPlaceLabel([labelName, custom.taluk || merged?.taluk, custom.district || merged?.district].filter(Boolean).join(', '))
    }

    if (custom.segments?.length) setSegments(custom.segments)

    if (custom.boundary?.length) setBoundary(custom.boundary)

    else loadMap(selectedParcel)

  }, [profile, selectedParcel, loadMap])



  const updateField = (key, value) => setForm((f) => ({ ...f, [key]: value }))

  const updateSoil = (key, value) => setForm((f) => ({ ...f, soil: { ...f.soil, [key]: value } }))

  const updateSegment = (i, key, value) => {

    setSegments((segs) => segs.map((s, idx) => (idx === i ? { ...s, [key]: value } : s)))

  }



  const centroid = {

    lat: form.latitude !== '' ? Number(form.latitude) : undefined,

    lng: form.longitude !== '' ? Number(form.longitude) : undefined,

  }



  const resolveLocation = useCallback(async (lat, lng) => {
    setGeocoding(true)
    setError(null)
    updateField('latitude', lat.toFixed(6))
    updateField('longitude', lng.toFixed(6))
    if (segments.length && activeSeg != null) {
      updateSegment(activeSeg, 'latitude', lat)
      updateSegment(activeSeg, 'longitude', lng)
    }
    try {
      const geo = await reverseGeocodeClient(lat, lng)
      const name = geo.land_name || geo.village || geo.display_name?.split(',')[0]?.trim() || ''
      setPlaceLabel(geo.display_name || name)
      setForm((f) => ({
        ...f,
        latitude: lat.toFixed(6),
        longitude: lng.toFixed(6),
        village: geo.village || name,
        taluk: geo.taluk || f.taluk,
        district: geo.district || f.district,
        land_name: name,
      }))
    } catch {
      const fallback = `Farm · ${lat.toFixed(4)}, ${lng.toFixed(4)}`
      setPlaceLabel(fallback)
      setForm((f) => ({
        ...f,
        latitude: lat.toFixed(6),
        longitude: lng.toFixed(6),
        land_name: fallback,
      }))
    } finally {
      setGeocoding(false)
    }
  }, [activeSeg, segments.length])

  const handleMapClick = ({ lat, lng }) => {
    resolveLocation(lat, lng)
  }

  const handleAddLand = async () => {
    if (!farmerId) return
    setAddingLand(true)
    setError(null)
    try {
      const res = await createFarmLand(farmerId, {})
      const newId = res.land?.land_id || res.land?.parcel_id
      await loadProfile()
      if (newId) {
        setSelectedParcel(newId)
        onParcelChange?.(newId)
        setTab('map')
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setAddingLand(false)
    }
  }

  const handleDeleteLand = async () => {
    if (!farmerId || !selectedParcel?.startsWith('FL')) return
    if (!window.confirm('Remove this farm land registration?')) return
    try {
      await deleteFarmLand(farmerId, selectedParcel)
      await loadProfile()
      setSelectedParcel('')
    } catch (e) {
      setError(e.message)
    }
  }



  const handleBoundaryChange = (pts) => {
    setBoundary(pts)
    if (pts.length >= 3) {
      const ha = polygonAreaHa(pts)
      updateField('area', ha.toFixed(3))
      const c = polygonCentroid(pts)
      if (c) resolveLocation(c.lat, c.lng)
    }
  }



  const addSegment = () => {

    const lat = centroid.lat || 10.787

    const lng = centroid.lng || 79.137

    const offset = segments.length * 0.001

    setSegments((s) => [...s, newSegment(s.length, lat + offset, lng + offset)])

    setActiveSeg(segments.length)

  }



  const handleSave = async () => {

    if (!farmerId || !selectedParcel) return
    if (form.latitude === '' || form.longitude === '') {
      setError('Set your farm location first — tap My location or click the map.')
      return
    }
    setSaving(true)

    setError(null)

    setSuccess(false)

    try {
      const lat = Number(form.latitude)
      const lng = Number(form.longitude)
      let landName = form.land_name
      let village = form.village
      let taluk = form.taluk
      let district = form.district
      let displayName = placeLabel

      try {
        const geo = await reverseGeocodeClient(lat, lng)
        landName = geo.land_name || geo.village || landName
        village = geo.village || landName
        taluk = geo.taluk || taluk
        district = geo.district || district
        displayName = geo.display_name || landName
        setPlaceLabel(displayName)
        setForm((f) => ({ ...f, land_name: landName, village, taluk, district }))
      } catch {
        /* save with pinned coords even if lookup fails */
      }

      const payload = {
        land_name: landName || village || undefined,
        district: district || undefined,
        taluk: taluk || undefined,
        village: village || undefined,

        latitude: form.latitude !== '' ? Number(form.latitude) : undefined,

        longitude: form.longitude !== '' ? Number(form.longitude) : undefined,

        area: form.area !== '' ? Number(form.area) : undefined,

        crop: form.crop || undefined,

        growth_stage: form.growth_stage || undefined,

        soil_moisture: form.soil_moisture !== '' ? Number(form.soil_moisture) : undefined,

        land_type: form.land_type,

        irrigation_source: form.irrigation_source,

        land_slope: form.land_slope,

        drainage: form.drainage,

        water_table: form.water_table,

        soil_texture: form.soil_texture,

        field_condition: form.field_condition,

        boundary: boundary.length >= 3 ? boundary : undefined,

        soil: {

          ph: form.soil.ph !== '' ? Number(form.soil.ph) : undefined,

          nitrogen: form.soil.nitrogen !== '' ? Number(form.soil.nitrogen) : undefined,

          phosphorus: form.soil.phosphorus !== '' ? Number(form.soil.phosphorus) : undefined,

          potassium: form.soil.potassium !== '' ? Number(form.soil.potassium) : undefined,

          organic_carbon: form.soil.organic_carbon !== '' ? Number(form.soil.organic_carbon) : undefined,

          soil_type: form.soil.soil_type || form.soil_texture || undefined,

        },

        segments: segments.map((s) => ({

          ...s,

          area_ha: s.area_ha ? Number(s.area_ha) : undefined,

          soil_moisture: s.soil_moisture !== '' && s.soil_moisture != null ? Number(s.soil_moisture) : undefined,

        })),

      }

      const result = await saveParcelCustom(farmerId, selectedParcel, payload)
      const savedName = result.land_name || landName || village
      setProfile((prev) => {
        if (!prev) return prev
        const parcels_custom = {
          ...prev.parcels_custom,
          [selectedParcel]: {
            ...(prev.parcels_custom?.[selectedParcel] || {}),
            ...payload,
            land_name: savedName,
            village: result.village || village,
          },
        }
        return { ...prev, parcels_custom, active_parcel_id: selectedParcel }
      })
      if (result.land_name || result.village) {
        setForm((f) => ({
          ...f,
          land_name: result.land_name || f.land_name,
          village: result.village || f.village,
        }))
        setPlaceLabel(result.land_name || result.village || placeLabel)
      }
      setSuccess(true)

      onParcelChange?.(selectedParcel)

      onSaved?.()

      await loadProfile()

      setTimeout(() => setSuccess(false), 2500)

    } catch (e) {

      setError(e.message)

    } finally {

      setSaving(false)

    }

  }



  if (!open) return null

  const landList = buildLandList(profile)
  const hasCustom = profile?.parcels_custom?.[selectedParcel]



  return (

    <div className="fixed inset-0 z-40 flex justify-end">

      <button type="button" className="absolute inset-0 bg-black/40" onClick={onClose} aria-label="Close" />

      <aside className="relative w-full max-w-2xl h-full bg-white shadow-elevated flex flex-col border-l border-kv-beige animate-slide-in">

        <header className="px-5 py-4 border-b border-kv-beige shrink-0">

          <div className="flex items-start justify-between gap-3">

            <div>

              <h2 className="font-bold text-kv-forest">Farm profile</h2>

              <p className="text-xs text-gray-500 mt-0.5">
                Just speak — say &quot;I am planting rice&quot; or tap below. No technical words needed.
              </p>

            </div>

            <button type="button" onClick={onClose} className="p-2 rounded-xl hover:bg-kv-creamDark"><CloseIcon /></button>

          </div>

          <div className="flex gap-1 mt-3 p-1 bg-kv-creamDark rounded-xl overflow-x-auto">

            {TABS.map((t) => (

              <button

                key={t.id}

                type="button"

                onClick={() => setTab(t.id)}

                className={`flex-1 min-w-[70px] py-1.5 rounded-lg text-xs font-semibold transition whitespace-nowrap ${

                  tab === t.id ? 'bg-white text-kv-forest shadow-sm' : 'text-gray-500'

                }`}

              >

                {t.label}

              </button>

            ))}

          </div>

        </header>



        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">

          {loading && <p className="text-sm text-gray-500">Loading…</p>}

          {error && <p className="text-sm text-red-600 bg-red-50 rounded-xl px-3 py-2">{error}</p>}



          {!loading && (

            <>

              <section className="rounded-xl bg-kv-sageLight/30 border border-kv-sage/30 p-3 space-y-2">
                <p className="text-xs font-semibold text-kv-forest">🎤 Or just tell KrishiVoice in chat:</p>
                <p className="text-[11px] text-gray-600 leading-relaxed">
                  &quot;I am planting rice&quot; · &quot;My field is dry&quot; · &quot;Canal water wet land&quot; ·
                  &quot;Red soil, crop growing well&quot; · &quot;How much water for my crop?&quot;
                </p>
                <p className="text-[10px] text-kv-sage">Tamil-um English-um work — mic button in chat.</p>
              </section>

              <section>
                <div className="flex items-center justify-between gap-2 mb-2">
                  <label className="text-xs font-semibold text-gray-500 uppercase">Your farm lands</label>
                  <button
                    type="button"
                    onClick={handleAddLand}
                    disabled={addingLand}
                    className="text-xs font-semibold text-kv-sage hover:text-kv-forest disabled:opacity-50"
                  >
                    {addingLand ? 'Adding…' : '+ Add new land'}
                  </button>
                </div>
                <select
                  value={selectedParcel}
                  onChange={(e) => { setSelectedParcel(e.target.value); onParcelChange?.(e.target.value) }}
                  className="w-full px-3 py-2 rounded-xl border border-kv-beige text-sm"
                >
                  {landList.length === 0 && <option value="">No land yet — add one</option>}
                  {landList.map((p) => <option key={p.parcel_id} value={p.parcel_id}>{parcelLabel(p)}</option>)}
                </select>
                {selectedParcel?.startsWith('FL') && (
                  <button type="button" onClick={handleDeleteLand} className="text-[11px] text-red-600 mt-1 hover:underline">
                    Remove this land
                  </button>
                )}
                {hasCustom && (
                  <p className="text-[11px] text-kv-sage mt-1">✓ Saved — advice uses this land&apos;s GPS & soil data</p>
                )}
              </section>

              <section>
                <label className="text-[11px] text-gray-500">Farm / land name</label>
                <input
                  value={form.land_name}
                  onChange={(e) => updateField('land_name', e.target.value)}
                  placeholder="Auto-filled from map when you pick location"
                  className="w-full mt-1 px-3 py-2 rounded-xl border text-sm"
                />
              </section>



              {tab === 'map' && (

                <>

                  <FarmMapView
                    centroid={centroid.lat ? centroid : { lat: Number(form.latitude) || 10.787, lng: Number(form.longitude) || 79.137 }}
                    segments={segments}
                    boundary={boundary}
                    placeName={placeLabel || form.land_name || form.village}
                    onCentroidChange={handleMapClick}

                    onBoundaryChange={handleBoundaryChange}

                    onSegmentPick={setActiveSeg}

                    activeSegmentIndex={activeSeg}

                    height={340}

                  />

                  <p className="text-xs text-gray-500">
                    Tap <strong>My location</strong> or click the map — village & district fill automatically from the map.
                    {geocoding && <span className="text-kv-sage ml-1">Looking up place name…</span>}
                  </p>
                  {placeLabel && (
                    <p className="text-xs font-medium text-kv-forest bg-kv-sageLight/40 rounded-xl px-3 py-2">
                      📍 {placeLabel}
                    </p>
                  )}
                  <div className="grid grid-cols-2 gap-2">

                    <input type="number" step="any" value={form.latitude} onChange={(e) => updateField('latitude', e.target.value)} placeholder="Latitude" className="px-3 py-2 rounded-xl border text-sm" />

                    <input type="number" step="any" value={form.longitude} onChange={(e) => updateField('longitude', e.target.value)} placeholder="Longitude" className="px-3 py-2 rounded-xl border text-sm" />

                    <input type="number" step="0.001" value={form.area} onChange={(e) => updateField('area', e.target.value)} placeholder="Area (ha)" className="col-span-2 px-3 py-2 rounded-xl border text-sm" />

                  </div>

                </>

              )}



              {tab === 'land' && (

                <section className="space-y-3">

                  <p className="text-xs text-gray-500">Tell us about your land in simple words — or say it by voice in chat.</p>

                  <div className="grid grid-cols-1 gap-3">

                    <div>

                      <label className="text-xs font-medium text-kv-forest">What kind of field?</label>

                      <select value={form.land_type} onChange={(e) => updateField('land_type', e.target.value)} className="w-full mt-1 px-3 py-2 rounded-xl border text-sm">

                        {LAND_TYPES.map((t) => <option key={t.value} value={t.value}>{t.en}</option>)}

                      </select>

                    </div>

                    <div>

                      <label className="text-xs font-medium text-kv-forest">Where does water come from?</label>

                      <select value={form.irrigation_source} onChange={(e) => updateField('irrigation_source', e.target.value)} className="w-full mt-1 px-3 py-2 rounded-xl border text-sm">

                        {IRRIGATION_SOURCES.map((t) => <option key={t.value} value={t.value}>{t.en}</option>)}

                      </select>

                    </div>

                    <div>

                      <label className="text-xs font-medium text-kv-forest">What soil do you have?</label>

                      <select value={form.soil_texture} onChange={(e) => { updateField('soil_texture', e.target.value); updateSoil('soil_type', e.target.value) }} className="w-full mt-1 px-3 py-2 rounded-xl border text-sm">

                        {SOIL_TYPES.map((t) => <option key={t.value} value={t.value}>{t.en}</option>)}

                      </select>

                    </div>

                  </div>

                </section>

              )}



              {tab === 'segments' && (

                <div className="space-y-3">

                  <div className="flex items-center justify-between">

                    <h3 className="text-xs font-semibold text-gray-500 uppercase">Land segments</h3>

                    <button type="button" onClick={addSegment} className="text-xs font-semibold text-kv-sage">+ Add segment</button>

                  </div>

                  {segments.map((seg, i) => (

                    <div key={seg.segment_id || i} className={`rounded-xl border p-3 space-y-2 ${activeSeg === i ? 'border-kv-sage bg-kv-sageLight/30' : 'border-kv-beige'}`}>

                      <div className="grid grid-cols-2 gap-2">

                        <input value={seg.name} onChange={(e) => updateSegment(i, 'name', e.target.value)} placeholder="Segment name" className="col-span-2 px-2 py-1.5 rounded-lg border text-sm" />

                        <select value={seg.crop} onChange={(e) => updateSegment(i, 'crop', e.target.value)} className="px-2 py-1.5 rounded-lg border text-sm">

                          {CROPS.map((c) => <option key={c}>{c}</option>)}

                        </select>

                        <select value={seg.growth_stage} onChange={(e) => updateSegment(i, 'growth_stage', e.target.value)} className="px-2 py-1.5 rounded-lg border text-sm">

                          {GROWTH_STAGES.map((s) => <option key={s.value} value={s.value}>{s.en}</option>)}

                        </select>

                        <input type="number" step="0.01" value={seg.area_ha} onChange={(e) => updateSegment(i, 'area_ha', e.target.value)} placeholder="Area ha" className="px-2 py-1.5 rounded-lg border text-sm" />

                        <select value={seg.soil_type} onChange={(e) => updateSegment(i, 'soil_type', e.target.value)} className="px-2 py-1.5 rounded-lg border text-sm">

                          {SOIL_TYPES.map((t) => <option key={t.value} value={t.value}>{t.en}</option>)}

                        </select>

                        <input type="number" value={seg.soil?.ph ?? ''} onChange={(e) => updateSegment(i, 'soil', { ...seg.soil, ph: e.target.value })} placeholder="pH" className="px-2 py-1.5 rounded-lg border text-sm" />

                        <input type="number" value={seg.soil_moisture ?? ''} onChange={(e) => updateSegment(i, 'soil_moisture', e.target.value)} placeholder="Moisture %" className="px-2 py-1.5 rounded-lg border text-sm" />

                      </div>

                      <p className="text-[10px] text-gray-400">📍 {Number(seg.latitude).toFixed(5)}, {Number(seg.longitude).toFixed(5)}</p>

                    </div>

                  ))}

                </div>

              )}



              {tab === 'soil' && (
                <SoilReportPanel
                  farmerId={farmerId}
                  parcelId={selectedParcel}
                  district={form.district}
                  onApplied={() => { onSaved?.(); loadProfile?.() }}
                />
              )}

              {tab === 'details' && (

                <>

                  <section className="space-y-3">

                    <div>

                      <label className="text-xs font-medium text-kv-forest">What crop are you growing?</label>

                      <div className="flex flex-wrap gap-2 mt-2">

                        {CROPS.map((c) => (

                          <button

                            key={c}

                            type="button"

                            onClick={() => updateField('crop', c)}

                            className={`px-3 py-1.5 rounded-full text-xs font-semibold border transition ${

                              form.crop === c ? 'bg-kv-forest text-white border-kv-forest' : 'bg-white text-gray-600 border-kv-beige hover:border-kv-sage'

                            }`}

                          >

                            {CROP_LABELS[c]?.en || c}

                          </button>

                        ))}

                      </div>

                    </div>

                    <div>

                      <label className="text-xs font-medium text-kv-forest">How is your crop now?</label>

                      <select value={form.growth_stage} onChange={(e) => updateField('growth_stage', e.target.value)} className="w-full mt-1 px-3 py-2 rounded-xl border text-sm">

                        {GROWTH_STAGES.map((s) => <option key={s.value} value={s.value}>{s.en}</option>)}

                      </select>

                    </div>

                    <div>

                      <label className="text-xs font-medium text-kv-forest">How wet is your field?</label>

                      <div className="grid grid-cols-2 gap-2 mt-2">

                        {MOISTURE_OPTIONS.map((m) => (

                          <button

                            key={m.value}

                            type="button"

                            onClick={() => updateField('soil_moisture', m.value)}

                            className={`px-2 py-2 rounded-xl text-[11px] font-medium border text-left transition ${

                              Number(form.soil_moisture) === m.value ? 'bg-kv-sageLight border-kv-sage text-kv-forest' : 'border-kv-beige text-gray-600 hover:border-kv-sage'

                            }`}

                          >

                            {m.en}

                          </button>

                        ))}

                      </div>

                    </div>

                  </section>

                  <details className="text-xs">

                    <summary className="cursor-pointer text-gray-500 font-medium">Optional: location & soil test numbers</summary>

                    <section className="grid grid-cols-2 gap-3 mt-3">

                      <div className="col-span-2">

                        <label className="text-[11px] text-gray-500">District</label>

                        <select value={form.district} onChange={(e) => updateField('district', e.target.value)} className="w-full mt-1 px-3 py-2 rounded-xl border text-sm">

                          <option value="">Select</option>

                          {DISTRICTS.map((d) => <option key={d}>{d}</option>)}

                        </select>

                      </div>

                      <input value={form.taluk} onChange={(e) => updateField('taluk', e.target.value)} placeholder="Taluk" className="px-3 py-2 rounded-xl border text-sm" />

                      <input value={form.village} onChange={(e) => updateField('village', e.target.value)} placeholder="Village" className="px-3 py-2 rounded-xl border text-sm" />

                      <input type="number" step="0.1" value={form.soil.ph} onChange={(e) => updateSoil('ph', e.target.value)} placeholder="pH (if known)" className="px-3 py-2 rounded-xl border text-sm" />

                      <select value={form.soil.soil_type} onChange={(e) => updateSoil('soil_type', e.target.value)} className="px-3 py-2 rounded-xl border text-sm">

                        {SOIL_TYPES.map((t) => <option key={t.value} value={t.value}>{t.en}</option>)}

                      </select>

                      <input type="number" value={form.soil.nitrogen} onChange={(e) => updateSoil('nitrogen', e.target.value)} placeholder="N (optional)" className="px-3 py-2 rounded-xl border text-sm" />

                      <input type="number" value={form.soil.phosphorus} onChange={(e) => updateSoil('phosphorus', e.target.value)} placeholder="P (optional)" className="px-3 py-2 rounded-xl border text-sm" />

                    </section>

                  </details>

                </>

              )}

            </>

          )}

        </div>



        <footer className="px-5 py-4 border-t border-kv-beige shrink-0 space-y-2">

          {success && <p className="text-sm text-green-700 text-center">Saved — advice will use your farm location & land data</p>}

          <button type="button" onClick={handleSave} disabled={saving || loading || !selectedParcel} className="w-full py-2.5 rounded-xl bg-kv-forest text-white font-semibold text-sm disabled:opacity-50">

            {saving ? 'Saving…' : 'Save farm profile'}

          </button>

        </footer>

      </aside>

    </div>

  )

}



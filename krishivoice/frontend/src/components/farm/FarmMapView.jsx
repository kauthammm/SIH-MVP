import { useCallback, useEffect, useState } from 'react'

import { CircleMarker, MapContainer, Marker, Polygon, Popup, TileLayer, useMap, useMapEvents } from 'react-leaflet'

import L from 'leaflet'

import 'leaflet/dist/leaflet.css'



import iconUrl from 'leaflet/dist/images/marker-icon.png'

import iconRetina from 'leaflet/dist/images/marker-icon-2x.png'

import shadowUrl from 'leaflet/dist/images/marker-shadow.png'

import { polygonAreaHa, polygonCentroid } from '../../utils/geo'



delete L.Icon.Default.prototype._getIconUrl

L.Icon.Default.mergeOptions({ iconRetinaUrl: iconRetina, iconUrl, shadowUrl })



const SEGMENT_COLORS = ['#40916c', '#d4a373', '#4895ef', '#f72585', '#7209b7', '#f77f00']



function MapClickHandler({ drawMode, onPick, onBoundaryPoint }) {

  useMapEvents({

    click(e) {

      if (drawMode) {

        onBoundaryPoint?.({ lat: e.latlng.lat, lng: e.latlng.lng })

      } else {

        onPick?.({ lat: e.latlng.lat, lng: e.latlng.lng })

      }

    },

  })

  return null

}



function FlyTo({ center, zoom }) {

  const map = useMap()

  useEffect(() => {

    if (center?.lat && center?.lng) {

      map.flyTo([center.lat, center.lng], zoom ?? map.getZoom(), { duration: 0.8 })

    }

  }, [center?.lat, center?.lng, zoom, map])

  return null

}



export default function FarmMapView({
  centroid,
  segments = [],
  boundary = [],
  placeName = '',
  onCentroidChange,
  onBoundaryChange,
  onSegmentPick,
  activeSegmentIndex = null,
  height = 320,
}) {

  const center = centroid?.lat && centroid?.lng

    ? [centroid.lat, centroid.lng]

    : [10.787, 79.1378]



  const [layer, setLayer] = useState('satellite')

  const [drawMode, setDrawMode] = useState(false)

  const [draftPoints, setDraftPoints] = useState(boundary || [])

  const [locating, setLocating] = useState(false)

  const [locError, setLocError] = useState(null)



  useEffect(() => {

    setDraftPoints(boundary || [])

  }, [boundary])



  const activeBoundary = drawMode ? draftPoints : (boundary || [])

  const areaHa = activeBoundary.length >= 3 ? polygonAreaHa(activeBoundary) : 0



  const polygonPositions = activeBoundary.map((p) => [p.lat, p.lng])



  const useMyLocation = useCallback(() => {

    if (!navigator.geolocation) {

      setLocError('GPS not supported in this browser')

      return

    }

    setLocating(true)

    setLocError(null)

    navigator.geolocation.getCurrentPosition(

      (pos) => {

        const { latitude: lat, longitude: lng } = pos.coords

        onCentroidChange?.({ lat, lng })

        setLocating(false)

      },

      (err) => {

        setLocError(err.message || 'Could not get location')

        setLocating(false)

      },

      { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 },

    )

  }, [onCentroidChange])



  const addBoundaryPoint = (pt) => {

    setDraftPoints((prev) => [...prev, pt])

  }



  const finishBoundary = () => {

    if (draftPoints.length < 3) return

    onBoundaryChange?.(draftPoints)

    setDrawMode(false)

  }



  const clearBoundary = () => {

    setDraftPoints([])

    onBoundaryChange?.([])

    setDrawMode(false)

  }



  const undoPoint = () => {

    setDraftPoints((prev) => prev.slice(0, -1))

  }



  const osm = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'

  const satellite = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'



  return (

    <div className="rounded-2xl overflow-hidden border border-kv-beige shadow-card">

      <div className="flex flex-wrap items-center justify-between gap-2 px-3 py-2 bg-kv-creamDark/60 border-b border-kv-beige">

        <p className="text-xs font-semibold text-kv-forest">

          {drawMode ? 'Click map corners to outline your farm' : 'Farm map · tap to set pin'}

        </p>

        <div className="flex flex-wrap gap-1">

          <button

            type="button"

            onClick={useMyLocation}

            disabled={locating}

            className="px-2 py-1 rounded-lg text-[10px] font-semibold bg-kv-sageLight text-kv-forest disabled:opacity-50"

          >

            {locating ? 'Locating…' : '📍 My location'}

          </button>

          <button

            type="button"

            onClick={() => { setDrawMode(!drawMode); if (!drawMode) setDraftPoints(boundary || []) }}

            className={`px-2 py-1 rounded-lg text-[10px] font-semibold ${drawMode ? 'bg-amber-500 text-white' : 'bg-white text-gray-600'}`}

          >

            {drawMode ? 'Drawing…' : 'Draw area'}

          </button>

          <button

            type="button"

            onClick={() => setLayer('satellite')}

            className={`px-2 py-1 rounded-lg text-[10px] font-semibold ${layer === 'satellite' ? 'bg-kv-forest text-white' : 'bg-white text-gray-600'}`}

          >

            Satellite

          </button>

          <button

            type="button"

            onClick={() => setLayer('street')}

            className={`px-2 py-1 rounded-lg text-[10px] font-semibold ${layer === 'street' ? 'bg-kv-forest text-white' : 'bg-white text-gray-600'}`}

          >

            Map

          </button>

        </div>

      </div>



      {drawMode && (

        <div className="flex flex-wrap gap-1 px-3 py-2 bg-amber-50 border-b border-amber-100 text-[10px]">

          <span className="text-amber-800 font-medium">{draftPoints.length} points</span>

          {areaHa > 0 && <span className="text-amber-700">· ~{areaHa.toFixed(2)} ha</span>}

          <button type="button" onClick={undoPoint} className="ml-auto px-2 py-0.5 rounded bg-white border text-gray-600">Undo</button>

          <button type="button" onClick={finishBoundary} disabled={draftPoints.length < 3} className="px-2 py-0.5 rounded bg-kv-forest text-white disabled:opacity-40">Finish area</button>

          <button type="button" onClick={clearBoundary} className="px-2 py-0.5 rounded bg-white border text-red-600">Clear</button>

        </div>

      )}



      {locError && (

        <p className="px-3 py-1 text-[10px] text-red-600 bg-red-50">{locError}</p>

      )}



      <MapContainer center={center} zoom={16} style={{ height, width: '100%' }} scrollWheelZoom>

        <TileLayer

          attribution={layer === 'satellite' ? 'Esri' : '&copy; OpenStreetMap'}

          url={layer === 'satellite' ? satellite : osm}

        />

        <FlyTo center={centroid} zoom={17} />

        <MapClickHandler

          drawMode={drawMode}

          onPick={onCentroidChange}

          onBoundaryPoint={addBoundaryPoint}

        />

        {activeBoundary.length >= 3 && (

          <Polygon

            positions={polygonPositions}

            pathOptions={{ color: '#1b4332', fillColor: '#40916c', fillOpacity: 0.25, weight: 2 }}

          />

        )}

        {activeBoundary.length >= 1 && activeBoundary.length < 3 && (

          <Polygon

            positions={polygonPositions}

            pathOptions={{ color: '#d4a373', fillOpacity: 0, weight: 2, dashArray: '4 4' }}

          />

        )}

        {centroid?.lat && !drawMode && (
          <Marker position={[centroid.lat, centroid.lng]}>
            <Popup>
              {placeName || 'Farm pin'}
              {areaHa > 0 ? ` · ${areaHa.toFixed(2)} ha` : ''}
              <br />
              <span style={{ fontSize: '11px' }}>{centroid.lat.toFixed(5)}, {centroid.lng.toFixed(5)}</span>
            </Popup>
          </Marker>
        )}

        {segments.map((seg, i) => {

          if (!seg.latitude || !seg.longitude) return null

          const color = seg.color || SEGMENT_COLORS[i % SEGMENT_COLORS.length]

          const isActive = activeSegmentIndex === i

          return (

            <CircleMarker

              key={seg.segment_id || i}

              center={[seg.latitude, seg.longitude]}

              radius={isActive ? 14 : 10}

              pathOptions={{

                color: isActive ? '#1b4332' : color,

                fillColor: color,

                fillOpacity: 0.75,

                weight: isActive ? 3 : 2,

              }}

              eventHandlers={{ click: () => onSegmentPick?.(i) }}

            >

              <Popup>

                <strong>{seg.name || `Segment ${i + 1}`}</strong>

                <br />

                {seg.crop} · {seg.area_ha || '?'} ha

                <br />

                {seg.soil_type || ''}

              </Popup>

            </CircleMarker>

          )

        })}

      </MapContainer>



      {areaHa > 0 && !drawMode && (
        <p className="px-3 py-1.5 text-[10px] text-kv-sage bg-kv-sageLight/30 border-t border-kv-beige">
          {placeName ? `${placeName} · ` : ''}~{areaHa.toFixed(2)} ha from drawn area
          {centroid?.lat ? ` · ${centroid.lat.toFixed(5)}, ${centroid.lng.toFixed(5)}` : ''}
        </p>
      )}

    </div>

  )

}



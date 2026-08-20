import { polygonAreaHa } from './geo'

export function mergeLandEntry(base, custom = {}) {
  const hasCustom = Boolean(
    custom.latitude != null || custom.land_name || custom.village
    || custom.boundary?.length || custom.is_custom_land,
  )
  let area = custom.area ?? base.area
  if ((!area || area === base.area) && custom.boundary?.length >= 3) {
    area = polygonAreaHa(custom.boundary)
  }
  const name = custom.land_name || custom.village || base.land_name || base.village || base.parcel_id
  return {
    ...base,
    district: custom.district ?? base.district,
    taluk: custom.taluk ?? base.taluk,
    village: custom.village ?? base.village,
    latitude: custom.latitude ?? base.latitude,
    longitude: custom.longitude ?? base.longitude,
    area,
    land_name: name,
    is_custom_land: Boolean(
      base.is_custom_land || custom.is_custom_land || String(base.parcel_id || '').startsWith('FL'),
    ),
    has_custom: hasCustom,
  }
}

/** Merge CSV parcels + saved profile overrides (works even if API returns CSV only). */
export function buildLandList(profile) {
  if (!profile) return []
  const custom = profile.parcels_custom || {}
  const csvParcels = profile.parcels || []
  const seen = new Set()
  const out = []

  for (const p of csvParcels) {
    seen.add(p.parcel_id)
    out.push(mergeLandEntry(p, custom[p.parcel_id] || {}))
  }
  for (const [pid, c] of Object.entries(custom)) {
    if (seen.has(pid)) continue
    if (c.is_custom_land || pid.startsWith('FL')) {
      out.push(mergeLandEntry({
        parcel_id: pid,
        farmer_id: profile.farmer_id,
        village: c.village || '',
        area: c.area || 0,
        is_custom_land: true,
      }, c))
    }
  }
  return out
}

export function parcelLabel(p) {
  const name = p.land_name || p.village || p.parcel_id
  const areaNum = p.area != null && p.area !== '' ? Number(p.area) : null
  const areaStr = areaNum != null && !Number.isNaN(areaNum) ? `${areaNum.toFixed(2)} ha` : null

  if (p.is_custom_land || p.parcel_id?.startsWith('FL')) {
    return areaStr ? `${name} · ${areaStr}` : name
  }
  if (p.has_custom) {
    return areaStr ? `${name} · ${areaStr}` : name
  }
  return areaStr ? `${p.parcel_id} · ${name} (${areaStr})` : `${p.parcel_id} · ${name}`
}

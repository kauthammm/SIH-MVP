/** Parse Nominatim address into farm fields */
function parseNominatimAddress(data, lat, lng) {
  const addr = data?.address || {}
  const village =
    addr.village || addr.hamlet || addr.town || addr.suburb
    || addr.neighbourhood || addr.locality || addr.quarter || ''
  const taluk = addr.county || addr.city_district || addr.municipality || addr.suburb || ''
  let district = addr.state_district || addr.district || addr.city || ''
  if (district && / district/i.test(district)) {
    district = district.replace(/ district/i, '')
  }
  const shortName = village || taluk || district.split(',')[0] || data?.display_name?.split(',')[0]?.trim() || ''
  return {
    latitude: lat,
    longitude: lng,
    display_name: data?.display_name || `${shortName}, ${district}`.trim(),
    land_name: shortName,
    village: village || shortName,
    taluk,
    district,
    state: addr.state || 'Tamil Nadu',
  }
}

/** Reverse geocode — backend first, Nominatim fallback if route missing */
export async function reverseGeocodeClient(lat, lng) {
  const API = import.meta.env.VITE_API_URL || '/api/v1'
  try {
    const res = await fetch(`${API}/geo/reverse?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lng)}`)
    if (res.ok) return res.json()
  } catch {
    /* try fallback */
  }

  const url = `https://nominatim.openstreetmap.org/reverse?format=json&lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lng)}&addressdetails=1&zoom=14`
  const res = await fetch(url, {
    headers: {
      Accept: 'application/json',
      'Accept-Language': 'en',
    },
  })
  if (!res.ok) throw new Error('Could not look up place name for this location')
  const data = await res.json()
  return parseNominatimAddress(data, lat, lng)
}

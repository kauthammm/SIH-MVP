/** Approximate polygon area in hectares (WGS84, equirectangular at centroid). */
export function polygonAreaHa(points) {
  if (!points || points.length < 3) return 0
  const lat0 = points.reduce((s, p) => s + p.lat, 0) / points.length
  const cosLat = Math.cos((lat0 * Math.PI) / 180)
  const mPerDegLat = 111320
  const mPerDegLng = 111320 * cosLat
  let area = 0
  for (let i = 0; i < points.length; i++) {
    const a = points[i]
    const b = points[(i + 1) % points.length]
    const x1 = a.lng * mPerDegLng
    const y1 = a.lat * mPerDegLat
    const x2 = b.lng * mPerDegLng
    const y2 = b.lat * mPerDegLat
    area += x1 * y2 - x2 * y1
  }
  return Math.abs(area / 2) / 10000
}

export function polygonCentroid(points) {
  if (!points?.length) return null
  const lat = points.reduce((s, p) => s + p.lat, 0) / points.length
  const lng = points.reduce((s, p) => s + p.lng, 0) / points.length
  return { lat, lng }
}

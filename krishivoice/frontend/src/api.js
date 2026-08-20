import { formatApiError } from './utils/formatError'

const API = import.meta.env.VITE_API_URL || '/api/v1'
const SESSION_KEY = 'krishivoice_session'

export function getStoredSession() {
  try {
    const raw = localStorage.getItem(SESSION_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function authHeaders(extra = {}) {
  const session = getStoredSession()
  const headers = { ...extra }
  if (session?.token && session.authMode === 'user') {
    headers.Authorization = `Bearer ${session.token}`
  }
  return headers
}

async function authFetch(path, options = {}) {
  const res = await fetch(`${API}${path}`, {
    ...options,
    headers: authHeaders(options.headers || {}),
  })
  if (!res.ok) await parseError(res)
  return res.json()
}

async function parseError(res) {
  const text = await res.text()
  try {
    const json = JSON.parse(text)
    const message = formatApiError(json.detail, json.message || text)
    throw new Error(message)
  } catch (e) {
    if (e instanceof Error && e.message !== text) throw e
    throw new Error(text || `Request failed (${res.status})`)
  }
}

export async function fetchJSON(path) {
  const res = await fetch(`${API}${path}`)
  if (!res.ok) await parseError(res)
  return res.json()
}

export async function postJSON(path, body) {
  const res = await fetch(`${API}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) await parseError(res)
  return res.json()
}

export async function putJSON(path, body) {
  const res = await fetch(`${API}${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) await parseError(res)
  return res.json()
}

export async function loginFarmer(farmerId, pin) {
  return postJSON('/auth/login', { farmer_id: farmerId, pin })
}

export async function loginUser(username, password) {
  return postJSON('/auth/login', { username, password })
}

export async function registerUser({ username, password, displayName, farmerId, district, village, primaryCrop }) {
  return postJSON('/auth/register', {
    username,
    password,
    display_name: displayName || undefined,
    farmer_id: farmerId || undefined,
    district: district || undefined,
    village: village || undefined,
    primary_crop: primaryCrop || undefined,
  })
}

export async function fetchConversations() {
  return authFetch('/conversations')
}

export async function createConversation(title = 'New chat') {
  return authFetch('/conversations', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  })
}

export async function fetchConversation(conversationId) {
  return authFetch(`/conversations/${conversationId}`)
}

export async function deleteConversation(conversationId) {
  const res = await fetch(`${API}/conversations/${conversationId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  })
  if (!res.ok) await parseError(res)
  return res.json()
}

export async function fetchFarmerProfile(farmerId) {
  const session = getStoredSession()
  if (session?.token && session.authMode === 'user') {
    return authFetch(`/farmers/${farmerId}/profile`)
  }
  return fetchJSON(`/farmers/${farmerId}/profile`)
}

export async function saveParcelCustom(farmerId, parcelId, data) {
  return putJSON(`/farmers/${farmerId}/parcels/${parcelId}/custom`, data)
}

export async function askKrishiVoiceGuest({ query, language, sessionId, useWebSearch = false }) {
  const { getGuestSessionId, setGuestSessionId } = await import('./utils/guestSession')
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 45000)
  try {
    const res = await fetch(`${API}/voice/query-guest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query_text: query,
        language,
        session_id: sessionId || getGuestSessionId(),
        use_web_search: useWebSearch,
      }),
      signal: controller.signal,
    })
    clearTimeout(timeout)
    if (!res.ok) await parseError(res)
    const data = await res.json()
    const sid = data.entities?.session_id
    if (sid) setGuestSessionId(sid)
    return data
  } catch (e) {
    clearTimeout(timeout)
    if (e.name === 'AbortError') throw new Error('Request timed out. Try again.')
    throw e
  }
}

export async function askKrishiVoice({ farmerId, parcelId, query, language, guest = false, conversationId, userId, useWebSearch = false }) {
  if (guest || !farmerId) {
    return askKrishiVoiceGuest({ query, language, useWebSearch })
  }

  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 45000)
  try {
    const res = await fetch(`${API}/voice/query`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({
        farmer_id: farmerId,
        parcel_id: parcelId || undefined,
        query_text: query,
        language,
        guest: false,
        conversation_id: conversationId || undefined,
        user_id: userId || undefined,
        use_web_search: useWebSearch,
      }),
      signal: controller.signal,
    })
    clearTimeout(timeout)
    if (!res.ok) await parseError(res)
    return res.json()
  } catch (e) {
    clearTimeout(timeout)
    if (e.name === 'AbortError') throw new Error('Request timed out. Try again.')
    throw e
  }
}

/** Fetch natural Tamil/English speech audio from backend Edge TTS */
export async function fetchSpeechAudio(text, language = 'Tamil') {
  const res = await fetch(`${API}/voice/speak`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, language }),
  })
  if (!res.ok) throw new Error('Speech unavailable')
  return res.blob()
}

export async function fetchWeatherAlerts({ parcelId, farmerId, guest = false } = {}) {
  const data = await fetchNotifications({ guest, farmerId, parcelId })
  return {
    alerts: data.notifications || [],
    alert_count: data.notification_count,
    high_count: data.high_count,
    weather_source: data.weather_source,
  }
}

export async function fetchNotifications({
  parcelId,
  farmerId,
  guest = false,
  sessionId,
  language = 'Tamil',
} = {}) {
  const params = new URLSearchParams({ language: language === 'English' ? 'English' : 'Tamil' })
  if (guest) {
    const { getGuestSessionId } = await import('./utils/guestSession')
    const sid = sessionId || getGuestSessionId()
    if (sid) params.set('session_id', sid)
  } else if (farmerId && parcelId) {
    params.set('farmer_id', farmerId)
    params.set('parcel_id', parcelId)
  }
  return fetchJSON(`/notifications?${params}`)
}

export async function fetchFarmReport({ period = 'weekly', farmerId, parcelId, sessionId, language = 'Tamil' } = {}) {
  const params = new URLSearchParams({
    period,
    language: language === 'English' ? 'English' : 'Tamil',
  })
  if (farmerId && parcelId) {
    params.set('farmer_id', farmerId)
    params.set('parcel_id', parcelId)
  } else if (sessionId) {
    params.set('session_id', sessionId)
  } else {
    const { getGuestSessionId } = await import('./utils/guestSession')
    const sid = getGuestSessionId()
    if (sid) params.set('session_id', sid)
  }
  return fetchJSON(`/voice/farm-report?${params}`)
}

export async function fetchCallBriefing({ farmerId, parcelId, language, guest, farmerName }) {
  return postJSON('/voice/call/briefing', {
    farmer_id: guest ? undefined : farmerId,
    parcel_id: guest ? undefined : parcelId,
    language: language === 'English' ? 'English' : 'Tamil',
    guest: !!guest,
    farmer_name: farmerName,
  })
}

export async function askCallAssistant({ farmerId, parcelId, query, language, guest = false, useWebSearch = false }) {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 45000)
  try {
    const res = await fetch(`${API}/voice/call/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query_text: query,
        farmer_id: guest ? undefined : farmerId,
        parcel_id: guest ? undefined : parcelId,
        language,
        guest: !!guest,
        use_web_search: useWebSearch,
      }),
      signal: controller.signal,
    })
    clearTimeout(timeout)
    if (!res.ok) await parseError(res)
    return res.json()
  } catch (e) {
    clearTimeout(timeout)
    if (e.name === 'AbortError') throw new Error('Request timed out. Try again.')
    throw e
  }
}

export async function createFarmLand(farmerId, data = {}) {
  return postJSON(`/farmers/${farmerId}/lands`, data)
}

export async function deleteFarmLand(farmerId, landId) {
  const res = await fetch(`${API}/farmers/${farmerId}/lands/${landId}`, { method: 'DELETE' })
  if (!res.ok) await parseError(res)
  return res.json()
}

export async function reverseGeocode(lat, lng) {
  const { reverseGeocodeClient } = await import('./utils/geocode')
  return reverseGeocodeClient(lat, lng)
}

export async function fetchFarmMap(farmerId, parcelId) {
  return fetchJSON(`/parcels/${parcelId}/farm-map?farmer_id=${encodeURIComponent(farmerId)}`)
}

export async function saveFarmSegments(farmerId, parcelId, segments) {
  return putJSON(`/farmers/${farmerId}/parcels/${parcelId}/segments`, { segments })
}

export async function uploadSoilReport(farmerId, parcelId, file) {
  const form = new FormData()
  form.append('file', file)
  const params = new URLSearchParams()
  if (farmerId) params.set('farmer_id', farmerId)
  if (parcelId) params.set('parcel_id', parcelId)
  const res = await fetch(`${API}/soil/upload-report?${params}`, {
    method: 'POST',
    headers: authHeaders(),
    body: form,
  })
  if (!res.ok) await parseError(res)
  return res.json()
}

export async function analyzeSoil(body) {
  return postJSON('/soil/analyze', body)
}

export async function checkCropSuitability({
  farmerId, parcelId, district, region, cropOrVariety,
  pH, nitrogen, phosphorus, potassium, organicCarbon, electricalConductivity, soilType, drainage,
}) {
  return postJSON('/soil/check-crop', {
    farmer_id: farmerId,
    parcel_id: parcelId,
    district,
    region,
    crop_or_variety: cropOrVariety,
    pH,
    nitrogen,
    phosphorus,
    potassium,
    organic_carbon: organicCarbon,
    electrical_conductivity: electricalConductivity,
    soil_type: soilType,
    drainage,
  })
}

export async function fetchSoilModelMetrics() {
  return fetchJSON('/soil/model-metrics')
}

export async function fetchMarketCatalog() {
  return fetchJSON('/market/catalog')
}

export async function fetchMarketPrices({ commodity, category, district, state } = {}) {
  const q = new URLSearchParams()
  if (commodity) q.set('commodity', commodity)
  if (category) q.set('category', category)
  if (district) q.set('district', district)
  if (state) q.set('state', state)
  const qs = q.toString()
  return fetchJSON(`/market/prices${qs ? `?${qs}` : ''}`)
}

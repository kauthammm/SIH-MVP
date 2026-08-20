const GUEST_SESSION_KEY = 'krishivoice_guest_session'

export function getGuestSessionId() {
  try {
    return localStorage.getItem(GUEST_SESSION_KEY) || null
  } catch {
    return null
  }
}

export function setGuestSessionId(id) {
  try {
    if (id) localStorage.setItem(GUEST_SESSION_KEY, id)
    else localStorage.removeItem(GUEST_SESSION_KEY)
  } catch { /* ignore */ }
}

export async function startGuestSession(language = 'Tamil') {
  return postJSON('/voice/guest/session', { language: language === 'English' ? 'English' : 'Tamil' })
}

export async function guestChat({ query, language, sessionId }) {
  const res = await postJSON('/voice/guest/chat', {
    query_text: query,
    language: language || 'Auto',
    session_id: sessionId || getGuestSessionId(),
  })
  if (res.session_id) setGuestSessionId(res.session_id)
  return res
}

export async function fetchDailyBriefing({ farmerId, parcelId, sessionId, language = 'Tamil', guest = false } = {}) {
  const params = new URLSearchParams({ language: language === 'English' ? 'English' : 'Tamil' })
  if (guest && sessionId) params.set('session_id', sessionId)
  else if (farmerId && parcelId) {
    params.set('farmer_id', farmerId)
    params.set('parcel_id', parcelId)
  }
  return fetchJSON(`/voice/daily-briefing?${params}`)
}

export async function fetchDemandForecast({ crop, landType, district, language = 'Tamil' } = {}) {
  const params = new URLSearchParams({ language: language === 'English' ? 'English' : 'Tamil', land_type: landType || 'Wetland' })
  if (crop) params.set('crop', crop)
  if (district) params.set('district', district)
  return fetchJSON(`/voice/demand-forecast?${params}`)
}

export async function fetchKnowledgeStats() {
  return fetchJSON('/knowledge/stats')
}

/** Turn FastAPI / fetch errors into readable strings (never [object Object]). */
export function formatApiError(detail, fallback = 'Request failed') {
  if (detail == null || detail === '') return fallback
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const parts = detail.map((item) => {
      if (typeof item === 'string') return item
      if (item && typeof item === 'object') {
        const field = Array.isArray(item.loc)
          ? item.loc.filter((p) => p !== 'body').join(' → ')
          : ''
        const msg = item.msg || item.message
        if (msg && field) return `${field}: ${msg}`
        if (msg) return msg
      }
      return null
    }).filter(Boolean)
    return parts.length ? parts.join('. ') : fallback
  }
  if (typeof detail === 'object') {
    return detail.message || detail.msg || fallback
  }
  return String(detail)
}

export function errorMessage(err, fallback = 'Something went wrong') {
  if (!err) return fallback
  if (typeof err === 'string') return err
  const msg = err.message
  if (typeof msg === 'string' && msg && !msg.includes('[object Object]')) return msg
  return fallback
}

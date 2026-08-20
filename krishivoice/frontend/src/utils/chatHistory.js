const KEY = 'krishivoice_recent_chats'

export function loadRecentChats() {
  try {
    const raw = localStorage.getItem(KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

export function addRecentChat(title) {
  if (!title?.trim()) return loadRecentChats()
  const entry = {
    id: Date.now(),
    title: title.length > 42 ? `${title.slice(0, 42)}…` : title,
    time: Date.now(),
  }
  const prev = loadRecentChats().filter((c) => c.title !== entry.title)
  const next = [entry, ...prev].slice(0, 8)
  localStorage.setItem(KEY, JSON.stringify(next))
  return next
}

export function formatRelativeTime(ts, language = 'Tamil') {
  const diff = Date.now() - ts
  const mins = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)
  const isEn = language === 'English'
  if (mins < 1) return isEn ? 'Just now' : 'இப்போதே'
  if (mins < 60) return isEn ? `${mins} min ago` : `${mins} நிமி முன்`
  if (hours < 24) return isEn ? `${hours} hr ago` : `${hours} மணி முன்`
  return isEn ? `${days} days ago` : `${days} நாள் முன்`
}

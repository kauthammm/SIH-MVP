import { useCallback, useEffect, useRef, useState } from 'react'
import { fetchNotifications } from '../api'
import { getGuestSessionId } from '../utils/guestSession'

const POLL_MS = 3 * 60 * 1000 // 3 minutes
const READ_KEY = 'kv_notifications_read'

function loadReadIds() {
  try {
    return new Set(JSON.parse(localStorage.getItem(READ_KEY) || '[]'))
  } catch {
    return new Set()
  }
}

function saveReadIds(ids) {
  try {
    localStorage.setItem(READ_KEY, JSON.stringify([...ids]))
  } catch { /* ignore */ }
}

export function useNotifications({ isGuest, farmerId, parcelId, language, enabled = true }) {
  const [notifications, setNotifications] = useState([])
  const [highCount, setHighCount] = useState(0)
  const [mediumCount, setMediumCount] = useState(0)
  const [loading, setLoading] = useState(false)
  const [readIds, setReadIds] = useState(loadReadIds)
  const lastTopIdRef = useRef(null)
  const [newAlert, setNewAlert] = useState(null)

  const load = useCallback(async () => {
    if (!enabled) return
    setLoading(true)
    try {
      const data = await fetchNotifications({
        guest: isGuest,
        farmerId,
        parcelId,
        sessionId: isGuest ? getGuestSessionId() : undefined,
        language: language === 'English' ? 'English' : 'Tamil',
      })
      const list = data.notifications || []
      setNotifications(list)
      setHighCount(data.high_count || 0)
      setMediumCount(data.medium_count || 0)

      const topHigh = list.find((n) => n.severity === 'high')
      const read = loadReadIds()
      if (topHigh && topHigh.id !== lastTopIdRef.current && !read.has(topHigh.id)) {
        lastTopIdRef.current = topHigh.id
        setNewAlert(topHigh)
      }
    } catch {
      setNotifications([])
      setHighCount(0)
    } finally {
      setLoading(false)
    }
  }, [enabled, isGuest, farmerId, parcelId, language])

  useEffect(() => {
    load()
    const id = setInterval(load, POLL_MS)
    return () => clearInterval(id)
  }, [load])

  const unreadCount = notifications.filter((n) => !readIds.has(n.id)).length

  const markRead = useCallback((id) => {
    setReadIds((prev) => {
      const next = new Set(prev)
      next.add(id)
      saveReadIds(next)
      return next
    })
  }, [])

  const markAllRead = useCallback(() => {
    const all = new Set(notifications.map((n) => n.id))
    setReadIds(all)
    saveReadIds(all)
    setNewAlert(null)
  }, [notifications])

  const dismissBanner = useCallback(() => {
    if (newAlert) markRead(newAlert.id)
    setNewAlert(null)
  }, [newAlert, markRead])

  return {
    notifications,
    highCount,
    mediumCount,
    unreadCount,
    loading,
    readIds,
    newAlert,
    load,
    markRead,
    markAllRead,
    dismissBanner,
  }
}

const CATEGORY_META = {
  weather: { en: 'Weather', ta: 'வானிலை', icon: '🌧', color: 'bg-sky-50 text-sky-800 border-sky-200' },
  climate: { en: 'Climate', ta: 'Climate', icon: '🌡', color: 'bg-orange-50 text-orange-800 border-orange-200' },
  irrigation: { en: 'Water', ta: 'தண்ணீர்', icon: '💧', color: 'bg-blue-50 text-blue-800 border-blue-200' },
  disease: { en: 'Disease', ta: 'நோய்', icon: '🦠', color: 'bg-purple-50 text-purple-800 border-purple-200' },
  field: { en: 'Field risk', ta: 'வயல் risk', icon: '⚠', color: 'bg-red-50 text-red-800 border-red-200' },
  daily: { en: 'Daily report', ta: 'Daily report', icon: '📋', color: 'bg-kv-sageLight text-kv-forest border-kv-sage/40' },
  crop: { en: 'Crop care', ta: 'Crop care', icon: '🌾', color: 'bg-emerald-50 text-emerald-800 border-emerald-200' },
  market: { en: 'Market tip', ta: 'Market tip', icon: '📈', color: 'bg-amber-50 text-amber-800 border-amber-200' },
}

const SEVERITY_STYLES = {
  high: 'border-l-4 border-l-red-500',
  medium: 'border-l-4 border-l-amber-400',
  low: 'border-l-4 border-l-kv-sage',
}

export default function NotificationsPanel({
  open,
  onClose,
  notifications,
  readIds,
  unreadCount,
  loading,
  language,
  onMarkRead,
  onMarkAllRead,
  onSpeak,
}) {
  const isEn = language === 'English'

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <button type="button" className="absolute inset-0 bg-black/40" onClick={onClose} aria-label="Close" />
      <aside className="relative w-full max-w-md h-full bg-white shadow-elevated flex flex-col border-l border-kv-beige animate-slide-in">
        <header className="px-5 py-4 border-b border-kv-beige shrink-0">
          <div className="flex items-center justify-between gap-2">
            <div>
              <h2 className="font-bold text-kv-forest">{isEn ? 'Notifications' : 'Notifications'}</h2>
              <p className="text-xs text-gray-500 mt-0.5">
                {isEn
                  ? 'Weather, crop tips & daily reports — all in the app'
                  : 'Weather, crop tips, daily report — ellam app-la'}
                {unreadCount > 0 && (
                  <span className="ml-2 text-kv-sage font-semibold">{unreadCount} new</span>
                )}
              </p>
            </div>
            {unreadCount > 0 && (
              <button
                type="button"
                onClick={onMarkAllRead}
                className="text-xs font-semibold text-kv-sage hover:text-kv-forest"
              >
                {isEn ? 'Mark all read' : 'Ellam read'}
              </button>
            )}
          </div>
        </header>

        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2">
          {loading && notifications.length === 0 && (
            <p className="text-sm text-gray-500 text-center py-8">{isEn ? 'Loading…' : 'Loading…'}</p>
          )}
          {!loading && notifications.length === 0 && (
            <div className="text-center py-12 px-4">
              <p className="text-4xl mb-3">✓</p>
              <p className="text-sm font-medium text-kv-forest">{isEn ? 'All clear!' : 'Ellam safe!'}</p>
              <p className="text-xs text-gray-500 mt-1">
                {isEn ? 'No alerts for your farm right now.' : 'Ippove alert illa.'}
              </p>
            </div>
          )}
          {notifications.map((n) => {
            const cat = CATEGORY_META[n.category] || CATEGORY_META.weather
            const unread = !readIds.has(n.id)
            const title = isEn ? n.title_en : n.title_ta
            const message = isEn ? n.message_en : n.message_ta
            const action = isEn ? n.action_en : n.action_ta

            return (
              <article
                key={n.id}
                className={`rounded-xl border p-3 transition ${SEVERITY_STYLES[n.severity] || ''} ${
                  unread ? 'bg-white shadow-sm' : 'bg-gray-50/80 opacity-80'
                }`}
                onClick={() => onMarkRead(n.id)}
              >
                <div className="flex items-start gap-2">
                  <span className={`text-xs px-2 py-0.5 rounded-full border shrink-0 ${cat.color}`}>
                    {cat.icon} {isEn ? cat.en : cat.ta}
                  </span>
                  {unread && <span className="w-2 h-2 rounded-full bg-kv-sage shrink-0 mt-1.5" title="New" />}
                </div>
                <h3 className="text-sm font-semibold text-gray-900 mt-2">{title}</h3>
                <p className="text-xs text-gray-600 mt-1 leading-relaxed">{message}</p>
                {action && (
                  <p className="text-xs font-medium text-kv-forest mt-2">{action}</p>
                )}
                <div className="flex items-center justify-between mt-2">
                  <span className={`text-[10px] uppercase font-bold ${
                    n.severity === 'high' ? 'text-red-600' : n.severity === 'medium' ? 'text-amber-600' : 'text-gray-400'
                  }`}
                  >
                    {n.severity}
                  </span>
                  {onSpeak && (
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); onSpeak(isEn ? n.spoken_en : n.spoken_ta, isEn ? 'English' : 'Tamil') }}
                      className="text-[10px] font-semibold text-kv-sage hover:text-kv-forest"
                    >
                      🔊 {isEn ? 'Listen' : 'Kekunga'}
                    </button>
                  )}
                </div>
              </article>
            )
          })}
        </div>

        <footer className="px-5 py-3 border-t border-kv-beige text-[10px] text-gray-400 text-center shrink-0">
          {isEn ? 'Updates every 3 min · SMS alerts coming later' : '3 min-ku oru murai update · SMS later'}
        </footer>
      </aside>
    </div>
  )
}

import { MenuIcon, SunIcon } from '../icons'

export default function DashboardHeader({
  onToggleSidebar,
  displayName,
  username,
  parcel,
  crop,
  weather,
  isListening,
  isSpeaking,
  alertCount,
  onNotifications,
  onReports,
  inCall,
}) {
  const name = displayName?.split('—')[0]?.trim() || displayName || username || 'Farmer'
  const location = parcel
    ? `${parcel.village || parcel.land_name || parcel.district}, TN`
    : weather?.location || 'Tamil Nadu'

  return (
    <header className="flex items-center gap-3 px-4 py-3 border-b border-kv-beige bg-white/80 backdrop-blur shrink-0">
      <button
        type="button"
        onClick={onToggleSidebar}
        className="p-2 rounded-lg hover:bg-kv-creamDark text-gray-500 lg:hidden"
        aria-label="Toggle menu"
      >
        <MenuIcon />
      </button>

      <div className="min-w-0 flex-1">
        <h1 className="text-base font-semibold text-kv-forest truncate">
          Welcome, {name}
        </h1>
        <p className="text-xs text-gray-500 truncate">
          {crop ? `${crop} · ` : ''}{location}
        </p>
      </div>

      <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full bg-sky-50 text-sky-800 text-xs font-medium">
        <SunIcon className="w-3.5 h-3.5" />
        {weather?.temp != null ? `${weather.temp}°C` : '—'} · {location.split(',')[0]}
      </div>

      {(isListening || isSpeaking || inCall) && (
        <span className="px-2.5 py-1 rounded-full bg-kv-sageLight text-kv-forest text-xs font-medium animate-pulse">
          {inCall ? 'On call' : isListening ? 'Listening…' : 'Speaking…'}
        </span>
      )}

      <button
        type="button"
        onClick={onReports}
        className="hidden md:block px-3 py-1.5 rounded-lg text-xs font-medium text-kv-forest hover:bg-kv-creamDark transition"
      >
        Farm report
      </button>

      <button
        type="button"
        onClick={onNotifications}
        className="relative p-2 rounded-lg hover:bg-kv-creamDark text-gray-500 transition"
        aria-label="Notifications"
      >
        <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
          <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 01-3.46 0" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        {alertCount > 0 && (
          <span className="absolute top-1 right-1 w-4 h-4 rounded-full bg-red-500 text-white text-[10px] font-bold flex items-center justify-center">
            {alertCount > 9 ? '9+' : alertCount}
          </span>
        )}
      </button>
    </header>
  )
}

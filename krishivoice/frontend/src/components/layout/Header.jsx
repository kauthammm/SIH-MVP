import { BellIcon, MenuIcon, SproutIcon, SunIcon } from '../icons'

const MODES = [
  { id: 'chat', en: 'Chat', ta: 'Chat' },
  { id: 'voice', en: 'Voice', ta: 'Voice' },
  { id: 'field', en: 'My Field', ta: 'என் வயல்' },
]

export default function Header({
  onToggleSidebar,
  activeMode,
  onModeChange,
  language,
  weather,
  isListening,
  isSpeaking,
  lastDetected,
  onProfile,
  onNotifications,
  onReports,
  alertCount = 0,
  inCall = false,
}) {
  const isEn = language === 'English'

  return (
    <header className="sticky top-0 z-20 flex items-center justify-between gap-4 px-4 md:px-6 py-3 bg-kv-cream/80 backdrop-blur-md border-b border-kv-beige/60 shrink-0">
      <button
        type="button"
        onClick={onToggleSidebar}
        className="p-2 rounded-xl text-gray-500 hover:bg-kv-creamDark lg:hidden"
        aria-label="Menu"
      >
        <MenuIcon />
      </button>

      {/* Center mode pills */}
      <div className="flex-1 flex justify-center">
        <div className="inline-flex items-center p-1 rounded-full bg-kv-creamDark/80 border border-kv-beige">
          {MODES.map(({ id, en, ta }) => (
            <button
              key={id}
              type="button"
              onClick={() => onModeChange(id)}
              className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-all ${
                activeMode === id
                  ? 'bg-white text-kv-forest shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {isEn ? en : ta}
            </button>
          ))}
        </div>
      </div>

      {/* Right utilities */}
      <div className="flex items-center gap-2 md:gap-3 shrink-0">
        {inCall && (
          <span className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-kv-forest text-white text-xs font-semibold animate-pulse">
            <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
            Call
          </span>
        )}
        {isListening && (
          <span className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-red-50 text-red-600 text-xs font-medium animate-pulse">
            <span className="w-1.5 h-1.5 rounded-full bg-red-500" />
            {isEn ? 'Listening' : 'கேட்கிறேன்'}
          </span>
        )}        {isSpeaking && !isListening && (
          <span className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-kv-sageLight text-kv-forest text-xs font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-kv-sage animate-pulse" />
            {lastDetected === 'English' ? 'Speaking' : 'பேசுகிறேன்'}
          </span>
        )}

        {weather && (
          <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white border border-kv-beige text-xs">
            <SunIcon className="w-4 h-4 text-amber-500" />
            <span className="font-semibold text-gray-800">{weather.temp}°C</span>
            <span className="text-gray-400">·</span>
            <span className="text-gray-600 truncate max-w-[100px]">{weather.location}</span>
          </div>
        )}

        <button
          type="button"
          onClick={onReports}
          className="hidden sm:flex items-center gap-1 px-2.5 py-1.5 rounded-xl text-xs font-semibold text-kv-forest hover:bg-white border border-transparent hover:border-kv-beige transition"
          aria-label="Farm reports"
        >
          📊 {isEn ? 'Reports' : 'அறிக்கை'}
        </button>

        <button
          type="button"
          onClick={onNotifications}
          className="relative p-2 rounded-xl text-gray-500 hover:bg-white hover:text-kv-forest border border-transparent hover:border-kv-beige transition"
          aria-label="Weather alerts"
        >
          <BellIcon className="w-5 h-5" />
          {alertCount > 0 && (
            <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 rounded-full bg-red-500 text-white text-[10px] font-bold flex items-center justify-center">
              {alertCount}
            </span>
          )}
        </button>

        <button
          type="button"
          onClick={onProfile}
          className="w-9 h-9 rounded-xl bg-kv-forest text-kv-sageLight flex items-center justify-center hover:bg-kv-forestDark transition shadow-sm"
          aria-label="Profile"
        >
          <SproutIcon className="w-4 h-4" />
        </button>
      </div>
    </header>
  )
}

import {
  AdviceIcon, ChatIcon, ChevronDownIcon, CropIcon, MarketIcon,
  PlusIcon, RecordsIcon, SchemeIcon, SettingsIcon, SproutIcon, WeatherIcon,
} from '../icons'
import { formatRelativeTime } from '../../utils/chatHistory'

const NAV = [
  { id: 'chat', icon: ChatIcon, en: 'Chat', ta: 'Chat' },
  { id: 'crops', icon: CropIcon, en: 'My Crops', ta: 'என் பயிர்கள்' },
  { id: 'weather', icon: WeatherIcon, en: 'Weather', ta: 'வானிலை' },
  { id: 'market', icon: MarketIcon, en: 'Market Rates', ta: 'சந்தை விலை' },
  { id: 'advice', icon: AdviceIcon, en: 'Advice', ta: 'ஆலோசனை' },
  { id: 'schemes', icon: SchemeIcon, en: 'Schemes', ta: 'திட்டங்கள்' },
  { id: 'records', icon: RecordsIcon, en: 'Records', ta: 'பதிவுகள்' },
  { id: 'settings', icon: SettingsIcon, en: 'Settings', ta: 'Settings' },
]

export default function Sidebar({
  open,
  isGuest,
  isUserAuth,
  displayName,
  farmerId,
  parcel,
  language,
  activeNav,
  recentChats,
  conversations = [],
  activeConversationId,
  onNav,
  onNewChat,
  onLogin,
  onProfile,
  onRecentChat,
  onSelectConversation,
}) {
  const isEn = language === 'English'
  const farmerName = isGuest
    ? (isEn ? 'Guest Farmer' : 'Guest விவசாயி')
    : (displayName?.split('—')[0]?.trim() || displayName || farmerId)
  const location = isGuest
    ? (isEn ? 'Tamil Nadu, India' : 'தமிழ்நாடு, இந்தியா')
    : parcel
      ? `${parcel.village || parcel.district}, TN`
      : (isEn ? 'Tamil Nadu, India' : 'தமிழ்நாடு')

  const chatItems = isUserAuth ? conversations : recentChats

  return (
    <aside
      className={`${open ? 'w-[240px] xl:w-[260px]' : 'w-0'} flex-shrink-0 bg-kv-cream border-r border-kv-beige transition-all duration-300 overflow-hidden flex flex-col`}
    >
      <div className="px-4 pt-5 pb-4">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-kv-forest flex items-center justify-center text-kv-sageLight">
            <SproutIcon className="w-5 h-5" />
          </div>
          <div>
            <p className="font-bold text-kv-forest text-[15px] leading-tight">KrishiVoice</p>
            <p className="text-[11px] text-kv-sage leading-tight">
              {isEn ? 'Your farming companion' : 'உங்கள் விவசாய துணை'}
            </p>
          </div>
        </div>
      </div>

      <div className="px-3 mb-3">
        <button
          type="button"
          onClick={onNewChat}
          className="flex items-center justify-center gap-2 w-full px-4 py-2.5 rounded-xl bg-kv-forest hover:bg-kv-forestDark text-white text-sm font-semibold shadow-card transition-colors"
        >
          <PlusIcon className="w-4 h-4" />
          {isEn ? 'New Chat' : 'புதிய Chat'}
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 space-y-0.5">
        {NAV.map(({ id, icon: Icon, en, ta }) => (
          <button
            key={id}
            type="button"
            onClick={() => onNav(id)}
            className={`flex items-center gap-3 w-full px-3 py-2.5 rounded-xl text-sm transition-colors ${
              activeNav === id
                ? 'nav-item-active'
                : 'text-gray-600 hover:bg-kv-creamDark hover:text-kv-forest'
            }`}
          >
            <Icon className="w-[18px] h-[18px] shrink-0 opacity-80" />
            <span>{isEn ? en : ta}</span>
          </button>
        ))}

        {chatItems.length > 0 ? (
          <div className="mt-5 pt-4 border-t border-kv-beige">
            <p className="text-[11px] font-semibold text-gray-400 px-3 mb-2 uppercase tracking-wide">
              {isEn ? 'Recent chats' : 'சமீப chat'}
            </p>
            <div className="space-y-0.5">
              {chatItems.slice(0, 4).map((c) => (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => onRecentChat(c.title)}
                  className="w-full text-left px-3 py-2 rounded-xl hover:bg-kv-creamDark transition group"
                >
                  <p className="text-xs text-gray-700 truncate group-hover:text-kv-forest">{c.title}</p>
                  {c.time && (
                    <p className="text-[10px] text-gray-400 mt-0.5">
                      {formatRelativeTime(c.time, language)}
                    </p>
                  )}
                </button>
              ))}
            </div>
          </div>
        ) : isGuest ? (
          <div className="mt-5 pt-4 border-t border-kv-beige px-3">
            <p className="text-xs text-gray-500 mb-2">{isEn ? 'Save your chat history' : 'Chat history save பண்ண'}</p>
            <button
              type="button"
              onClick={onLogin}
              className="w-full py-2 rounded-xl border border-kv-sage text-kv-forest text-xs font-semibold hover:bg-kv-sageLight transition"
            >
              {isEn ? 'Sign in' : 'Sign in'}
            </button>
          </div>
        ) : null}
      </nav>

      <div className="p-3 border-t border-kv-beige">
        {isGuest ? (
          <button
            type="button"
            onClick={onLogin}
            className="flex items-center gap-3 w-full px-3 py-2.5 rounded-2xl bg-kv-forest text-white hover:bg-kv-forestDark transition text-left"
          >
            <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center font-bold text-sm shrink-0">
              →
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold">{isEn ? 'Sign in' : 'Sign in'}</p>
              <p className="text-[11px] text-white/70">{isEn ? 'Save chats & farm profile' : 'Chat & profile save'}</p>
            </div>
          </button>
        ) : (
          <button
            type="button"
            onClick={onProfile}
            className="flex items-center gap-3 w-full px-3 py-2.5 rounded-2xl hover:bg-kv-creamDark transition text-left group"
          >
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-kv-gold to-kv-sage overflow-hidden shrink-0 ring-2 ring-white shadow-sm flex items-center justify-center text-white font-bold text-sm">
              {farmerName[0]?.toUpperCase() || 'F'}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-gray-800 truncate">{farmerName}</p>
              <p className="text-[11px] text-gray-500 truncate">{location}</p>
            </div>
            <ChevronDownIcon className="w-4 h-4 text-gray-400 group-hover:text-kv-forest shrink-0" />
          </button>
        )}
      </div>
    </aside>
  )
}

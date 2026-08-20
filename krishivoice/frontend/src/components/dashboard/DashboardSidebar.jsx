import {
  AdviceIcon, ChatIcon, CropIcon, LogoutIcon, MarketIcon, PlusIcon,
  RecordsIcon, SchemeIcon, SettingsIcon, SproutIcon, WeatherIcon,
} from '../icons'
import { formatRelativeTime } from '../../utils/chatHistory'

const NAV = [
  { id: 'chat', icon: ChatIcon, label: 'Assistant' },
  { id: 'weather', icon: WeatherIcon, label: 'Weather' },
  { id: 'market', icon: MarketIcon, label: 'Market' },
  { id: 'advice', icon: AdviceIcon, label: 'Advice' },
  { id: 'schemes', icon: SchemeIcon, label: 'Schemes' },
  { id: 'records', icon: RecordsIcon, label: 'My Farm' },
  { id: 'settings', icon: SettingsIcon, label: 'Settings' },
]

export default function DashboardSidebar({
  open,
  displayName,
  username,
  farmerId,
  parcel,
  conversations,
  activeConversationId,
  activeNav,
  onNav,
  onNewChat,
  onSelectConversation,
  onProfile,
  onLogout,
}) {
  const name = displayName?.split('—')[0]?.trim() || displayName || username || 'Farmer'
  const location = parcel
    ? `${parcel.village || parcel.land_name || parcel.district}, TN`
    : 'Tamil Nadu'

  return (
    <aside
      className={`${open ? 'w-[260px]' : 'w-0'} flex-shrink-0 bg-[#171717] text-gray-100 transition-all duration-300 overflow-hidden flex flex-col`}
    >
      <div className="p-4 border-b border-white/10">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-kv-sage flex items-center justify-center">
            <SproutIcon className="w-4 h-4 text-white" />
          </div>
          <span className="font-semibold text-[15px]">KrishiVoice</span>
        </div>
      </div>

      <div className="p-3">
        <button
          type="button"
          onClick={onNewChat}
          className="flex items-center gap-2.5 w-full px-3 py-2.5 rounded-lg border border-white/15 hover:bg-white/10 text-sm font-medium transition"
        >
          <PlusIcon className="w-4 h-4" />
          New chat
        </button>
      </div>

      {conversations.length > 0 && (
        <div className="flex-1 overflow-y-auto px-2 pb-2 min-h-0">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-500 px-2 mb-2">Recent</p>
          <div className="space-y-0.5">
            {conversations.slice(0, 12).map((c) => (
              <button
                key={c.id}
                type="button"
                onClick={() => onSelectConversation?.(c.id)}
                className={`w-full text-left px-3 py-2.5 rounded-lg text-sm transition truncate ${
                  c.id === activeConversationId
                    ? 'bg-white/15 text-white'
                    : 'text-gray-400 hover:bg-white/8 hover:text-gray-200'
                }`}
                title={c.title}
              >
                <span className="block truncate">{c.title}</span>
                {c.updated_at && (
                  <span className="text-[10px] text-gray-500 mt-0.5 block">
                    {formatRelativeTime(Date.parse(c.updated_at), 'English')}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>
      )}

      <nav className={`${conversations.length ? 'border-t border-white/10' : 'flex-1'} px-2 py-3 space-y-0.5`}>
        {NAV.map(({ id, icon: Icon, label }) => (
          <button
            key={id}
            type="button"
            onClick={() => onNav(id)}
            className={`flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm transition ${
              activeNav === id ? 'bg-white/12 text-white' : 'text-gray-400 hover:bg-white/8 hover:text-gray-200'
            }`}
          >
            <Icon className="w-[17px] h-[17px] opacity-80" />
            {label}
          </button>
        ))}
      </nav>

      <div className="p-3 border-t border-white/10 mt-auto">
        <button
          type="button"
          onClick={onProfile}
          className="flex items-center gap-3 w-full px-2 py-2 rounded-lg hover:bg-white/8 transition text-left mb-1"
        >
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-kv-gold to-kv-sage flex items-center justify-center text-white font-bold text-sm shrink-0">
            {name[0]?.toUpperCase() || 'F'}
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium truncate">{name}</p>
            <p className="text-[11px] text-gray-500 truncate">
              {farmerId ? `${farmerId} · ` : ''}{location}
            </p>
          </div>
        </button>
        <button
          type="button"
          onClick={onLogout}
          className="flex items-center gap-2 w-full px-3 py-2 rounded-lg text-sm text-gray-400 hover:bg-white/8 hover:text-red-300 transition"
        >
          <LogoutIcon className="w-4 h-4" />
          Sign out
        </button>
      </div>
    </aside>
  )
}

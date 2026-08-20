import { FieldIcon, SoilIcon, SparkleIcon, VoiceIcon, WeatherIcon } from '../icons'

const FEATURES = {
  guest: [
    {
      icon: SparkleIcon,
      title: 'Instant answers',
      desc: 'General Tamil Nadu farming guidance — no login required',
      accent: 'from-violet-500/10 to-purple-500/5 border-violet-200/60',
      iconColor: 'text-violet-600',
    },
    {
      icon: VoiceIcon,
      title: 'Voice & text',
      desc: 'Speak or type in Tamil or English — natural voice replies',
      accent: 'from-emerald-500/10 to-green-500/5 border-emerald-200/60',
      iconColor: 'text-emerald-600',
    },
    {
      icon: FieldIcon,
      title: 'Login to personalize',
      desc: 'Add your farm location & soil test for field-specific advice',
      accent: 'from-amber-500/10 to-orange-500/5 border-amber-200/60',
      iconColor: 'text-amber-600',
    },
    {
      icon: WeatherIcon,
      title: 'Live weather',
      desc: 'Weather-aware irrigation when you connect your parcel',
      accent: 'from-sky-500/10 to-blue-500/5 border-sky-200/60',
      iconColor: 'text-sky-600',
    },
  ],
  personalized: [
    {
      icon: FieldIcon,
      title: 'Your parcel',
      desc: 'Advice tailored to your selected land parcel & location',
      accent: 'from-emerald-500/10 to-green-500/5 border-emerald-200/60',
      iconColor: 'text-emerald-600',
    },
    {
      icon: SoilIcon,
      title: 'Soil test data',
      desc: 'Custom pH, NPK & moisture from your farm profile',
      accent: 'from-amber-500/10 to-yellow-500/5 border-amber-200/60',
      iconColor: 'text-amber-700',
    },
    {
      icon: WeatherIcon,
      title: 'Live weather',
      desc: 'Open-Meteo forecasts at your farm coordinates',
      accent: 'from-sky-500/10 to-blue-500/5 border-sky-200/60',
      iconColor: 'text-sky-600',
    },
    {
      icon: VoiceIcon,
      title: 'Tamil voice',
      desc: 'Natural Tamil speech via Edge TTS — tap Listen on any reply',
      accent: 'from-violet-500/10 to-purple-500/5 border-violet-200/60',
      iconColor: 'text-violet-600',
    },
  ],
}

export default function WelcomeScreen({
  isGuest,
  language,
  suggestions,
  onSuggestion,
  onLogin,
  onProfile,
  hasCustomProfile,
}) {
  const features = FEATURES[isGuest ? 'guest' : 'personalized']
  const isEn = language === 'English'

  return (
    <div className="flex flex-col items-center justify-center min-h-full px-4 py-10 md:py-16 animate-fade-in">
      <div className="max-w-2xl w-full text-center">
        {/* Logo mark */}
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br from-emerald-500 to-emerald-700 text-white shadow-lg shadow-emerald-500/20 mb-6">
          <SparkleIcon className="w-7 h-7" />
        </div>

        <h1 className="text-2xl md:text-3xl font-semibold text-gray-900 tracking-tight mb-2">
          {isGuest
            ? (isEn ? 'How can I help with farming today?' : 'இன்று விவசாயத்தில் என்ன உதவி வேண்டும்?')
            : (isEn ? 'Your field advisor is ready' : 'உங்கள் வயல் ஆலோசகர் தயார்')}
        </h1>

        <p className="text-gray-500 text-sm md:text-[15px] leading-relaxed max-w-lg mx-auto mb-8">
          {isGuest ? (
            isEn ? (
              <>Ask in <strong className="text-gray-700">Tamil</strong> or <strong className="text-gray-700">English</strong> for general guidance.{' '}
                <button type="button" onClick={onLogin} className="text-emerald-600 font-medium hover:underline">Sign in</button>
                {' '}for personalized advice.</>
            ) : (
              <>பொதுவான ஆலோசனைக்கு <strong className="text-gray-700">தமிழ்</strong> அல்லது <strong className="text-gray-700">English</strong>-ல் கேளுங்கள்.{' '}
                <button type="button" onClick={onLogin} className="text-emerald-600 font-medium hover:underline">Login</button>
                {' '}செய்தால் உங்கள் வயலுக்கான custom reply.</>
            )
          ) : (
            isEn ? (
              <>Using your parcel data{hasCustomProfile ? ' & custom soil test' : ''}.{' '}
                <button type="button" onClick={onProfile} className="text-emerald-600 font-medium hover:underline">Update farm profile</button>
                {' '}anytime.</>
            ) : (
              <>உங்கள் parcel data{hasCustomProfile ? ' & soil test' : ''} use பண்ணுது.{' '}
                <button type="button" onClick={onProfile} className="text-emerald-600 font-medium hover:underline">Farm profile</button>
                {' '}update பண்ணலாம்.</>
            )
          )}
        </p>

        {/* Feature grid — Claude-style cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-8 text-left">
          {features.map(({ icon: Icon, title, desc, accent, iconColor }) => (
            <div
              key={title}
              className={`rounded-xl border bg-gradient-to-br ${accent} p-4 transition hover:shadow-card`}
            >
              <div className={`inline-flex p-2 rounded-lg bg-white/80 mb-2.5 ${iconColor}`}>
                <Icon className="w-4 h-4" />
              </div>
              <p className="text-sm font-semibold text-gray-900 mb-0.5">{title}</p>
              <p className="text-xs text-gray-500 leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>

        {/* Suggestion pills — ChatGPT style */}
        <p className="text-[11px] font-semibold uppercase tracking-widest text-gray-400 mb-3">
          {isEn ? 'Try asking' : 'இதை கேட்டுப் பாருங்க'}
        </p>
        <div className="flex flex-col gap-2">
          {suggestions.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => onSuggestion(s)}
              className="group w-full text-left px-4 py-3.5 rounded-xl border border-gray-200 bg-white hover:border-emerald-300 hover:bg-emerald-50/30 text-sm text-gray-700 transition-all duration-200 shadow-sm hover:shadow-card"
            >
              <span className="flex items-center justify-between gap-3">
                <span className="leading-relaxed">{s}</span>
                <span className="text-gray-300 group-hover:text-emerald-500 transition-colors shrink-0">→</span>
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

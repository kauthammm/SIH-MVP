import HeroSearchBar from './HeroSearchBar'
import { AdviceIcon, CropIcon, MarketIcon, SchemeIcon, WeatherIcon } from '../icons'

const QUICK_ACTIONS = [
  {
    id: 'crop',
    icon: CropIcon,
    color: 'bg-emerald-50 text-emerald-700',
    en: { title: 'Crop Advice', desc: 'Get AI advice for your crop' },
    ta: { title: 'பயிர் ஆலோசனை', desc: 'உங்கள் பயிருக்கு AI advice' },
    query: { en: 'I am planting rice — how much water and fertilizer?', ta: 'நெல் விதைக்கிறேன் — எவ்வளவு தண்ணீர், உரம்?' },
  },
  {
    id: 'weather',
    icon: WeatherIcon,
    color: 'bg-sky-50 text-sky-700',
    en: { title: 'Weather Info', desc: 'Precise forecast for your area' },
    ta: { title: 'வானிலை', desc: 'உங்கள் area-வுக்கு exact forecast' },
    query: { en: 'Will it rain tomorrow?', ta: 'நாளைக்கு மழை வருமா?' },
  },
  {
    id: 'market',
    icon: MarketIcon,
    color: 'bg-amber-50 text-amber-700',
    en: { title: 'Market Rates', desc: "Today's mandi prices" },
    ta: { title: 'சந்தை விலை', desc: 'இன்றைய mandi rate' },
    query: { en: 'What are current paddy market rates in Tamil Nadu?', ta: 'நெல் market rate என்ன?' },
  },
  {
    id: 'schemes',
    icon: SchemeIcon,
    color: 'bg-violet-50 text-violet-700',
    en: { title: 'Govt. Schemes', desc: 'Farmer scheme information' },
    ta: { title: 'அரசு திட்டம்', desc: 'விவசாயி scheme info' },
    query: { en: 'What government schemes are available for farmers?', ta: 'விவசாயிகளுக்கு என்ன govt scheme irukku?' },
  },
]

const TIPS = {
  en: 'Just speak naturally — say "I am planting rice" or "my field is dry". KrishiVoice learns your crop and gives specific water, fertilizer & weather advice.',
  ta: 'இயல்பா பேசுங்க — "நெல் விதைக்கிறேன்" or "வயல் வறண்டது" சொல்லுங்க. KrishiVoice record பண்ணி exact advice கொடுக்கும்.',
}

export default function HeroDashboard({
  isGuest,
  isUserAuth = false,
  displayName,
  username,
  farmerId,
  parcel,
  weather,
  language,
  input,
  setInput,
  onSend,
  onMic,
  thinking,
  isListening,
  isSupported,
  inputRef,
  onKeyDown,
  onQuickAction,
  onUploadSoil,
  onLogin,
  onStartCall,
  inCall,
  webSearchEnabled,
  onToggleWebSearch,
}) {
  const isEn = language === 'English'
  const firstName = isGuest
    ? (isEn ? 'Farmer' : 'விவசாயி')
    : (displayName?.split('—')[0]?.replace('Demo Farmer', '').trim() || displayName?.split(' ')[0] || username || farmerId || 'Farmer')

  const greeting = isUserAuth
    ? (isEn ? `Welcome back, ${firstName}` : `மீண்டும் வரவேற்கிறோம், ${firstName}`)
    : (isEn ? `Vanakkam, ${firstName},` : `வணக்கம் ${firstName},`)

  const sub = isUserAuth
    ? (isEn ? 'Your farm dashboard — ask anything by voice or text.' : 'உங்கள் farm dashboard — voice or text-ல கேளுங்க.')
    : (isEn ? 'How can we help you today?' : 'இன்று நாம் உங்களுக்கு எப்படி உதவலாம்?')

  return (
    <div className="hero-field-bg min-h-full flex flex-col">
      <div className="flex-1 flex flex-col items-center px-4 md:px-8 pt-8 md:pt-14 pb-6">
        {/* Greeting */}
        <div className="text-center mb-8 md:mb-10 animate-fade-in">
          <h1 className="text-3xl md:text-[2.5rem] font-bold text-kv-forest leading-tight tracking-tight">
            {greeting}
          </h1>
          <p className="text-base md:text-lg text-gray-600 mt-2 font-medium">{sub}</p>
          {isGuest && (
            <button
              type="button"
              onClick={onLogin}
              className="mt-4 inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-kv-forest text-white text-sm font-semibold hover:bg-kv-forestDark shadow-card transition"
            >
              {isEn ? 'Sign in to your account' : 'Account-ல sign in'}
            </button>
          )}
          {isUserAuth && parcel && (
            <div className="mt-5 flex flex-wrap justify-center gap-2">
              {parcel.crop && (
                <span className="px-3 py-1 rounded-full bg-emerald-50 text-emerald-800 text-xs font-medium border border-emerald-100">
                  {parcel.crop}
                </span>
              )}
              {(parcel.village || parcel.district) && (
                <span className="px-3 py-1 rounded-full bg-sky-50 text-sky-800 text-xs font-medium border border-sky-100">
                  {parcel.village || parcel.district}, TN
                </span>
              )}
              {weather?.temp != null && (
                <span className="px-3 py-1 rounded-full bg-amber-50 text-amber-800 text-xs font-medium border border-amber-100">
                  {weather.temp}°C today
                </span>
              )}
            </div>
          )}
        </div>

        {/* Hero search */}
        <div className="w-full mb-6 animate-fade-in" style={{ animationDelay: '0.05s' }}>
          <HeroSearchBar
            input={input}
            setInput={setInput}
            onSend={onSend}
            onMic={onMic}
            thinking={thinking}
            isListening={isListening}
            isSupported={isSupported}
            language={language}
            inputRef={inputRef}
            onKeyDown={onKeyDown}
            isGuest={isGuest}
            onUploadSoil={onUploadSoil}
            webSearchEnabled={webSearchEnabled}
            onToggleWebSearch={onToggleWebSearch}
          />
        </div>

        {/* Call assistant CTA */}
        {onStartCall && (
          <div className="w-full max-w-3xl mx-auto mb-8 animate-fade-in">
            <button
              type="button"
              onClick={onStartCall}
              disabled={inCall}
              className="w-full flex items-center justify-center gap-3 py-4 rounded-2xl bg-kv-forest hover:bg-kv-forestDark disabled:opacity-60 text-white font-semibold shadow-lg transition"
            >
              <span className="text-xl">📞</span>
              {inCall
                ? (isEn ? 'Call in progress…' : 'Call ongoing…')
                : (isEn ? 'Start voice call — auto weather alerts' : 'Voice call start — auto weather alert')}
            </button>
            <p className="text-center text-xs text-gray-500 mt-2">
              {isEn
                ? 'Hands-free: speaks weather briefing, then listens for your questions'
                : 'Hands-free: weather briefing பேசும், அப்புறம் உங்க questions-ku answer'}
            </p>
          </div>
        )}

        {/* Quick start grid */}
        <div className="w-full max-w-3xl animate-fade-in" style={{ animationDelay: '0.1s' }}>
          <p className="text-sm font-semibold text-gray-700 mb-3 px-1">
            {isEn ? 'Get started quickly' : 'விரைவாக தொடங்குங்கள்'}
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {QUICK_ACTIONS.map(({ id, icon: Icon, color, en, ta, query }) => {
              const labels = isEn ? en : ta
              const q = isEn ? query.en : query.ta
              return (
                <button
                  key={id}
                  type="button"
                  onClick={() => onQuickAction(q)}
                  className="flex items-start gap-3 p-4 rounded-2xl bg-kv-wheat/60 hover:bg-kv-wheat border border-kv-beige/80 text-left transition-all hover:shadow-card group"
                >
                  <div className={`p-2.5 rounded-xl ${color} shrink-0`}>
                    <Icon className="w-5 h-5" />
                  </div>
                  <div>
                    <p className="text-sm font-bold text-gray-800 group-hover:text-kv-forest">{labels.title}</p>
                    <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">{labels.desc}</p>
                  </div>
                </button>
              )
            })}
          </div>
        </div>
      </div>

      {/* Tip of the day banner */}
      <div className="px-4 md:px-8 pb-6 md:pb-8 animate-fade-in" style={{ animationDelay: '0.15s' }}>
        <div className="max-w-3xl mx-auto rounded-2xl bg-gradient-to-r from-kv-sageLight/80 via-white to-kv-wheat/80 border border-kv-sageMuted/60 p-4 md:p-5 flex items-start gap-4 shadow-card">
          <div className="w-10 h-10 rounded-xl bg-kv-sage/20 flex items-center justify-center shrink-0">
            <AdviceIcon className="w-5 h-5 text-kv-forest" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-bold text-kv-forest uppercase tracking-wide mb-1">
              {isEn ? "Today's tip" : 'இன்றைய tip'}
            </p>
            <p className="text-sm text-gray-700 leading-relaxed">{isEn ? TIPS.en : TIPS.ta}</p>
          </div>
          <div className="hidden md:block text-4xl shrink-0 opacity-80" aria-hidden="true">🚜</div>
        </div>
      </div>
    </div>
  )
}

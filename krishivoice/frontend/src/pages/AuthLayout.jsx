import { SproutIcon } from '../components/icons'

const FEATURES = [
  { title: 'Voice-first advice', desc: 'Speak in Tamil or Tanglish — get crop, weather & market answers.' },
  { title: 'Your farm, remembered', desc: 'Location, crop and soil saved across every chat session.' },
  { title: 'Live weather reports', desc: 'Daily, weekly and monthly reports from your field GPS.' },
]

export default function AuthLayout({ title, subtitle, children, footer }) {
  return (
    <div className="min-h-screen flex bg-kv-cream">
      {/* Brand panel */}
      <div className="hidden lg:flex lg:w-[44%] xl:w-[48%] relative overflow-hidden bg-gradient-to-br from-kv-forest via-[#2d6a4f] to-kv-forestDark text-white flex-col justify-between p-10 xl:p-14">
        <div className="absolute inset-0 opacity-[0.07] pointer-events-none hero-field-bg" />
        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-12">
            <div className="w-11 h-11 rounded-2xl bg-white/15 backdrop-blur flex items-center justify-center">
              <SproutIcon className="w-6 h-6 text-kv-sageLight" />
            </div>
            <div>
              <p className="font-bold text-xl tracking-tight">KrishiVoice</p>
              <p className="text-sm text-white/70">Field intelligence for Tamil Nadu farmers</p>
            </div>
          </div>
          <h1 className="text-3xl xl:text-4xl font-bold leading-tight max-w-md">
            {title}
          </h1>
          <p className="mt-4 text-white/75 text-base max-w-sm leading-relaxed">{subtitle}</p>
        </div>
        <ul className="relative z-10 space-y-5 mt-10">
          {FEATURES.map((f) => (
            <li key={f.title} className="flex gap-3">
              <span className="w-1.5 h-1.5 rounded-full bg-kv-sageMuted mt-2 shrink-0" />
              <div>
                <p className="font-semibold text-sm">{f.title}</p>
                <p className="text-sm text-white/65 mt-0.5">{f.desc}</p>
              </div>
            </li>
          ))}
        </ul>
        <p className="relative z-10 text-xs text-white/40 mt-8">© KrishiVoice · Smart India Hackathon</p>
      </div>

      {/* Form panel */}
      <div className="flex-1 flex flex-col justify-center px-6 py-10 sm:px-10 lg:px-16">
        <div className="lg:hidden flex items-center gap-2.5 mb-8">
          <div className="w-9 h-9 rounded-xl bg-kv-forest flex items-center justify-center text-kv-sageLight">
            <SproutIcon className="w-5 h-5" />
          </div>
          <span className="font-bold text-kv-forest text-lg">KrishiVoice</span>
        </div>
        <div className="w-full max-w-md mx-auto">
          {children}
          {footer && <div className="mt-8">{footer}</div>}
        </div>
      </div>
    </div>
  )
}

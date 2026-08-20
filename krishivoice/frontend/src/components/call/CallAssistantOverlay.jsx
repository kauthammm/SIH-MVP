import { MicIcon, StopIcon } from '../icons'

const STATUS_LABELS = {
  idle: { en: 'Ready', ta: 'Ready' },
  briefing: { en: 'Farm briefing…', ta: 'Farm update…' },
  listening: { en: 'Listening — speak now', ta: 'கேட்கிறேன் — பேசுங்க' },
  thinking: { en: 'Thinking…', ta: 'Process பண்ணுது…' },
  speaking: { en: 'Speaking…', ta: 'பேசுகிறேன்…' },
  alert: { en: 'Weather alert', ta: 'Weather alert' },
}

export default function CallAssistantOverlay({
  open,
  callStatus,
  alerts,
  language,
  onEndCall,
  highCount,
}) {
  if (!open) return null

  const isEn = language === 'English'
  const status = STATUS_LABELS[callStatus] || STATUS_LABELS.idle
  const highAlerts = alerts.filter((a) => a.severity === 'high')

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4 bg-kv-forest/40 backdrop-blur-sm">
      <div className="w-full max-w-md bg-white rounded-3xl shadow-elevated overflow-hidden animate-fade-in">
        <div className="px-6 pt-8 pb-6 text-center bg-gradient-to-b from-kv-sageLight/50 to-white">
          <div className="relative mx-auto w-24 h-24 mb-4">
            <span className={`absolute inset-0 rounded-full bg-kv-sage/20 ${callStatus === 'listening' ? 'animate-ping' : ''}`} />
            <span className="relative flex items-center justify-center w-24 h-24 rounded-full bg-kv-forest text-white shadow-lg">
              {callStatus === 'listening' ? (
                <MicIcon className="w-10 h-10" />
              ) : (
                <span className="text-3xl">🌾</span>
              )}
            </span>
          </div>
          <h2 className="text-lg font-bold text-kv-forest">KrishiVoice Call</h2>
          <p className="text-sm text-kv-sage font-medium mt-1">
            {isEn ? status.en : status.ta}
          </p>
          <p className="text-xs text-gray-500 mt-2">
            {isEn
              ? 'Hands-free — speak after each reply. Weather alerts run automatically.'
              : 'Hands-free mode — reply-ku apram automatic-aa kekum. Weather alert auto varum.'}
          </p>
        </div>

        {(highCount > 0 || highAlerts.length > 0) && (
          <div className="mx-4 mb-4 p-3 rounded-2xl bg-amber-50 border border-amber-200 text-left">
            <p className="text-xs font-bold text-amber-800 uppercase tracking-wide mb-1">
              {isEn ? 'Active alerts' : 'Active alerts'} ({highCount || highAlerts.length})
            </p>
            <p className="text-sm text-amber-900 leading-relaxed">
              {isEn ? highAlerts[0]?.message_en : highAlerts[0]?.message_ta}
            </p>
          </div>
        )}

        <div className="px-6 pb-6">
          <button
            type="button"
            onClick={onEndCall}
            className="w-full flex items-center justify-center gap-2 py-3.5 rounded-2xl bg-red-500 hover:bg-red-600 text-white font-semibold transition shadow-sm"
          >
            <StopIcon className="w-4 h-4" />
            {isEn ? 'End call' : 'Call முடிக்க'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function AlertBanner({ alert, language, onDismiss, onOpenPanel, onSpeak }) {
  if (!alert) return null
  const isEn = language === 'English'
  const title = isEn ? alert.title_en : alert.title_ta
  const message = isEn ? alert.message_en : alert.message_ta

  return (
    <div className={`mx-4 mt-2 px-4 py-3 rounded-xl border flex items-start gap-3 shrink-0 ${
      alert.severity === 'high'
        ? 'bg-red-50 border-red-200 text-red-900'
        : 'bg-amber-50 border-amber-200 text-amber-900'
    }`}
    >
      <span className="text-lg shrink-0">{alert.severity === 'high' ? '⚠' : 'ℹ'}</span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold">{title}</p>
        <p className="text-xs mt-0.5 opacity-90 line-clamp-2">{message}</p>
        <div className="flex gap-3 mt-2">
          <button
            type="button"
            onClick={onOpenPanel}
            className="text-xs font-semibold underline hover:no-underline"
          >
            {isEn ? 'View all' : 'Ellam paaru'}
          </button>
          {onSpeak && (
            <button
              type="button"
              onClick={() => onSpeak(isEn ? alert.spoken_en : alert.spoken_ta, isEn ? 'English' : 'Tamil')}
              className="text-xs font-semibold underline hover:no-underline"
            >
              🔊 {isEn ? 'Listen' : 'Kekunga'}
            </button>
          )}
        </div>
      </div>
      <button
        type="button"
        onClick={onDismiss}
        className="text-gray-500 hover:text-gray-800 text-lg leading-none shrink-0"
        aria-label="Dismiss"
      >
        ×
      </button>
    </div>
  )
}

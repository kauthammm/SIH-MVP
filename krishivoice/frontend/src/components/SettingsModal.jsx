export default function SettingsModal({ open, onClose, language, onLanguageChange, autoSpeak, onAutoSpeakChange }) {
  if (!open) return null
  const isEn = language === 'English'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm">
      <div className="w-full max-w-sm bg-white rounded-2xl shadow-elevated border border-kv-beige overflow-hidden">
        <div className="px-5 py-4 border-b border-kv-beige flex items-center justify-between">
          <h2 className="font-semibold text-kv-forest">{isEn ? 'Settings' : 'Settings'}</h2>
          <button type="button" onClick={onClose} className="p-2 rounded-xl hover:bg-kv-creamDark text-gray-500">✕</button>
        </div>
        <div className="p-5 space-y-4">
          <div>
            <p className="text-xs font-semibold text-gray-500 mb-2">{isEn ? 'Language' : 'Language'}</p>
            <div className="flex gap-2">
              {['Auto', 'Tamil', 'English'].map((l) => (
                <button
                  key={l}
                  type="button"
                  onClick={() => onLanguageChange(l)}
                  className={`flex-1 py-2 rounded-xl text-xs font-semibold border transition ${
                    language === l ? 'bg-kv-sageLight border-kv-sage text-kv-forest' : 'border-kv-beige text-gray-600 hover:bg-kv-cream'
                  }`}
                >
                  {l}
                </button>
              ))}
            </div>
          </div>
          <label className="flex items-center gap-3 cursor-pointer">
            <input type="checkbox" checked={autoSpeak} onChange={(e) => onAutoSpeakChange(e.target.checked)} className="rounded text-kv-sage" />
            <span className="text-sm text-gray-700">{isEn ? 'Auto-speak responses' : 'Auto speak replies'}</span>
          </label>
        </div>
      </div>
    </div>
  )
}

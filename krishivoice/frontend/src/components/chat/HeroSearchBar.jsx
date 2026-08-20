import { GlobeIcon, LeafScanIcon, MicIcon, SendIcon, StopIcon } from '../icons'
import SoilPdfAttachButton from './SoilPdfAttachButton'

export default function HeroSearchBar({
  input,
  setInput,
  onSend,
  onMic,
  onUploadSoil,
  thinking,
  isListening,
  isSupported,
  language,
  inputRef,
  onKeyDown,
  isGuest,
  webSearchEnabled,
  onToggleWebSearch,
}) {
  const isEn = language === 'English'
  const placeholder = isEn
    ? 'What would you like to know?'
    : 'நீங்கள் என்ன தெரிஞ்சுக்கணும்?'
  const uploadTitle = isEn ? 'Upload soil test PDF' : 'Soil test PDF upload'
  const webTitle = webSearchEnabled
    ? (isEn ? 'Web search ON — click to use local advice' : 'Web search ON — local advice-ku click pannunga')
    : (isEn ? 'Search web (TNAU, ICAR, govt sites)' : 'Web search (TNAU, ICAR, govt sites)')

  return (
    <div className="w-full max-w-3xl mx-auto">
      <div className="bg-white rounded-2xl md:rounded-3xl shadow-input border border-kv-beige/80 overflow-hidden">
        <div className="px-4 md:px-5 pt-4 pb-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            rows={2}
            disabled={thinking}
            placeholder={placeholder}
            className="chat-input w-full bg-transparent resize-none text-base md:text-lg leading-relaxed placeholder:text-gray-400 disabled:opacity-50 min-h-[56px]"
          />
        </div>
        <div className="flex items-center justify-between gap-2 px-3 md:px-4 py-3 border-t border-kv-beige/60 bg-kv-cream/30">
          <div className="flex items-center gap-1">
            {onUploadSoil ? (
              <SoilPdfAttachButton onFile={onUploadSoil} disabled={thinking} title={uploadTitle} />
            ) : (
              <button type="button" className="p-2 rounded-xl text-gray-400 hover:text-kv-forest hover:bg-white transition" title="Attach">
                <span className="sr-only">Attach</span>
              </button>
            )}
            <button type="button" className="p-2 rounded-xl text-gray-400 hover:text-kv-forest hover:bg-white transition" title="Crop scan">
              <LeafScanIcon />
            </button>
            <button
              type="button"
              onClick={onToggleWebSearch}
              disabled={thinking}
              className={`p-2 rounded-xl transition disabled:opacity-40 ${
                webSearchEnabled
                  ? 'bg-sky-100 text-sky-700 ring-1 ring-sky-200'
                  : 'text-gray-400 hover:text-kv-forest hover:bg-white'
              }`}
              title={webTitle}
              aria-pressed={webSearchEnabled}
            >
              <GlobeIcon />
            </button>
            {isSupported && (
              <button
                type="button"
                onClick={onMic}
                disabled={thinking}
                title={isListening ? 'Stop' : 'Voice'}
                className={`relative p-2 rounded-xl transition disabled:opacity-40 ${
                  isListening ? 'mic-active bg-red-500 text-white' : 'text-gray-400 hover:text-kv-forest hover:bg-white'
                }`}
              >
                {isListening ? <StopIcon className="w-4 h-4" /> : <MicIcon className="w-4 h-4" />}
              </button>
            )}
          </div>
          <div className="flex items-center gap-2">
            <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-kv-creamDark border border-kv-beige text-xs font-medium text-gray-600">
              <span className={`w-1.5 h-1.5 rounded-full ${webSearchEnabled ? 'bg-sky-500' : 'bg-kv-sage'}`} />
              {webSearchEnabled ? (isEn ? 'Web search' : 'Web search') : 'Krishi AI 1.0'}
            </div>
            <button
              type="button"
              onClick={onSend}
              disabled={!input.trim() || thinking}
              className="w-10 h-10 rounded-full bg-kv-sage hover:bg-kv-forest text-white flex items-center justify-center disabled:opacity-30 transition shadow-sm"
            >
              <SendIcon className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

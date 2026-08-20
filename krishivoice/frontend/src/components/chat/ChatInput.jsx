import { GlobeIcon, MicIcon, SendIcon, StopIcon } from '../icons'
import SoilPdfAttachButton from './SoilPdfAttachButton'

export default function ChatInput({
  input,
  setInput,
  onSend,
  onMic,
  onUploadSoil,
  thinking,
  isListening,
  isSupported,
  isGuest,
  language,
  inputRef,
  onKeyDown,
  webSearchEnabled,
  onToggleWebSearch,
}) {
  const isEn = language === 'English'
  const placeholder = isGuest
    ? (isEn ? 'Ask anything — e.g. "How much water for rice?"' : 'எதுவும் கேளுங்க — "நெலுக்கு எவ்வளவு தண்ணீர்?"')
    : (isEn
      ? 'Speak naturally — "I am planting rice, field is dry, how much water?"'
      : 'இயல்பா பேசுங்க — "நெல் விதைக்கிறேன், வயல் வறண்டது, எவ்வளவு தண்ணீர்?"')

  const uploadTitle = isEn ? 'Upload soil test PDF' : 'Soil test PDF upload'
  const webTitle = webSearchEnabled
    ? (isEn ? 'Web search ON' : 'Web search ON')
    : (isEn ? 'Search web for answers' : 'Web-la search pannunga')

  return (
    <div className="shrink-0 bg-kv-cream border-t border-kv-beige px-4 pb-4 pt-3 md:pb-6">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-end gap-2 bg-white rounded-2xl border border-kv-beige shadow-input px-4 py-3 focus-within:border-kv-sage/50 focus-within:ring-2 focus-within:ring-kv-sageLight transition">
          {onUploadSoil && (
            <SoilPdfAttachButton
              onFile={onUploadSoil}
              disabled={thinking}
              className="mb-0.5 shrink-0 hover:bg-kv-creamDark"
              title={uploadTitle}
            />
          )}
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            rows={1}
            disabled={thinking}
            placeholder={placeholder}
            className="chat-input flex-1 bg-transparent resize-none text-[15px] leading-relaxed max-h-32 placeholder:text-gray-400 disabled:opacity-50 py-1"
          />
          <div className="flex items-center gap-1 pb-0.5 shrink-0">
            {onToggleWebSearch && (
              <button
                type="button"
                onClick={onToggleWebSearch}
                disabled={thinking}
                title={webTitle}
                aria-pressed={webSearchEnabled}
                className={`p-2.5 rounded-xl transition disabled:opacity-40 ${
                  webSearchEnabled
                    ? 'bg-sky-100 text-sky-700'
                    : 'text-gray-400 hover:bg-kv-creamDark'
                }`}
              >
                <GlobeIcon className="w-4 h-4" />
              </button>
            )}
            {isSupported && (
              <button
                type="button"
                onClick={onMic}
                disabled={thinking}
                className={`relative p-2.5 rounded-xl transition disabled:opacity-40 ${
                  isListening ? 'mic-active bg-red-500 text-white' : 'text-gray-400 hover:bg-kv-creamDark'
                }`}
              >
                {isListening ? <StopIcon className="w-4 h-4" /> : <MicIcon className="w-4 h-4" />}
              </button>
            )}
            <button
              type="button"
              onClick={onSend}
              disabled={!input.trim() || thinking}
              className="p-2.5 rounded-xl bg-kv-sage text-white disabled:opacity-30 hover:bg-kv-forest transition"
            >
              <SendIcon className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

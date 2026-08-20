import { useState } from 'react'
import StructuredAdvisory from './StructuredAdvisory'
import { CopyIcon, SpeakerIcon, SparkleIcon, UserIcon } from '../icons'

function LangBadge({ lang }) {
  return (
    <span className={`text-[10px] px-2 py-0.5 rounded-md font-semibold ${
      lang === 'Tamil' ? 'bg-orange-50 text-orange-700 ring-1 ring-orange-200/60' : 'bg-blue-50 text-blue-700 ring-1 ring-blue-200/60'
    }`}>
      {lang === 'Tamil' ? 'தமிழ்' : 'EN'}
    </span>
  )
}

export default function ChatMessage({ msg, onSpeak }) {
  const isUser = msg.role === 'user'
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(msg.content)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch { /* ignore */ }
  }

  return (
    <article className={`group animate-fade-in ${isUser ? 'bg-kv-creamDark/40' : 'bg-white'}`}>
      <div className="max-w-3xl mx-auto w-full px-4 md:px-6 py-5 md:py-6">
        <div className="flex gap-4">
          <div className={`flex-shrink-0 w-8 h-8 rounded-xl flex items-center justify-center ${
            isUser ? 'bg-kv-forest text-white' : 'bg-kv-sage text-white shadow-sm'
          }`}>
            {isUser ? <UserIcon className="w-4 h-4" /> : <SparkleIcon className="w-3.5 h-3.5" />}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1.5 flex-wrap">
              <span className="text-sm font-semibold text-gray-900">{isUser ? 'You' : 'KrishiVoice'}</span>
              <LangBadge lang={msg.language} />
            </div>
            <p className="prose-kv">{msg.content}</p>
            {!isUser && msg.advisory && (
              <StructuredAdvisory advisory={msg.advisory} intent={msg.intent} guest={msg.guest} language={msg.language} />
            )}
            {!isUser && (
              <div className="flex items-center gap-1 mt-3 opacity-0 group-hover:opacity-100 transition-opacity">
                <button type="button" onClick={handleCopy} className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs text-gray-500 hover:bg-kv-creamDark">
                  <CopyIcon /> {copied ? 'Copied' : 'Copy'}
                </button>
                <button type="button" onClick={() => onSpeak(msg.content, msg.language)} className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs text-gray-500 hover:bg-kv-sageLight hover:text-kv-forest">
                  <SpeakerIcon /> {msg.language === 'Tamil' ? 'கேளுங்க' : 'Listen'}
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </article>
  )
}

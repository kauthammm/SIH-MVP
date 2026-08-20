import { useCallback, useEffect, useRef, useState } from 'react'
import { fetchSpeechAudio } from '../api'
import { micSpeechLang } from '../utils/language'

const SpeechRecognition =
  typeof window !== 'undefined'
    ? window.SpeechRecognition || window.webkitSpeechRecognition
    : null

/** How long to wait after you stop speaking before sending (ms) */
export const SILENCE_END_MS = 1200

/** Maximum listen duration per voice turn (ms) */
const MAX_LISTEN_MS = 60000

export { detectLanguage } from '../utils/language'

export function useSpeech(sidebarLanguage = 'Auto', lastDetectedLang = 'Tamil') {
  const [isListening, setIsListening] = useState(false)
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [isSupported] = useState(!!SpeechRecognition)
  const recognitionRef = useRef(null)
  const audioRef = useRef(null)
  const finalSentRef = useRef(false)
  const transcriptRef = useRef('')
  const silenceTimerRef = useRef(null)
  const maxTimerRef = useRef(null)
  const callbacksRef = useRef({ onInterim: null, onFinal: null, onError: null })

  const clearTimers = useCallback(() => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current)
      silenceTimerRef.current = null
    }
    if (maxTimerRef.current) {
      clearTimeout(maxTimerRef.current)
      maxTimerRef.current = null
    }
  }, [])

  const stopSpeaking = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current = null
    }
    window.speechSynthesis?.cancel()
    setIsSpeaking(false)
  }, [])

  const speakBrowser = useCallback((text, language) => {
    return new Promise((resolve) => {
      if (!window.speechSynthesis) {
        resolve()
        return
      }
      window.speechSynthesis.cancel()
      const utter = new SpeechSynthesisUtterance(text)
      utter.lang = language === 'Tamil' ? 'ta-IN' : 'en-IN'
      // Slower, warmer — closer to field conversation than default browser TTS
      utter.rate = 0.88
      utter.pitch = 0.95
      const voices = window.speechSynthesis.getVoices()
      const prefer = language === 'Tamil'
        ? (v) => v.lang.startsWith('ta') && /pallavi|tamil|india/i.test(v.name)
        : (v) => v.lang.startsWith('en-IN') || (v.lang.startsWith('en') && /india|neerja|ravi/i.test(v.name))
      const voice = voices.find(prefer)
        || voices.find(v => language === 'Tamil' ? v.lang.startsWith('ta') : v.lang.startsWith('en'))
      if (voice) utter.voice = voice
      utter.onstart = () => setIsSpeaking(true)
      utter.onend = () => {
        setIsSpeaking(false)
        resolve()
      }
      utter.onerror = () => {
        setIsSpeaking(false)
        resolve()
      }
      window.speechSynthesis.speak(utter)
    })
  }, [])

  const speak = useCallback(async (text, language = 'Tamil') => {
    if (!text) return

    // Stop mic so assistant speech is not transcribed as the farmer's question
    try {
      recognitionRef.current?.abort()
    } catch (_) { /* ignore */ }
    clearTimers()
    finalSentRef.current = true
    setIsListening(false)

    stopSpeaking()
    setIsSpeaking(true)

    try {
      const blob = await fetchSpeechAudio(text, language)
      const url = URL.createObjectURL(blob)
      const audio = new Audio(url)
      audioRef.current = audio
      await new Promise((resolve, reject) => {
        audio.onended = () => {
          URL.revokeObjectURL(url)
          resolve()
        }
        audio.onerror = () => {
          URL.revokeObjectURL(url)
          reject(new Error('audio playback failed'))
        }
        audio.play().catch(reject)
      })
    } catch {
      await speakBrowser(text, language)
    } finally {
      setIsSpeaking(false)
    }
  }, [stopSpeaking, speakBrowser, clearTimers])

  const finalize = useCallback((reason = 'silence') => {
    if (finalSentRef.current) return
    finalSentRef.current = true
    clearTimers()

    const text = transcriptRef.current.trim()
    try {
      recognitionRef.current?.stop()
    } catch (_) { /* ignore */ }

    setIsListening(false)

    if (text) {
      callbacksRef.current.onFinal?.(text)
    } else if (reason === 'manual') {
      callbacksRef.current.onError?.('No speech captured. Try again.')
    } else {
      const tamil = micSpeechLang(sidebarLanguage, lastDetectedLang).startsWith('ta')
      callbacksRef.current.onError?.(
        tamil ? 'சத்தம் கேட்கல. மறுபடி try பண்ணுங்க.' : 'No speech heard. Try again.'
      )
    }
  }, [clearTimers, sidebarLanguage, lastDetectedLang])

  const resetSilenceTimer = useCallback(() => {
    if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current)
    silenceTimerRef.current = setTimeout(() => finalize('silence'), SILENCE_END_MS)
  }, [finalize])

  const startListening = useCallback((onInterim, onFinal, onError) => {
    if (!SpeechRecognition) {
      onError?.('Voice not supported. Use Chrome or Edge.')
      return
    }

    try {
      recognitionRef.current?.abort()
    } catch (_) { /* ignore */ }

    clearTimers()
    finalSentRef.current = false
    transcriptRef.current = ''
    callbacksRef.current = { onInterim, onFinal, onError }

    const sttLang = micSpeechLang(sidebarLanguage, lastDetectedLang)
    const recognition = new SpeechRecognition()

    // continuous = listen through pauses so full sentence is captured
    recognition.continuous = true
    recognition.interimResults = true
    recognition.lang = sttLang
    recognition.maxAlternatives = 1

    recognition.onstart = () => {
      setIsListening(true)
      maxTimerRef.current = setTimeout(() => finalize('max'), MAX_LISTEN_MS)
    }

    recognition.onend = () => {
      setIsListening(false)
      clearTimers()
      // Browser stopped early — send whatever we captured
      if (!finalSentRef.current && transcriptRef.current.trim()) {
        finalSentRef.current = true
        callbacksRef.current.onFinal?.(transcriptRef.current.trim())
      }
    }

    recognition.onerror = (e) => {
      if (e.error === 'aborted') return
      clearTimers()
      setIsListening(false)
      if (e.error === 'no-speech' && transcriptRef.current.trim()) {
        if (!finalSentRef.current) {
          finalSentRef.current = true
          callbacksRef.current.onFinal?.(transcriptRef.current.trim())
        }
        return
      }
      const tamil = sttLang.startsWith('ta')
      const msgs = {
        'no-speech': tamil ? 'சத்தம் கேட்கல. மறுபடி try பண்ணுங்க.' : 'No speech heard. Try again.',
        'not-allowed': 'Allow microphone access in browser settings.',
        'network': 'Network error. Check internet connection.',
      }
      callbacksRef.current.onError?.(msgs[e.error] || `Voice error: ${e.error}`)
    }

    recognition.onresult = (event) => {
      // Accumulate FULL transcript (all segments, including pauses mid-sentence)
      let full = ''
      for (let i = 0; i < event.results.length; i++) {
        full += event.results[i][0].transcript
      }
      full = full.trim()
      if (!full) return

      transcriptRef.current = full
      callbacksRef.current.onInterim?.(full)

      // Reset end-of-speech timer on every new word — only sends after SILENCE_END_MS quiet
      resetSilenceTimer()
    }

    recognitionRef.current = recognition
    try {
      recognition.start()
    } catch (e) {
      onError?.(String(e))
    }
  }, [sidebarLanguage, lastDetectedLang, clearTimers, finalize, resetSilenceTimer])

  /** Tap mic again to finish immediately and send */
  const stopListening = useCallback(() => {
    if (finalSentRef.current) {
      try { recognitionRef.current?.abort() } catch (_) { /* ignore */ }
      setIsListening(false)
      clearTimers()
      return
    }
    finalize('manual')
  }, [finalize, clearTimers])

  useEffect(() => () => {
    clearTimers()
    stopSpeaking()
    try { recognitionRef.current?.abort() } catch (_) { /* ignore */ }
  }, [clearTimers, stopSpeaking])

  return {
    isListening,
    isSpeaking,
    isSupported,
    silenceEndMs: SILENCE_END_MS,
    startListening,
    stopListening,
    speak,
    stopSpeaking,
  }
}

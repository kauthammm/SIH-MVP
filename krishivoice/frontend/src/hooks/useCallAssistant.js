import { useCallback, useEffect, useRef, useState } from 'react'
import { askCallAssistant, fetchCallBriefing, fetchWeatherAlerts } from '../api'

const ALERT_POLL_MS = 5 * 60 * 1000
/** Pause after TTS so mic does not pick up speaker bleed */
const POST_SPEAK_DELAY_MS = 800

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

export function useCallAssistant({
  isGuest,
  farmerId,
  parcelId,
  displayName,
  language,
  isSupported,
  startListening,
  stopListening,
  speak,
  stopSpeaking,
  onMessage,
  onError,
  useWebSearch = false,
}) {
  const [inCall, setInCall] = useState(false)
  const [callStatus, setCallStatus] = useState('idle') // idle | briefing | listening | thinking | speaking | alert
  const [alerts, setAlerts] = useState([])
  const inCallRef = useRef(false)
  const busyRef = useRef(false)
  const lastAlertIdRef = useRef(null)

  const langPref = language === 'English' ? 'English' : 'Tamil'
  const farmerName = displayName?.split('—')[0]?.trim() || (isGuest ? 'Farmer' : farmerId)

  const loadAlerts = useCallback(async () => {
    try {
      const data = await fetchWeatherAlerts({
        parcelId,
        farmerId,
        guest: isGuest,
      })
      setAlerts(data.alerts || [])
      return data
    } catch {
      return { alerts: [] }
    }
  }, [isGuest, farmerId, parcelId])

  const speakAlertIfNew = useCallback(async (alertList, forceLang) => {
    const high = alertList.find((a) => a.severity === 'high') || alertList[0]
    if (!high || high.id === lastAlertIdRef.current) return
    lastAlertIdRef.current = high.id
    const lang = forceLang || langPref
    const text = lang === 'Tamil' ? high.spoken_ta : high.spoken_en
    setCallStatus('alert')
    await speak(text, lang)
  }, [langPref, speak])

  const listenNext = useCallback(() => {
    if (!inCallRef.current || busyRef.current) return
    setCallStatus('listening')
    startListening(
      () => {},
      async (transcript) => {
        if (!inCallRef.current || busyRef.current) return
        busyRef.current = true
        setCallStatus('thinking')
        try {
          const result = await askCallAssistant({
            farmerId,
            parcelId,
            query: transcript,
            language: langPref,
            guest: isGuest,
            useWebSearch,
          })
          onMessage?.({
            role: 'user',
            content: transcript,
            language: result.language,
          })
          onMessage?.({
            role: 'assistant',
            content: result.text,
            language: result.language,
            intent: result.intent,
            advisory: result.advisory,
            callMode: true,
          })
          setCallStatus('speaking')
          stopListening()
          await speak(result.text, result.language)
          await wait(POST_SPEAK_DELAY_MS)
          busyRef.current = false
          if (inCallRef.current) listenNext()
          else setCallStatus('idle')
        } catch (e) {
          busyRef.current = false
          onError?.(e.message)
          if (inCallRef.current) listenNext()
        }
      },
      (err) => {
        onError?.(err)
        if (inCallRef.current && !busyRef.current) listenNext()
      },
    )
  }, [farmerId, parcelId, isGuest, langPref, startListening, stopListening, speak, onMessage, onError, useWebSearch])

  const startCall = useCallback(async () => {
    if (!isSupported) {
      onError?.('Voice not supported. Use Chrome or Edge.')
      return
    }
    inCallRef.current = true
    setInCall(true)
    busyRef.current = true
    setCallStatus('briefing')

    try {
      const alertData = await loadAlerts()
      setAlerts(alertData.alerts || [])

      const briefing = await fetchCallBriefing({
        farmerId,
        parcelId,
        language: langPref,
        guest: isGuest,
        farmerName,
      })

      onMessage?.({
        role: 'assistant',
        content: briefing.text,
        language: briefing.language,
        callMode: true,
        briefing: true,
      })

      setCallStatus('speaking')
      stopListening()
      await speak(briefing.text, briefing.language)
      await wait(POST_SPEAK_DELAY_MS)

      if (alertData.high_count > 0 && alertData.alerts?.[0]) {
        lastAlertIdRef.current = alertData.alerts[0].id
      }

      busyRef.current = false
      listenNext()
    } catch (e) {
      busyRef.current = false
      inCallRef.current = false
      setInCall(false)
      setCallStatus('idle')
      onError?.(e.message)
    }
  }, [isSupported, loadAlerts, farmerId, parcelId, langPref, isGuest, farmerName, speak, stopListening, listenNext, onMessage, onError])

  const endCall = useCallback(() => {
    inCallRef.current = false
    busyRef.current = false
    setInCall(false)
    setCallStatus('idle')
    stopListening()
    stopSpeaking()
  }, [stopListening, stopSpeaking])

  useEffect(() => {
    if (!inCall) return undefined
    const id = setInterval(async () => {
      if (busyRef.current || callStatus === 'speaking' || callStatus === 'briefing') return
      const data = await loadAlerts()
      const high = (data.alerts || []).filter((a) => a.severity === 'high')
      if (high.length && inCallRef.current) {
        busyRef.current = true
        stopListening()
        await speakAlertIfNew(high, langPref)
        await wait(POST_SPEAK_DELAY_MS)
        busyRef.current = false
        if (inCallRef.current) listenNext()
      }
    }, ALERT_POLL_MS)
    return () => clearInterval(id)
  }, [inCall, callStatus, loadAlerts, speakAlertIfNew, langPref, listenNext, stopListening])

  return {
    inCall,
    callStatus,
    alerts,
    startCall,
    endCall,
    loadAlerts,
    speakAlertIfNew,
  }
}

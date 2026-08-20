import { useCallback, useEffect, useRef, useState } from 'react'
import { buildLandList } from './utils/lands'
import { askKrishiVoice, createConversation, fetchConversation, fetchConversations, fetchFarmerProfile, fetchJSON, getStoredSession, uploadSoilReport } from './api'
import CallAssistantOverlay from './components/call/CallAssistantOverlay'
import ProfilePanel from './components/ProfilePanel'
import SettingsModal from './components/SettingsModal'
import ChatInput from './components/chat/ChatInput'
import GuestProfileBar from './components/chat/GuestProfileBar'
import ChatMessage from './components/chat/ChatMessage'
import HeroDashboard from './components/chat/HeroDashboard'
import TypingIndicator from './components/chat/TypingIndicator'
import Header from './components/layout/Header'
import Sidebar from './components/layout/Sidebar'
import DashboardSidebar from './components/dashboard/DashboardSidebar'
import DashboardHeader from './components/dashboard/DashboardHeader'
import { SparkleIcon } from './components/icons'
import { useAuth } from './context/AuthContext'
import { useCallAssistant } from './hooks/useCallAssistant'
import { useSpeech } from './hooks/useSpeech'
import { addRecentChat, loadRecentChats } from './utils/chatHistory'
import { detectLanguage } from './utils/language'
import { errorMessage } from './utils/formatError'
import AlertBanner from './components/notifications/AlertBanner'
import NotificationsPanel from './components/notifications/NotificationsPanel'
import FarmReportsPanel from './components/reports/FarmReportsPanel'
import MarketRatesPanel from './components/market/MarketRatesPanel'
import { useNotifications } from './hooks/useNotifications'
import { fetchDailyBriefing, getGuestSessionId, startGuestSession } from './utils/guestSession'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'

const NAV_QUERIES = {
  weather: { en: 'Will it rain tomorrow?', ta: 'நாளைக்கு மழை வருமா?' },
  market: { en: 'What are current paddy market rates?', ta: 'நெல் market rate என்ன?' },
  advice: { en: 'What should I do for my crop now?', ta: 'என் crop-ku ippove enna seiyanum?' },
  schemes: { en: 'What government schemes are available for farmers?', ta: 'விவசாயிகளுக்கு என்ன govt scheme irukku?' },
}

export default function App() {
  const { session } = useAuth()
  const [guestMode, setGuestMode] = useState(false)
  const [authScreen, setAuthScreen] = useState(null)

  const showAuth = !session && !guestMode

  if (showAuth) {
    if (authScreen === 'register') {
      return (
        <RegisterPage
          onLogin={() => setAuthScreen('login')}
          onSuccess={() => setAuthScreen(null)}
        />
      )
    }
    return (
      <LoginPage
        onRegister={() => setAuthScreen('register')}
        onGuest={() => setGuestMode(true)}
        onSuccess={() => setAuthScreen(null)}
      />
    )
  }

  return (
    <KrishiAssistant
      onSignIn={() => { setGuestMode(false); setAuthScreen('login') }}
      onLoggedOut={() => { setGuestMode(false); setAuthScreen('login') }}
    />
  )
}

function KrishiAssistant({ onSignIn, onLoggedOut }) {
  const { isGuest, farmerId, displayName, logout, isUserAuth, userId, username, parcelId: sessionParcelId } = useAuth()

  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [profileOpen, setProfileOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [activeNav, setActiveNav] = useState('chat')
  const [activeMode, setActiveMode] = useState('chat')
  const [parcelId, setParcelId] = useState(sessionParcelId || null)
  const [parcels, setParcels] = useState([])
  const [parcel, setParcel] = useState(null)
  const [hasCustomProfile, setHasCustomProfile] = useState(false)
  const [profileLearned, setProfileLearned] = useState(null)
  const [weather, setWeather] = useState({ temp: 32, location: 'Thanjavur, TN' })
  const [language, setLanguage] = useState('Auto')
  const [lastDetected, setLastDetected] = useState('Tamil')
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState([])
  const [recentChats, setRecentChats] = useState(loadRecentChats)
  const [conversations, setConversations] = useState([])
  const [conversationId, setConversationId] = useState(null)
  const [thinking, setThinking] = useState(false)
  const [error, setError] = useState(null)
  const [autoSpeak, setAutoSpeak] = useState(true)
  const [toast, setToast] = useState(null)
  const [guestProfile, setGuestProfile] = useState({})
  const [guestCompleteness, setGuestCompleteness] = useState(0)
  const [briefingLoading, setBriefingLoading] = useState(false)
  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const [reportsOpen, setReportsOpen] = useState(false)
  const [marketOpen, setMarketOpen] = useState(false)
  const [webSearchEnabled, setWebSearchEnabled] = useState(false)

  const {
    notifications,
    highCount,
    unreadCount,
    loading: notificationsLoading,
    readIds,
    newAlert,
    markRead,
    markAllRead,
    dismissBanner,
    load: reloadNotifications,
  } = useNotifications({
    isGuest,
    farmerId,
    parcelId,
    language: lastDetected,
    enabled: true,
  })

  const chatEndRef = useRef(null)
  const inputRef = useRef(null)
  const busyRef = useRef(false)
  const inChat = messages.length > 0 || thinking

  const { isListening, isSpeaking, isSupported, silenceEndMs, startListening, stopListening, speak, stopSpeaking } =
    useSpeech(language, lastDetected)

  const handleCallMessage = useCallback((msg) => {
    setMessages((prev) => [...prev, { id: Date.now() + Math.random(), ...msg }])
  }, [])

  const {
    inCall,
    callStatus,
    alerts: callAlerts,
    startCall,
    endCall,
    loadAlerts,
  } = useCallAssistant({
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
    onMessage: handleCallMessage,
    onError: setError,
    useWebSearch: webSearchEnabled,
  })

  useEffect(() => {
    if (!isGuest || getGuestSessionId()) return
    startGuestSession(language === 'English' ? 'English' : 'Tamil')
      .then((s) => {
        if (s.session_id) {
          setMessages([{
            id: Date.now(),
            role: 'assistant',
            content: s.text,
            language: s.language,
            guest: true,
            greeting: true,
          }])
        }
      })
      .catch(() => {})
  }, [isGuest, language])

  const applyProfileLands = useCallback((prof, currentParcelId) => {
    const lands = buildLandList(prof)
    setParcels(lands)
    const pid = currentParcelId || prof.active_parcel_id || lands[0]?.parcel_id
    if (pid) setParcelId(pid)
    setHasCustomProfile(Boolean(prof.parcels_custom?.[pid]))
    const active = lands.find((p) => p.parcel_id === pid)
    if (active) {
      setParcel(active)
      setWeather((w) => ({
        ...w,
        location: `${active.land_name || active.village || active.district}, TN`,
      }))
    }
    return pid
  }, [])

  useEffect(() => {
    if (!isGuest && sessionParcelId) {
      setParcelId(sessionParcelId)
    }
  }, [isGuest, sessionParcelId, farmerId])

  useEffect(() => {
    if (isGuest) {
      setParcels([])
      setParcel(null)
      setHasCustomProfile(false)
      setWeather({ temp: 32, location: 'Thanjavur, TN' })
      return
    }
    fetchFarmerProfile(farmerId)
      .then((prof) => { applyProfileLands(prof, parcelId || prof.active_parcel_id) })
      .catch(() => {})
  }, [isGuest, farmerId, applyProfileLands])

  useEffect(() => {
    if (isGuest || !parcelId) return
    const fromList = parcels.find((p) => p.parcel_id === parcelId)
    if (fromList) {
      setParcel(fromList)
      setWeather((w) => ({
        ...w,
        location: `${fromList.land_name || fromList.village || fromList.district}, TN`,
      }))
    } else {
      fetchJSON(`/parcels/${parcelId}?farmer_id=${encodeURIComponent(farmerId)}`).then((p) => {
        setParcel(p)
        setWeather((w) => ({ ...w, location: `${p.land_name || p.village || p.district}, TN` }))
      }).catch(() => {})
    }
    fetchJSON(`/parcels/${parcelId}/weather?days=1&farmer_id=${encodeURIComponent(farmerId)}`)
      .then((data) => {
        const today = data?.[0]
        if (today?.temperature != null) {
          setWeather((w) => ({ ...w, temp: Math.round(today.temperature) }))
        }
      })
      .catch(() => {})
  }, [isGuest, farmerId, parcelId, parcels])

  const loadConversationList = useCallback(async () => {
    const sess = getStoredSession()
    if (sess?.authMode !== 'user') return
    try {
      const list = await fetchConversations()
      setConversations(list)
    } catch {
      setConversations([])
    }
  }, [])

  const openConversation = useCallback(async (id) => {
    if (!isUserAuth || !id) return
    try {
      const conv = await fetchConversation(id)
      setConversationId(conv.id)
      setMessages((conv.messages || []).map((m, i) => ({
        id: m.id || `${conv.id}-${i}`,
        role: m.role,
        content: m.content,
        language: m.meta?.language,
        intent: m.meta?.intent,
      })))
      setActiveNav('chat')
      setError(null)
    } catch (e) {
      setError(e.message)
    }
  }, [isUserAuth])

  useEffect(() => {
    if (isUserAuth) {
      loadConversationList()
      setMessages([])
      setConversationId(null)
    } else {
      setConversations([])
      setConversationId(null)
    }
  }, [isUserAuth, loadConversationList])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, thinking])

  const getResponseText = useCallback((result, lang) => {
    const adv = result.advisory
    if (lang === 'Tamil' && adv.tamil_response) return adv.tamil_response
    return adv.english_response || adv.recommendation
  }, [])

  const sendMessage = useCallback(async (text) => {
    const query = text.trim()
    if (!query || busyRef.current) return

    busyRef.current = true
    const lang = detectLanguage(query, language)
    setLastDetected(lang)
    setError(null)
    setInput('')
    setActiveNav('chat')
    setMessages((prev) => [...prev, { id: Date.now(), role: 'user', content: query, language: lang }])
    setThinking(true)

    if (messages.length === 0 && !isUserAuth) {
      setRecentChats(addRecentChat(query))
    }

    try {
      const result = await askKrishiVoice({
        farmerId: isGuest ? null : farmerId,
        parcelId: isGuest ? null : parcelId,
        query,
        language: lang === 'Tamil' ? 'Tamil' : lang === 'English' ? 'English' : 'Auto',
        guest: isGuest,
        conversationId: isUserAuth ? conversationId : undefined,
        userId: isUserAuth ? userId : undefined,
        useWebSearch: webSearchEnabled,
      })
      if (result.conversation_id && isUserAuth) {
        setConversationId(result.conversation_id)
        loadConversationList()
      }
      const resolvedLang = result.detected_language || lang
      const isGuestReply = result.entities?.mode === 'guest' || isGuest
      setLastDetected(resolvedLang)
      const responseText = getResponseText(result, resolvedLang)

      setMessages((prev) => [...prev, {
        id: Date.now() + 1,
        role: 'assistant',
        content: responseText,
        language: resolvedLang,
        intent: result.intent,
        advisory: result.advisory,
        guest: isGuestReply,
      }])
      if (result.profile_updated && result.profile_fields) {
        setHasCustomProfile(true)
        const fields = Object.entries(result.profile_fields)
          .filter(([k]) => !['soil'].includes(k))
          .map(([k, v]) => (typeof v === 'object' ? 'soil' : k))
          .join(', ')
        setProfileLearned(fields || 'farm details')
        setToast(`Saved from your voice: ${fields || 'farm info'}`)
        fetchFarmerProfile(farmerId)
          .then((prof) => { applyProfileLands(prof, parcelId) })
          .catch(() => {})
        setTimeout(() => setToast(null), 5000)
      }
      if (isGuest && result.entities?.profile) {
        setGuestProfile(result.entities.profile)
        const comp = result.entities.profile?.crop ? 0.5 : 0
        setGuestCompleteness(result.profile_fields ? Math.min(1, Object.keys(result.profile_fields).length * 0.15) : comp)
        if (result.entities.profile.crop) {
          setGuestCompleteness((c) => Math.max(c, 0.4 + Object.keys(result.entities.profile).length * 0.1))
        }
      }
      setThinking(false)
      busyRef.current = false
      if (autoSpeak) speak(responseText, resolvedLang)
    } catch (e) {
      setThinking(false)
      busyRef.current = false
      setError(errorMessage(e, 'Request failed'))
      setMessages((prev) => [...prev, {
        id: Date.now() + 1,
        role: 'assistant',
        content: lang === 'Tamil'
          ? 'மன்னிக்கவும், process பண்ண முடியல. Internet check பண்ணுங்க.'
          : `Sorry, could not process. ${e.message}`,
        language: lang,
      }])
    }
  }, [isGuest, farmerId, parcelId, language, getResponseText, autoSpeak, speak, messages.length, applyProfileLands, isUserAuth, conversationId, userId, loadConversationList, webSearchEnabled])

  const handleSoilUpload = useCallback(async (file) => {
    if (busyRef.current) return
    busyRef.current = true
    const lang = language === 'English' ? 'English' : (lastDetected === 'English' ? 'English' : 'Tamil')
    setError(null)
    setActiveNav('chat')
    setMessages((prev) => [...prev, {
      id: Date.now(),
      role: 'user',
      content: lang === 'Tamil' ? `📄 Soil test report: ${file.name}` : `📄 Soil test report: ${file.name}`,
      language: lang,
      attachment: file.name,
    }])
    setThinking(true)

    try {
      const data = await uploadSoilReport(isGuest ? null : farmerId, isGuest ? null : parcelId, file)
      const responseText = lang === 'Tamil'
        ? (data.chat_message_ta || data.chat_message_en)
        : (data.chat_message_en || data.chat_message_ta)

      setMessages((prev) => [...prev, {
        id: Date.now() + 1,
        role: 'assistant',
        content: responseText,
        language: lang,
        soilReport: data,
      }])

      if (!isGuest && farmerId && data.ocr) {
        setHasCustomProfile(true)
        setProfileLearned('soil')
        setToast(lang === 'Tamil' ? 'Soil report profile-ல save aachu' : 'Soil report saved to your profile')
        fetchFarmerProfile(farmerId)
          .then((prof) => { applyProfileLands(prof, parcelId) })
          .catch(() => {})
        setTimeout(() => setToast(null), 5000)
      }

      if (autoSpeak && responseText) speak(responseText, lang)
    } catch (e) {
      setError(errorMessage(e, lang === 'Tamil' ? 'PDF read பண்ண முடியல' : 'Could not read PDF'))
      setMessages((prev) => [...prev, {
        id: Date.now() + 1,
        role: 'assistant',
        content: lang === 'Tamil'
          ? 'PDF-ல soil values clear-aa theriyala. Clear scan upload pannunga, illa manual-aa profile-ல enter pannunga.'
          : 'Could not read soil values from the PDF. Try a clearer scan or enter values in your profile.',
        language: lang,
      }])
    } finally {
      setThinking(false)
      busyRef.current = false
    }
  }, [isGuest, farmerId, parcelId, language, lastDetected, autoSpeak, speak, applyProfileLands])

  const handleMic = () => {
    if (isListening) { stopListening(); return }
    setError(null)
    startListening(
      (t) => setInput(t),
      (t) => { setInput(t); sendMessage(t) },
      (err) => setError(err),
    )
  }

  const newChat = async () => {
    setMessages([])
    setError(null)
    setInput('')
    setActiveNav('chat')
    stopSpeaking()
    if (isUserAuth) {
      try {
        const conv = await createConversation('New chat')
        setConversationId(conv.id)
        await loadConversationList()
      } catch (e) {
        setConversationId(null)
        setError(e.message)
      }
    } else {
      setConversationId(null)
    }
    inputRef.current?.focus()
  }


  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(input)
    }
  }

  const handleNav = (id) => {
    setActiveNav(id)
    const isEn = language === 'English'
    switch (id) {
      case 'chat':
        newChat()
        break
      case 'crops':
      case 'records':
        isGuest ? onSignIn?.() : setProfileOpen(true)
        break
      case 'weather':
        sendMessage(isEn ? NAV_QUERIES.weather.en : NAV_QUERIES.weather.ta)
        break
      case 'market':
        setMarketOpen(true)
        break
      case 'advice':
        sendMessage(isEn ? NAV_QUERIES.advice.en : NAV_QUERIES.advice.ta)
        break
      case 'schemes':
        sendMessage(isEn ? NAV_QUERIES.schemes.en : NAV_QUERIES.schemes.ta)
        break
      case 'settings':
        setSettingsOpen(true)
        break
      default:
        break
    }
  }

  const handleModeChange = (mode) => {
    setActiveMode(mode)
    if (mode === 'voice') {
      if (inCall) endCall()
      else startCall()
    }
    if (mode === 'field') isGuest ? onSignIn?.() : setProfileOpen(true)
  }

  const handleNotifications = () => {
    setNotificationsOpen(true)
    dismissBanner()
  }

  const handleSpeakNotification = useCallback(async (text, lang) => {
    if (autoSpeak) await speak(text, lang)
  }, [autoSpeak, speak])

  const handleGuestDailyBriefing = async () => {
    setBriefingLoading(true)
    try {
      const data = await fetchDailyBriefing({
        guest: true,
        sessionId: getGuestSessionId(),
        language: lastDetected === 'English' ? 'English' : 'Tamil',
      })
      setMessages((prev) => [...prev, {
        id: Date.now(),
        role: 'assistant',
        content: data.text,
        language: data.language,
        guest: true,
        briefing: true,
      }])
      if (autoSpeak) speak(data.text, data.language)
    } catch (e) {
      setError(e.message)
    } finally {
      setBriefingLoading(false)
    }
  }

  const showToast = (msg) => {
    setToast(msg)
    setTimeout(() => setToast(null), 3500)
  }

  const handleLogout = () => {
    logout()
    setMessages([])
    setConversationId(null)
    setConversations([])
    onLoggedOut?.()
  }

  const cropLabel = parcel?.crop || guestProfile?.crop

  return (
    <div className="flex h-screen bg-kv-cream text-gray-900 overflow-hidden">
      {isUserAuth ? (
        <DashboardSidebar
          open={sidebarOpen}
          displayName={displayName}
          username={username}
          farmerId={farmerId}
          parcel={parcel}
          conversations={conversations}
          activeConversationId={conversationId}
          activeNav={activeNav}
          onNav={handleNav}
          onNewChat={newChat}
          onSelectConversation={openConversation}
          onProfile={() => setProfileOpen(true)}
          onLogout={handleLogout}
        />
      ) : (
        <Sidebar
          open={sidebarOpen}
          isGuest={isGuest}
          isUserAuth={false}
          displayName={displayName}
          farmerId={farmerId}
          parcel={parcel}
          language={language}
          activeNav={activeNav}
          recentChats={recentChats}
          conversations={[]}
          activeConversationId={null}
          onNav={handleNav}
          onNewChat={newChat}
          onLogin={onSignIn}
          onProfile={() => (isGuest ? onSignIn?.() : setProfileOpen(true))}
          onRecentChat={sendMessage}
          onSelectConversation={() => {}}
        />
      )}

      <main className="flex-1 flex flex-col min-w-0 h-full bg-kv-cream">
        {isUserAuth ? (
          <DashboardHeader
            onToggleSidebar={() => setSidebarOpen((o) => !o)}
            displayName={displayName}
            username={username}
            parcel={parcel}
            crop={cropLabel}
            weather={weather}
            isListening={isListening}
            isSpeaking={isSpeaking}
            alertCount={unreadCount > 0 ? unreadCount : highCount}
            onNotifications={handleNotifications}
            onReports={() => setReportsOpen(true)}
            inCall={inCall}
          />
        ) : (
          <Header
            onToggleSidebar={() => setSidebarOpen((o) => !o)}
            activeMode={activeMode}
            onModeChange={handleModeChange}
            language={language}
            weather={weather}
            isListening={isListening}
            isSpeaking={isSpeaking}
            lastDetected={lastDetected}
            onProfile={() => (isGuest ? onSignIn?.() : setProfileOpen(true))}
            onNotifications={handleNotifications}
            onReports={() => setReportsOpen(true)}
            alertCount={unreadCount > 0 ? unreadCount : highCount}
            inCall={inCall}
          />
        )}

        {newAlert && !notificationsOpen && (
          <AlertBanner
            alert={newAlert}
            language={language === 'English' ? 'English' : lastDetected}
            onDismiss={dismissBanner}
            onOpenPanel={() => setNotificationsOpen(true)}
            onSpeak={handleSpeakNotification}
          />
        )}

        <div className="flex-1 overflow-y-auto min-h-0 flex flex-col">
          {isGuest && (
            <GuestProfileBar
              profile={guestProfile}
              completeness={guestCompleteness}
              onDailyBriefing={handleGuestDailyBriefing}
              loadingBriefing={briefingLoading}
            />
          )}
          {!inChat ? (
            <HeroDashboard
              isGuest={isGuest}
              isUserAuth={isUserAuth}
              displayName={displayName}
              username={username}
              farmerId={farmerId}
              parcel={parcel}
              weather={weather}
              language={language}
              input={input}
              setInput={setInput}
              onSend={() => sendMessage(input)}
              onMic={handleMic}
              thinking={thinking}
              isListening={isListening}
              isSupported={isSupported}
              inputRef={inputRef}
              onKeyDown={handleKeyDown}
              onQuickAction={sendMessage}
              onUploadSoil={handleSoilUpload}
              onLogin={onSignIn}
              onStartCall={startCall}
              inCall={inCall}
              webSearchEnabled={webSearchEnabled}
              onToggleWebSearch={() => setWebSearchEnabled((v) => !v)}
            />
          ) : (
            <>
              {messages.map((msg) => (
                <ChatMessage key={msg.id} msg={msg} onSpeak={speak} />
              ))}
              {thinking && (
                <div className="bg-white border-b border-kv-beige/60">
                  <div className="max-w-3xl mx-auto px-4 md:px-6 py-5 flex gap-4">
                    <div className="w-8 h-8 rounded-xl bg-kv-sage flex items-center justify-center text-white">
                      <SparkleIcon className="w-3.5 h-3.5" />
                    </div>
                    <TypingIndicator />
                  </div>
                </div>
              )}
              <div ref={chatEndRef} className="h-2" />
            </>
          )}
        </div>

        {error && (
          <div className="mx-4 mb-1 px-4 py-2.5 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700 shrink-0">
            {error}
          </div>
        )}

        {inChat && (
          <ChatInput
            input={input}
            setInput={setInput}
            onSend={() => sendMessage(input)}
            onMic={handleMic}
            onUploadSoil={handleSoilUpload}
            thinking={thinking}
            isListening={isListening}
            isSupported={isSupported}
            isGuest={isGuest}
            language={language}
            inputRef={inputRef}
            onKeyDown={handleKeyDown}
            webSearchEnabled={webSearchEnabled}
            onToggleWebSearch={() => setWebSearchEnabled((v) => !v)}
          />
        )}
      </main>

      {toast && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 px-4 py-3 rounded-xl bg-kv-forest text-white text-sm shadow-elevated max-w-md text-center animate-fade-in">
          {toast}
        </div>
      )}

      <SettingsModal
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        language={language}
        onLanguageChange={setLanguage}
        autoSpeak={autoSpeak}
        onAutoSpeakChange={setAutoSpeak}
      />
      {!isGuest && (
        <ProfilePanel
          open={profileOpen}
          onClose={() => setProfileOpen(false)}
          farmerId={farmerId}
          parcelId={parcelId}
          onParcelChange={setParcelId}
          onSaved={() => {
            setHasCustomProfile(true)
            fetchFarmerProfile(farmerId)
              .then((prof) => { applyProfileLands(prof, parcelId) })
              .catch(() => {})
          }}
        />
      )}

      <CallAssistantOverlay
        open={inCall}
        callStatus={callStatus}
        alerts={callAlerts}
        language={language}
        onEndCall={() => { endCall(); setActiveMode('chat') }}
        highCount={highCount}
      />

      <NotificationsPanel
        open={notificationsOpen}
        onClose={() => setNotificationsOpen(false)}
        notifications={notifications}
        readIds={readIds}
        unreadCount={unreadCount}
        loading={notificationsLoading}
        language={language === 'English' ? 'English' : lastDetected}
        onMarkRead={markRead}
        onMarkAllRead={markAllRead}
        onSpeak={handleSpeakNotification}
      />

      <FarmReportsPanel
        open={reportsOpen}
        farmerId={isGuest ? null : farmerId}
        parcelId={isGuest ? null : parcelId}
        sessionId={isGuest ? getGuestSessionId() : null}
        language={language === 'English' ? 'English' : lastDetected}
        onSpeak={speak}
        onClose={() => setReportsOpen(false)}
      />

      <MarketRatesPanel
        open={marketOpen}
        language={language === 'English' ? 'English' : lastDetected}
        onClose={() => setMarketOpen(false)}
        onAskInChat={(q) => {
          setActiveNav('chat')
          sendMessage(q)
        }}
      />
    </div>
  )
}

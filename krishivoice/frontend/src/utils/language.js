/** Tamil / English detection — mirrors backend logic */
const TAMIL_RE = /[\u0B80-\u0BFF]/
const TAMIL_HINTS = ['தண்ணீர்', 'பாய்ச்ச', 'மழை', 'வயல்', 'நெல்', 'இன்னைக்கு', 'நாளைக்கு', 'thanneer', 'paayich', 'mazhai', 'vayal', 'innikki']
const ENGLISH_HINTS = ['irrigate', 'water', 'rain', 'weather', 'crop', 'yield', 'disease', 'pest', 'field', 'should', 'today', 'tomorrow']

export function detectLanguage(text, preferred = 'Auto') {
  if (preferred === 'Tamil' || preferred === 'English') return preferred
  if (!text?.trim()) return 'Tamil'

  const tamilChars = (text.match(TAMIL_RE) || []).length
  const lower = text.toLowerCase()
  let tamilScore = tamilChars * 3
  let englishScore = (text.match(/[A-Za-z]/g) || []).length

  TAMIL_HINTS.forEach(h => {
    if (text.includes(h) || lower.includes(h)) tamilScore += 2
  })
  ENGLISH_HINTS.forEach(h => {
    if (lower.includes(h)) englishScore += 2
  })

  if (tamilScore > englishScore) return 'Tamil'
  if (englishScore > tamilScore) return 'English'
  return tamilChars > 0 ? 'Tamil' : 'English'
}

/** Web Speech API lang — Tamil or English (India) only */
export function speechLang(language) {
  return language === 'English' ? 'en-IN' : 'ta-IN'
}

/** Mic language when sidebar is Auto: pick STT language from last detect or default Tamil */
export function micSpeechLang(sidebarLang, lastDetected) {
  if (sidebarLang === 'Tamil') return 'ta-IN'
  if (sidebarLang === 'English') return 'en-IN'
  return lastDetected === 'English' ? 'en-IN' : 'ta-IN'
}

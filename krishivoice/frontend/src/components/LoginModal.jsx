import { useState } from 'react'
import { CloseIcon, SproutIcon } from './icons'
import { useAuth } from '../context/AuthContext'

export default function LoginModal({ open, onClose, onSuccess }) {
  const { login, loginWithUser, register, loggingIn, authError, clearAuthError } = useAuth()
  const [mode, setMode] = useState('farmer') // login | register | farmer
  const [username, setUsername] = useState('demo')
  const [password, setPassword] = useState('demo1234')
  const [displayName, setDisplayName] = useState('')
  const [farmerId, setFarmerId] = useState('F0042')
  const [pin, setPin] = useState('1234')

  if (!open) return null

  const handleSubmit = async (e) => {
    e.preventDefault()
    clearAuthError()
    try {
      if (mode === 'farmer') {
        await login(farmerId, pin)
      } else if (mode === 'register') {
        await register({
          username,
          password,
          displayName: displayName || undefined,
          farmerId: farmerId || undefined,
        })
      } else {
        await loginWithUser(username, password)
      }
      onSuccess?.()
      onClose()
    } catch { /* shown via authError */ }
  }

  const isEn = true

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-elevated border border-kv-beige overflow-hidden">
        <div className="px-6 py-5 border-b border-kv-beige">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-xl bg-kv-forest flex items-center justify-center text-kv-sageLight">
                <SproutIcon className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-kv-forest">
                  {mode === 'register' ? 'Create account' : 'Sign in'}
                </h2>
                <p className="text-sm text-gray-500 mt-0.5">
                  ChatGPT-style login — your chats are saved per account
                </p>
              </div>
            </div>
            <button type="button" onClick={onClose} className="p-2 rounded-xl hover:bg-kv-creamDark text-gray-400">
              <CloseIcon />
            </button>
          </div>
        </div>

        <div className="px-6 pt-4 flex gap-2">
          {['farmer', 'login', 'register'].map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => { setMode(m); clearAuthError() }}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                mode === m ? 'bg-kv-forest text-white' : 'bg-kv-creamDark text-gray-600 hover:bg-kv-beige'
              }`}
            >
              {m === 'login' ? 'Username' : m === 'register' ? 'Sign up' : 'Farmer ID'}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {(mode === 'login' || mode === 'register') && (
            <>
              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1.5">Username</label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-kv-beige text-sm focus:border-kv-sage focus:ring-2 focus:ring-kv-sageLight outline-none"
                  required
                  autoComplete="username"
                />
                {mode === 'login' && (
                  <p className="text-[11px] text-gray-400 mt-1">Demo: demo / demo1234</p>
                )}
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1.5">Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-kv-beige text-sm focus:border-kv-sage focus:ring-2 focus:ring-kv-sageLight outline-none"
                  required
                  autoComplete={mode === 'register' ? 'new-password' : 'current-password'}
                />
              </div>
            </>
          )}

          {mode === 'register' && (
            <>
              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1.5">Display name (optional)</label>
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-kv-beige text-sm focus:border-kv-sage focus:ring-2 focus:ring-kv-sageLight outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1.5">Link farmer ID (optional)</label>
                <input
                  type="text"
                  value={farmerId}
                  onChange={(e) => setFarmerId(e.target.value.toUpperCase())}
                  placeholder="F0042"
                  className="w-full px-3.5 py-2.5 rounded-xl border border-kv-beige text-sm focus:border-kv-sage focus:ring-2 focus:ring-kv-sageLight outline-none"
                />
                <p className="text-[11px] text-gray-400 mt-1">Defaults to F0042 (Thanjavur demo farm)</p>
              </div>
            </>
          )}

          {mode === 'farmer' && (
            <>
              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1.5">Farmer ID</label>
                <input
                  type="text"
                  value={farmerId}
                  onChange={(e) => setFarmerId(e.target.value.toUpperCase())}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-kv-beige text-sm focus:border-kv-sage focus:ring-2 focus:ring-kv-sageLight outline-none"
                  required
                />
                <p className="text-[11px] text-gray-400 mt-1">Demo: F0042 · PIN 1234 (no saved chats)</p>
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1.5">PIN</label>
                <input
                  type="password"
                  value={pin}
                  onChange={(e) => setPin(e.target.value)}
                  maxLength={6}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-kv-beige text-sm focus:border-kv-sage focus:ring-2 focus:ring-kv-sageLight outline-none"
                  required
                />
              </div>
            </>
          )}

          {authError && (
            <p className="text-sm text-red-700 bg-red-50 border border-red-100 rounded-xl px-3 py-2">{authError}</p>
          )}
          <button
            type="submit"
            disabled={loggingIn}
            className="w-full py-2.5 rounded-xl bg-kv-forest text-white font-semibold text-sm hover:bg-kv-forestDark disabled:opacity-50 transition"
          >
            {loggingIn ? 'Please wait…' : mode === 'register' ? 'Create account' : 'Continue'}
          </button>
        </form>
      </div>
    </div>
  )
}

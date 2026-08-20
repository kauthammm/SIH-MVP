import { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import AuthLayout from './AuthLayout'

export default function LoginPage({ onRegister, onGuest, onSuccess }) {
  const { loginWithUser, loggingIn, authError, clearAuthError } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    clearAuthError()
    try {
      await loginWithUser(username, password)
      onSuccess?.()
    } catch { /* authError */ }
  }

  return (
    <AuthLayout
      title="Welcome back"
      subtitle="Sign in to access your saved chats, farm profile and personalised voice assistant."
      footer={
        <div className="text-center space-y-3 text-sm text-gray-500">
          <p>
            New here?{' '}
            <button type="button" onClick={onRegister} className="font-semibold text-kv-forest hover:underline">
              Create an account
            </button>
          </p>
          <button type="button" onClick={onGuest} className="text-gray-400 hover:text-kv-forest transition">
            Continue without signing in →
          </button>
        </div>
      }
    >
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-kv-forest">Sign in</h2>
        <p className="text-sm text-gray-500 mt-1">Enter your account credentials</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-1.5">
            Username
          </label>
          <input
            id="username"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="your.username"
            autoComplete="username"
            required
            className="w-full px-4 py-3 rounded-xl border border-kv-beige bg-white text-sm focus:border-kv-sage focus:ring-2 focus:ring-kv-sageLight/50 outline-none transition"
          />
        </div>

        <div>
          <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1.5">
            Password
          </label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            autoComplete="current-password"
            required
            className="w-full px-4 py-3 rounded-xl border border-kv-beige bg-white text-sm focus:border-kv-sage focus:ring-2 focus:ring-kv-sageLight/50 outline-none transition"
          />
        </div>

        {authError && (
          <div className="flex gap-2.5 px-4 py-3 rounded-xl bg-red-50 border border-red-100 text-sm text-red-800">
            <span className="shrink-0 text-red-500">!</span>
            <span>{authError}</span>
          </div>
        )}

        <button
          type="submit"
          disabled={loggingIn}
          className="w-full py-3 rounded-xl bg-kv-forest text-white font-semibold text-sm hover:bg-kv-forestDark disabled:opacity-60 transition shadow-card"
        >
          {loggingIn ? 'Signing in…' : 'Sign in'}
        </button>
      </form>

      <p className="mt-6 text-xs text-gray-400 text-center">
        Demo account: <span className="font-mono text-gray-500">demo</span> / <span className="font-mono text-gray-500">demo1234</span>
      </p>
    </AuthLayout>
  )
}

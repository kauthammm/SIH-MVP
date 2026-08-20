import { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import AuthLayout from './AuthLayout'

const CROPS = ['Rice', 'Paddy', 'Sugarcane', 'Cotton', 'Groundnut', 'Maize', 'Turmeric', 'Banana']

export default function RegisterPage({ onLogin, onSuccess }) {
  const { register, loggingIn, authError, clearAuthError } = useAuth()
  const [displayName, setDisplayName] = useState('')
  const [username, setUsername] = useState('')
  const [district, setDistrict] = useState('')
  const [village, setVillage] = useState('')
  const [primaryCrop, setPrimaryCrop] = useState('Rice')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    clearAuthError()
    if (password !== confirm) {
      return
    }
    try {
      await register({
        username,
        password,
        displayName: displayName || undefined,
        district: district || undefined,
        village: village || undefined,
        primaryCrop: primaryCrop || undefined,
      })
      onSuccess?.()
    } catch { /* authError */ }
  }

  const mismatch = confirm && password !== confirm

  return (
    <AuthLayout
      title="Start your farm record"
      subtitle="Each account gets its own farmer profile — location, crop and chat history stay separate."
      footer={
        <p className="text-center text-sm text-gray-500">
          Already have an account?{' '}
          <button type="button" onClick={onLogin} className="font-semibold text-kv-forest hover:underline">
            Sign in
          </button>
        </p>
      }
    >
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-kv-forest">Create account</h2>
        <p className="text-sm text-gray-500 mt-1">A unique farm record will be assigned to your login</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="displayName" className="block text-sm font-medium text-gray-700 mb-1.5">
            Full name
          </label>
          <input
            id="displayName"
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="Ramesh Kumar"
            className="w-full px-4 py-3 rounded-xl border border-kv-beige bg-white text-sm focus:border-kv-sage focus:ring-2 focus:ring-kv-sageLight/50 outline-none"
          />
        </div>

        <div>
          <label htmlFor="reg-username" className="block text-sm font-medium text-gray-700 mb-1.5">
            Username
          </label>
          <input
            id="reg-username"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="ramesh.farm"
            autoComplete="username"
            required
            minLength={3}
            className="w-full px-4 py-3 rounded-xl border border-kv-beige bg-white text-sm focus:border-kv-sage focus:ring-2 focus:ring-kv-sageLight/50 outline-none"
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label htmlFor="district" className="block text-sm font-medium text-gray-700 mb-1.5">
              District
            </label>
            <input
              id="district"
              type="text"
              value={district}
              onChange={(e) => setDistrict(e.target.value)}
              placeholder="Thanjavur"
              className="w-full px-4 py-3 rounded-xl border border-kv-beige bg-white text-sm focus:border-kv-sage focus:ring-2 focus:ring-kv-sageLight/50 outline-none"
            />
          </div>
          <div>
            <label htmlFor="village" className="block text-sm font-medium text-gray-700 mb-1.5">
              Village
            </label>
            <input
              id="village"
              type="text"
              value={village}
              onChange={(e) => setVillage(e.target.value)}
              placeholder="Melattur"
              className="w-full px-4 py-3 rounded-xl border border-kv-beige bg-white text-sm focus:border-kv-sage focus:ring-2 focus:ring-kv-sageLight/50 outline-none"
            />
          </div>
        </div>

        <div>
          <label htmlFor="crop" className="block text-sm font-medium text-gray-700 mb-1.5">
            Primary crop
          </label>
          <select
            id="crop"
            value={primaryCrop}
            onChange={(e) => setPrimaryCrop(e.target.value)}
            className="w-full px-4 py-3 rounded-xl border border-kv-beige bg-white text-sm focus:border-kv-sage focus:ring-2 focus:ring-kv-sageLight/50 outline-none"
          >
            {CROPS.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="reg-password" className="block text-sm font-medium text-gray-700 mb-1.5">
            Password
          </label>
          <input
            id="reg-password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="new-password"
            required
            minLength={4}
            className="w-full px-4 py-3 rounded-xl border border-kv-beige bg-white text-sm focus:border-kv-sage focus:ring-2 focus:ring-kv-sageLight/50 outline-none"
          />
        </div>

        <div>
          <label htmlFor="confirm" className="block text-sm font-medium text-gray-700 mb-1.5">
            Confirm password
          </label>
          <input
            id="confirm"
            type="password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            autoComplete="new-password"
            required
            className={`w-full px-4 py-3 rounded-xl border bg-white text-sm focus:ring-2 focus:ring-kv-sageLight/50 outline-none ${
              mismatch ? 'border-red-300 focus:border-red-400' : 'border-kv-beige focus:border-kv-sage'
            }`}
          />
          {mismatch && <p className="text-xs text-red-600 mt-1">Passwords do not match</p>}
        </div>

        {authError && (
          <div className="flex gap-2.5 px-4 py-3 rounded-xl bg-red-50 border border-red-100 text-sm text-red-800">
            <span className="shrink-0 text-red-500">!</span>
            <span>{authError}</span>
          </div>
        )}

        <button
          type="submit"
          disabled={loggingIn || mismatch}
          className="w-full py-3 rounded-xl bg-kv-forest text-white font-semibold text-sm hover:bg-kv-forestDark disabled:opacity-60 transition shadow-card"
        >
          {loggingIn ? 'Creating account…' : 'Create account'}
        </button>
      </form>
    </AuthLayout>
  )
}

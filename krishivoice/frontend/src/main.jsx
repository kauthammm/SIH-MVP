import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { AuthProvider } from './context/AuthContext'
import './index.css'

class ErrorBoundary extends React.Component {
  state = { error: null }

  static getDerivedStateFromError(error) {
    return { error }
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: 24, fontFamily: 'Inter, sans-serif', maxWidth: 560, margin: '40px auto' }}>
          <h1 style={{ color: '#1a472a', marginBottom: 8 }}>KrishiVoice failed to load</h1>
          <p style={{ color: '#666', marginBottom: 16 }}>{String(this.state.error.message || this.state.error)}</p>
          <button
            type="button"
            onClick={() => window.location.reload()}
            style={{ padding: '10px 16px', background: '#1a472a', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}
          >
            Reload page
          </button>
        </div>
      )
    }
    return this.props.children
  }
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ErrorBoundary>
      <AuthProvider>
        <App />
      </AuthProvider>
    </ErrorBoundary>
  </React.StrictMode>,
)

import { useState } from 'react'
import { LogIn } from 'lucide-react'
import { api } from '../api.jsx'
import './Login.css'

function Login({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const data = await api('/api/auth/login', { method: 'POST', body: { username, password } })
      onLogin(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <form className="login-card" onSubmit={handleSubmit}>
        <h1>Property Investment Consultant</h1>
        <p>Sign in to continue</p>

        <label htmlFor="login-field-1">Username</label>
        <input id="login-field-1" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" />

        <label htmlFor="login-field-2">Password</label>
        <input id="login-field-2" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />

        {error && <div className="login-error" role="alert">{error}</div>}

        <button type="submit" disabled={loading || !username || !password}>
          <LogIn size={18} /> {loading ? 'Signing in...' : 'Sign in'}
        </button>
      </form>
    </div>
  )
}

export default Login

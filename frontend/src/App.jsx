import React, { useState, useEffect, useCallback } from 'react'
import { BarChart3, MessageSquare, Settings, LogOut, Coins } from 'lucide-react'
import ChatConsultant from './components/ChatConsultant'
import ComparisonTool from './components/ComparisonTool'
import SystemStatus from './components/SystemStatus'
import Login from './components/Login'
import { api, setUnauthorizedHandler, formatTokens } from './api.jsx'
import './App.css'

const load = (key, fallback) => {
  try {
    const raw = localStorage.getItem(key)
    return raw ? JSON.parse(raw) : fallback
  } catch {
    return fallback
  }
}
const save = (key, value) => {
  try { localStorage.setItem(key, JSON.stringify(value)) } catch { /* storage unavailable */ }
}

function App() {
  const [session, setSession] = useState(() => load('session', null))
  const [activeTab, setActiveTab] = useState('chat')
  const [systemStats, setSystemStats] = useState(null)
  const [error, setError] = useState(null)
  const [usage, setUsage] = useState({ total_tokens: 0 })
  const [llms, setLlms] = useState([])
  const [llmId, setLlmId] = useState(() => load('llmId', ''))
  const [profile, setProfile] = useState(() => load('profile', { budget: null, type: 'individual', risk_profile: 'moderate' }))

  const regionNames = Object.keys(systemStats?.by_region || {})
  const token = session?.token
  const user = session?.user
  const isAdmin = user?.role === 'admin'

  const logout = useCallback(() => {
    if (token) api('/api/auth/logout', { method: 'POST', token }).catch(() => {})
    localStorage.removeItem('session')
    setSession(null)
    setActiveTab('chat')
  }, [token])

  useEffect(() => {
    setUnauthorizedHandler(() => {
      localStorage.removeItem('session')
      setSession(null)
    })
  }, [])

  const handleLogin = (data) => {
    save('session', data)
    setSession(data)
  }

  const refreshLlms = useCallback(async () => {
    if (!token) return
    try {
      const list = await api('/api/llms', { token })
      setLlms(list)
      setLlmId((current) => (list.some((l) => l.id === current) ? current : list[0]?.id || ''))
    } catch { /* surfaced elsewhere */ }
  }, [token])

  const fetchSystemStats = useCallback(async () => {
    if (!token) return
    try {
      setSystemStats(await api('/api/system-stats', { token }))
      setError(null)
    } catch (err) {
      setError(err.message)
    }
  }, [token])

  useEffect(() => {
    if (!token) return
    api('/api/auth/me', { token }).then((d) => setUsage(d.usage)).catch(() => {})
    refreshLlms()
    fetchSystemStats()
    const interval = setInterval(fetchSystemStats, 30000)
    return () => clearInterval(interval)
  }, [token, refreshLlms, fetchSystemStats])

  useEffect(() => save('llmId', llmId), [llmId])
  useEffect(() => save('profile', profile), [profile])

  if (!session) return <Login onLogin={handleLogin} />

  const tabs = [
    { id: 'chat', label: 'Chat', icon: MessageSquare, title: 'Chat with investment consultant' },
    { id: 'compare', label: 'Compare', icon: BarChart3, title: 'Compare metrics across regions' },
    ...(isAdmin ? [{ id: 'status', label: 'Status', icon: Settings, title: 'Admin: system, users and LLMs' }] : [])
  ]

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <div className="header-title">
            <h1>Property Investment Consultant</h1>
            <p>AI-Powered RAG System for Global Real Estate Analysis</p>
          </div>
          <div className="header-user">
            <div className="token-counter" title="Total tokens you have used">
              <Coins size={16} /> {formatTokens(usage.total_tokens)} tokens
            </div>
            {llms.length > 0 && (
              <select className="llm-select" value={llmId} onChange={(e) => setLlmId(e.target.value)} title="Model">
                {llms.map((l) => (
                  <option key={l.id} value={l.id}>{l.name} ({l.model})</option>
                ))}
              </select>
            )}
            <span className="user-badge">{user.username}{isAdmin ? ' (admin)' : ''}</span>
            <button className="logout-button" onClick={logout} title="Sign out">
              <LogOut size={16} /> Sign out
            </button>
          </div>
        </div>
      </header>

      <div className="app-container">
        <nav className="app-nav">
          {tabs.map(({ id, label, icon: Icon, title }) => (
            <button
              key={id}
              className={`nav-button ${activeTab === id ? 'active' : ''}`}
              onClick={() => setActiveTab(id)}
              title={title}
            >
              <Icon size={20} />
              <span>{label}</span>
            </button>
          ))}
        </nav>

        <main className="app-main">
          {error && (
            <div className="error-banner">
              <p>{error}</p>
            </div>
          )}

          <div className="tab-pane" hidden={activeTab !== 'chat'}>
            <ChatConsultant
              token={token}
              llmId={llmId}
              profile={profile}
              onProfileChange={setProfile}
              onUsage={setUsage}
              hasLlm={llms.length > 0}
            />
          </div>

          <div className="tab-pane" hidden={activeTab !== 'compare'}>
            <ComparisonTool
              token={token}
              llmId={llmId}
              profile={profile}
              systemStats={systemStats}
              onUsage={setUsage}
            />
          </div>

          {isAdmin && (
            <div className="tab-pane" hidden={activeTab !== 'status'}>
              <SystemStatus
                token={token}
                currentUser={user}
                systemStats={systemStats}
                onReload={fetchSystemStats}
                onLlmsChanged={refreshLlms}
              />
            </div>
          )}
        </main>
      </div>

      <footer className="app-footer">
        <p title={regionNames.join(', ')}>
          Property Investment RAG Consultant © {new Date().getFullYear()} | Global real estate analysis
          {regionNames.length > 0 && ` | ${regionNames.length} ${regionNames.length === 1 ? 'market' : 'markets'} loaded`}
        </p>
      </footer>
    </div>
  )
}

export default App

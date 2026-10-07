import React, { useState, useEffect, useCallback } from 'react'
import { Plus, Trash2, PlugZap, Power, Pencil } from 'lucide-react'
import { api, formatTokens } from '../api.jsx'
import './AdminPanels.css'

const PROVIDERS = {
  openai: { label: 'OpenAI / OpenAI-compatible', model: 'gpt-4o-mini' },
  anthropic: { label: 'Anthropic (Claude)', model: 'claude-haiku-4-5-20251001' },
  gemini: { label: 'Google Gemini', model: 'gemini-2.0-flash' }
}

export function LlmPanel({ token, onChanged }) {
  const [llms, setLlms] = useState([])
  const [form, setForm] = useState({ name: '', provider: 'openai', model: PROVIDERS.openai.model, api_key: '', base_url: '' })
  const [notice, setNotice] = useState(null)
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    try {
      setLlms(await api('/api/admin/llms', { token }))
    } catch (err) {
      setNotice({ type: 'error', text: err.message })
    }
  }, [token])

  useEffect(() => { load() }, [load])

  const run = async (fn, successText) => {
    setBusy(true)
    setNotice(null)
    try {
      const result = await fn()
      setNotice({ type: result?.ok === false ? 'error' : 'success', text: result?.message || successText })
      await load()
      onChanged()
    } catch (err) {
      setNotice({ type: 'error', text: err.message })
    } finally {
      setBusy(false)
    }
  }

  const setField = (field, value) => setForm((f) => ({ ...f, [field]: value }))

  const handleProviderChange = (provider) => setForm((f) => ({ ...f, provider, model: PROVIDERS[provider].model }))

  const handleAdd = (e) => {
    e.preventDefault()
    run(async () => {
      await api('/api/admin/llms', { method: 'POST', token, body: form })
      setForm((f) => ({ ...f, name: '', api_key: '' }))
    }, 'LLM added. Use Test to verify the key.')
  }

  return (
    <div className="admin-panel">
      <h3>LLM Providers</h3>
      <p className="panel-hint">
        Users pick from the enabled models in the header. API keys are stored on the server and never shown again.
      </p>

      {llms.length === 0 && <p className="panel-empty">No LLMs yet. Add one below; until then the app only shows document excerpts.</p>}

      {llms.length > 0 && (
        <div className="table-wrap">
          <table className="admin-table">
            <thead>
              <tr><th>Name</th><th>Provider / model</th><th>Key</th><th>Tokens used</th><th>Status</th><th /></tr>
            </thead>
            <tbody>
              {llms.map((l) => (
                <tr key={l.id}>
                  <td>{l.name}</td>
                  <td>{l.provider} / {l.model}{l.base_url && <div className="muted">{l.base_url}</div>}</td>
                  <td className="mono">{l.api_key_masked}</td>
                  <td>{formatTokens(l.usage.total_tokens)} <span className="muted">({l.usage.requests} req)</span></td>
                  <td><span className={`pill ${l.enabled ? 'on' : 'off'}`}>{l.enabled ? 'Enabled' : 'Disabled'}</span></td>
                  <td className="row-actions">
                    <button disabled={busy} title="Change model (same API key)"
                      onClick={() => {
                        const model = window.prompt(`Model for ${l.name}

Examples: gpt-4o-mini, gpt-4o, gpt-4.1, gpt-4.1-mini`, l.model)
                        if (model && model.trim() && model.trim() !== l.model) {
                          run(async () => {
                            await api(`/api/admin/llms/${l.id}`, { method: 'PATCH', token, body: { model: model.trim() } })
                            return api(`/api/admin/llms/${l.id}/test`, { method: 'POST', token })
                          }, 'Model updated')
                        }
                      }}>
                      <Pencil size={15} />
                    </button>
                    <button disabled={busy || !l.enabled} title="Test connection"
                      onClick={() => run(() => api(`/api/admin/llms/${l.id}/test`, { method: 'POST', token }), 'Connected')}>
                      <PlugZap size={15} />
                    </button>
                    <button disabled={busy} title={l.enabled ? 'Disable' : 'Enable'}
                      onClick={() => run(() => api(`/api/admin/llms/${l.id}`, { method: 'PATCH', token, body: { enabled: !l.enabled } }), 'Updated')}>
                      <Power size={15} />
                    </button>
                    <button disabled={busy} title="Delete" className="danger"
                      onClick={() => window.confirm(`Delete ${l.name}?`) && run(() => api(`/api/admin/llms/${l.id}`, { method: 'DELETE', token }), 'Deleted')}>
                      <Trash2 size={15} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <form className="admin-form" onSubmit={handleAdd}>
        <input placeholder="Display name (e.g. GPT-4o mini)" value={form.name} onChange={(e) => setField('name', e.target.value)} />
        <select value={form.provider} onChange={(e) => handleProviderChange(e.target.value)}>
          {Object.entries(PROVIDERS).map(([id, p]) => <option key={id} value={id}>{p.label}</option>)}
        </select>
        <input placeholder="Model" value={form.model} onChange={(e) => setField('model', e.target.value)} />
        <input type="password" placeholder="API key" value={form.api_key} autoComplete="off" onChange={(e) => setField('api_key', e.target.value)} />
        {form.provider === 'openai' && (
          <input placeholder="Base URL (optional, for compatible APIs)" value={form.base_url} onChange={(e) => setField('base_url', e.target.value)} />
        )}
        <button type="submit" disabled={busy || !form.name || !form.model || !form.api_key}>
          <Plus size={16} /> Add LLM
        </button>
      </form>

      {notice && <div className={`panel-notice ${notice.type}`}>{notice.text}</div>}
    </div>
  )
}

export function UsersPanel({ token, currentUser }) {
  const [users, setUsers] = useState([])
  const [form, setForm] = useState({ username: '', password: '', role: 'user' })
  const [notice, setNotice] = useState(null)
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    try {
      setUsers(await api('/api/admin/users', { token }))
    } catch (err) {
      setNotice({ type: 'error', text: err.message })
    }
  }, [token])

  useEffect(() => { load() }, [load])

  const run = async (fn, successText) => {
    setBusy(true)
    setNotice(null)
    try {
      await fn()
      setNotice({ type: 'success', text: successText })
      await load()
    } catch (err) {
      setNotice({ type: 'error', text: err.message })
    } finally {
      setBusy(false)
    }
  }

  const handleAdd = (e) => {
    e.preventDefault()
    run(async () => {
      await api('/api/admin/users', { method: 'POST', token, body: form })
      setForm({ username: '', password: '', role: 'user' })
    }, 'User created')
  }

  return (
    <div className="admin-panel">
      <h3>Users</h3>
      <p className="panel-hint">Only admins can see the Status tab. Passwords need at least 6 characters.</p>

      <div className="table-wrap">
        <table className="admin-table">
          <thead>
            <tr><th>Username</th><th>Role</th><th>Tokens used</th><th>Requests</th><th /></tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.username}>
                <td>{u.username}{u.username === currentUser.username && <span className="muted"> (you)</span>}</td>
                <td><span className={`pill ${u.role === 'admin' ? 'on' : 'off'}`}>{u.role}</span></td>
                <td>{formatTokens(u.usage.total_tokens)}</td>
                <td>{u.usage.requests}</td>
                <td className="row-actions">
                  <button className="danger" title="Delete user"
                    disabled={busy || u.username === currentUser.username}
                    onClick={() => window.confirm(`Delete user ${u.username}?`) && run(() => api(`/api/admin/users/${encodeURIComponent(u.username)}`, { method: 'DELETE', token }), 'User deleted')}>
                    <Trash2 size={15} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <form className="admin-form" onSubmit={handleAdd}>
        <input placeholder="Username" value={form.username} autoComplete="off" onChange={(e) => setForm({ ...form, username: e.target.value })} />
        <input type="password" placeholder="Password (min 6 chars)" value={form.password} autoComplete="new-password" onChange={(e) => setForm({ ...form, password: e.target.value })} />
        <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
          <option value="user">User</option>
          <option value="admin">Admin</option>
        </select>
        <button type="submit" disabled={busy || !form.username || form.password.length < 6}>
          <Plus size={16} /> Add user
        </button>
      </form>

      {notice && <div className={`panel-notice ${notice.type}`}>{notice.text}</div>}
    </div>
  )
}

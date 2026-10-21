import React, { useState } from 'react'
import { X } from 'lucide-react'
import { api } from '../api.jsx'
import './ChangePassword.css'

const MIN_LENGTH = 8

function ChangePassword({ token, onClose }) {
  const [form, setForm] = useState({ current: '', next: '', confirm: '' })
  const [error, setError] = useState(null)
  const [done, setDone] = useState(false)
  const [busy, setBusy] = useState(false)

  const set = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }))
  const tooShort = form.next.length > 0 && form.next.length < MIN_LENGTH
  const mismatch = form.confirm.length > 0 && form.next !== form.confirm
  const canSubmit = form.current && form.next.length >= MIN_LENGTH && form.next === form.confirm && !busy

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await api('/api/auth/change-password', {
        method: 'POST',
        token,
        body: { current_password: form.current, new_password: form.next }
      })
      setDone(true)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose} role="presentation">
      <div className="modal-card" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true" aria-label="Change password">
        <button className="modal-close" onClick={onClose} title="Close"><X size={18} /></button>
        <h2>Change password</h2>

        {done ? (
          <>
            <div className="modal-notice success">Password changed. Your other sessions have been signed out.</div>
            <button className="modal-primary" onClick={onClose}>Done</button>
          </>
        ) : (
          <form onSubmit={submit}>
            <label>Current password</label>
            <input type="password" value={form.current} onChange={set('current')} autoComplete="current-password" autoFocus />

            <label>New password</label>
            <input type="password" value={form.next} onChange={set('next')} autoComplete="new-password" />
            {tooShort && <div className="modal-hint">At least {MIN_LENGTH} characters.</div>}

            <label>Confirm new password</label>
            <input type="password" value={form.confirm} onChange={set('confirm')} autoComplete="new-password" />
            {mismatch && <div className="modal-hint">The passwords do not match.</div>}

            {error && <div className="modal-notice error">{error}</div>}

            <button type="submit" className="modal-primary" disabled={!canSubmit}>
              {busy ? 'Saving...' : 'Change password'}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}

export default ChangePassword

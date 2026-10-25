import { useState, useEffect, useRef } from 'react'
import { X } from 'lucide-react'
import { api } from '../api.jsx'
import './ChangePassword.css'

const MIN_LENGTH = 8

function ChangePassword({ token, onClose }) {
  const [form, setForm] = useState({ current: '', next: '', confirm: '' })
  const [error, setError] = useState(null)
  const [done, setDone] = useState(false)
  const [busy, setBusy] = useState(false)
  const dialogRef = useRef(null)

  useEffect(() => {
    const previousFocus = document.activeElement
    const dialog = dialogRef.current
    dialog.querySelector('input, button')?.focus()
    const handleKey = (event) => {
      if (event.key === 'Escape') onClose()
      if (event.key !== 'Tab') return
      const controls = [...dialog.querySelectorAll('button:not(:disabled), input:not(:disabled)')]
      const first = controls[0]
      const last = controls[controls.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last?.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first?.focus()
      }
    }
    dialog.addEventListener('keydown', handleKey)
    return () => {
      dialog.removeEventListener('keydown', handleKey)
      previousFocus?.focus()
    }
  }, [onClose])

  useEffect(() => {
    if (done) dialogRef.current.querySelector('.modal-primary')?.focus()
  }, [done])

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
    <div className="modal-backdrop" onClick={(e) => { if (e.target === e.currentTarget) onClose() }} role="presentation">
      <div ref={dialogRef} className="modal-card" role="dialog" aria-modal="true" aria-label="Change password">
        <button className="modal-close" onClick={onClose} title="Close"><X size={18} /></button>
        <h2>Change password</h2>

        {done ? (
          <>
            <div className="modal-notice success">Password changed. Your other sessions have been signed out.</div>
            <button className="modal-primary" onClick={onClose}>Done</button>
          </>
        ) : (
          <form onSubmit={submit}>
            <label htmlFor="changepassword-field-1">Current password</label>
            <input id="changepassword-field-1" type="password" value={form.current} onChange={set('current')} autoComplete="current-password" />

            <label htmlFor="changepassword-field-2">New password</label>
            <input id="changepassword-field-2" type="password" value={form.next} onChange={set('next')} autoComplete="new-password" />
            {tooShort && <div className="modal-hint">At least {MIN_LENGTH} characters.</div>}

            <label htmlFor="changepassword-field-3">Confirm new password</label>
            <input id="changepassword-field-3" type="password" value={form.confirm} onChange={set('confirm')} autoComplete="new-password" />
            {mismatch && <div className="modal-hint">The passwords do not match.</div>}

            {error && <div role="alert" className="modal-notice error">{error}</div>}

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

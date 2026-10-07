import React, { useState, useEffect } from 'react'
import { Settings, RefreshCw, Database, FileText, CheckCircle } from 'lucide-react'
import { api } from '../api.jsx'
import { LlmPanel, UsersPanel } from './AdminPanels'
import './SystemStatus.css'

function SystemStatus({ token, currentUser, systemStats, onReload, onLlmsChanged }) {
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState(null)
  const [savedAnswers, setSavedAnswers] = useState(0)

  useEffect(() => {
    api('/api/admin/cache', { token }).then(d => setSavedAnswers(d.saved_answers)).catch(() => {})
  }, [token])

  const handleClearCache = async () => {
    try {
      const data = await api('/api/admin/cache', { method: 'DELETE', token })
      setSavedAnswers(0)
      setMessage({ type: 'success', text: `Cleared ${data.cleared} saved answers` })
    } catch (error) {
      setMessage({ type: 'error', text: error.message })
    }
  }

  const handleReload = async () => {
    setLoading(true)
    setMessage(null)

    try {
      const data = await api('/api/reload-documents', { method: 'POST', token })

      if (data.status === 'success') {
        setMessage({ type: 'success', text: data.message })
        onReload()
      } else {
        setMessage({ type: 'error', text: data.message })
      }
    } catch (error) {
      setMessage({ type: 'error', text: `Error: ${error.message}` })
    } finally {
      setLoading(false)
    }
  }

  const totalSize = (systemStats?.total_characters / (1024 * 1024)).toFixed(2)

  return (
    <div className="system-status">
      <div className="status-header">
        <h2><Settings size={24} /> Admin: System, LLMs & Users</h2>
        <p>Manage data, language models, users and token usage</p>
      </div>

      <div className="status-grid">
        {/* Overall Statistics */}
        <div className="status-card">
          <div className="card-icon documents">
            <FileText size={32} />
          </div>
          <div className="card-content">
            <div className="stat-label">Total Documents</div>
            <div className="stat-value">{systemStats?.total_documents || 0}</div>
          </div>
        </div>

        <div className="status-card">
          <div className="card-icon database">
            <Database size={32} />
          </div>
          <div className="card-content">
            <div className="stat-label">Data Size</div>
            <div className="stat-value">{totalSize} MB</div>
          </div>
        </div>

        <div className="status-card">
          <div className="card-icon health">
            <CheckCircle size={32} />
          </div>
          <div className="card-content">
            <div className="stat-label">System Status</div>
            <div className="stat-value">
              <span className="status-badge online">Online</span>
            </div>
          </div>
        </div>
      </div>

      {/* Regional Distribution */}
      <div className="status-section">
        <h3>Documents by Region</h3>
        <div className="region-stats">
          {systemStats?.by_region && Object.entries(systemStats.by_region).map(([region, count]) => (
            <div key={region} className="region-stat">
              <div className="region-name">{region}</div>
              <div className="region-bar">
                <div
                  className="region-fill"
                  style={{
                    width: `${(count / systemStats.total_documents) * 100}%`
                  }}
                ></div>
              </div>
              <div className="region-count">{count} docs</div>
            </div>
          ))}
        </div>
      </div>

      {/* Document Types */}
      <div className="status-section">
        <h3>Documents by Type</h3>
        <div className="type-grid">
          {systemStats?.by_type && Object.entries(systemStats.by_type).map(([type, count]) => (
            <div key={type} className="type-card">
              <div className="type-label">{type}</div>
              <div className="type-value">{count}</div>
              <div className="type-percentage">
                {((count / systemStats.total_documents) * 100).toFixed(1)}%
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Actions */}
      <div className="status-section">
        <h3>System Management</h3>
        <div className="actions">
          <button
            className="action-button"
            onClick={handleReload}
            disabled={loading}
          >
            <RefreshCw size={18} />
            {loading ? 'Reloading...' : 'Reload Documents'}
          </button>
          <p className="action-description">
            Click to reload documents from the data directories. Use this after adding new property data files.
          </p>
        </div>

        <div className="actions">
          <button className="action-button" onClick={handleClearCache} disabled={savedAnswers === 0}>
            Clear saved answers ({savedAnswers})
          </button>
          <p className="action-description">
            Repeated questions reuse a saved answer and cost no tokens. Clear them after changing models or prompts.
          </p>
        </div>

        {message && (
          <div className={`message-box message-${message.type}`}>
            <p>{message.text}</p>
          </div>
        )}
      </div>

      <LlmPanel token={token} onChanged={onLlmsChanged} />
      <UsersPanel token={token} currentUser={currentUser} />
    </div>
  )
}

export default SystemStatus

import React, { useState, useEffect } from 'react'
import { BarChart3, Search } from 'lucide-react'
import { api, formatTokens, renderInline } from '../api.jsx'
import './ComparisonTool.css'

function ComparisonTool({ token, llmId, profile, systemStats, onUsage }) {
  const [metric, setMetric] = useState('rental yields')
  const [selectedRegions, setSelectedRegions] = useState([])
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const availableRegions = systemStats?.by_region ? Object.keys(systemStats.by_region) : []

  useEffect(() => {
    setSelectedRegions(prev => {
      const stillValid = prev.filter(r => availableRegions.includes(r))
      return stillValid.length > 0 ? stillValid : availableRegions.slice(0, 2)
    })
  }, [availableRegions.join('|')])
  const commonMetrics = [
    'rental yields',
    'property prices',
    'market growth',
    'affordability',
    'investment returns',
    'transaction volume',
    'regulatory environment',
    'ROI potential'
  ]

  const toggleRegion = (region) => {
    setSelectedRegions(prev =>
      prev.includes(region)
        ? prev.filter(r => r !== region)
        : [...prev, region]
    )
  }

  const handleCompare = async () => {
    if (!metric.trim() || selectedRegions.length === 0) {
      setError('Please select a metric and at least one region')
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const data = await api('/api/compare-regions', {
        method: 'POST',
        token,
        body: {
          metric,
          regions: selectedRegions,
          llm_id: llmId || null,
          user_profile: {
            budget: profile?.budget || null,
            type: profile?.type,
            risk_profile: profile?.risk_profile
          }
        }
      })
      setResult(data)
      if (data.user_usage) onUsage(data.user_usage)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="comparison-tool">
      <div className="comparison-header">
        <h2><BarChart3 size={24} /> Regional Comparison</h2>
        <p>Compare property investment metrics across different regions</p>
      </div>

      <div className="comparison-controls">
        <div className="control-group">
          <label>Metric to Compare:</label>
          <div className="metric-input">
            <input
              type="text"
              value={metric}
              onChange={(e) => setMetric(e.target.value)}
              placeholder="Enter metric or select from suggestions..."
            />
          </div>
          <div className="suggestions">
            {commonMetrics.map(m => (
              <button
                key={m}
                className={`suggestion-chip ${metric === m ? 'active' : ''}`}
                onClick={() => setMetric(m)}
              >
                {m}
              </button>
            ))}
          </div>
        </div>

        <div className="control-group">
          <label>Select Markets (cities / countries):</label>
          <div className="region-grid">
            {availableRegions.map(region => (
              <button
                key={region}
                className={`region-checkbox ${selectedRegions.includes(region) ? 'selected' : ''}`}
                onClick={() => toggleRegion(region)}
              >
                <input
                  type="checkbox"
                  checked={selectedRegions.includes(region)}
                  onChange={() => toggleRegion(region)}
                  aria-label={region}
                />
                <span>{region}</span>
              </button>
            ))}
          </div>
        </div>

        <button
          className="compare-button"
          onClick={handleCompare}
          disabled={loading || !metric.trim() || selectedRegions.length === 0}
        >
          <Search size={18} />
          {loading ? 'Comparing...' : 'Compare'}
        </button>
      </div>

      {error && (
        <div className="error-box">
          <p>{error}</p>
        </div>
      )}

      {result && (
        <div className="comparison-result">
          <div className="result-header">
            <h3>Comparison Results</h3>
            <p>
              Regions: {selectedRegions.join(', ')}
              {result.cached && <> · Saved answer · no tokens used</>}
              {result.usage && <> · {result.llm} · {formatTokens(result.usage.prompt_tokens)} in / {formatTokens(result.usage.completion_tokens)} out · {formatTokens(result.usage.total_tokens)} tokens</>}
            </p>
          </div>

          <div className="result-content">
            <div className="answer-box">
              <h4>Analysis</h4>
              <div className="answer-text">
                {result.answer.split('\n').map((line, idx) => (
                  <div key={idx}>{renderInline(line)}</div>
                ))}
              </div>
            </div>

            {result.sources.length > 0 && (
              <div className="sources-box">
                <h4>Data Sources</h4>
                <div className="sources-list">
                  {result.sources.map((src, idx) => (
                    <div key={idx} className="source-card">
                      <div className="source-file">{src.file}</div>
                      <div className="source-meta">
                        <span className="region-tag">{src.region}</span>
                        <span className="type-tag">{src.type}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {!result && !error && !loading && (
        <div className="empty-state">
          <BarChart3 size={48} />
          <p>Select a metric and regions to begin comparison</p>
        </div>
      )}
    </div>
  )
}

export default ComparisonTool

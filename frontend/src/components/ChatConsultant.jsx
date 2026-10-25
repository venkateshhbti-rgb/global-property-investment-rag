import { useState, useRef, useEffect } from 'react'
import { Send, MessageCircle, Copy, Check } from 'lucide-react'
import { api, formatTokens, renderInline } from '../api.jsx'
import './ChatConsultant.css'

function QuestionForm({ questions, onSubmit }) {
  const [answers, setAnswers] = useState(() => questions.map(() => ''))

  const setAnswer = (index, value) =>
    setAnswers(prev => prev.map((a, i) => (i === index ? value : a)))

  const handleSubmit = (e) => {
    e.preventDefault()
    const lines = questions.map((q, i) => `- ${q.question} ${answers[i].trim() || 'No preference'}`)
    onSubmit(`My answers:\n${lines.join('\n')}\nPlease give me the full analysis.`)
  }

  return (
    <form className="question-form" onSubmit={handleSubmit}>
      {questions.map((q, i) => (
        <div key={i} className="question-item">
          <div className="question-label">{i + 1}. {q.question}</div>
          {q.options.length > 0 && (
            <div className="question-options">
              {q.options.map(opt => (
                <button
                  type="button"
                  key={opt}
                  className={`option-chip ${answers[i] === opt ? 'selected' : ''}`}
                  aria-pressed={answers[i] === opt}
                  onClick={() => setAnswer(i, opt)}
                >
                  {opt}
                </button>
              ))}
            </div>
          )}
          <input
            type="text"
            aria-label={q.question} className="question-input"
            value={answers[i]}
            onChange={(e) => setAnswer(i, e.target.value)}
            placeholder="Pick an option or type your own answer"
          />
        </div>
      ))}
      <button type="submit" className="question-submit">Get my analysis</button>
    </form>
  )
}

function ChatConsultant({ token, llmId, profile: userProfile, onProfileChange, onUsage, hasLlm }) {
  const [messages, setMessages] = useState([
    {
      id: 1,
      role: 'assistant',
      content: 'Welcome to Property Investment Consultant! I can help you with:\n\n• Property market analysis for the cities and countries in your data\n• Rental yield comparisons\n• Investment recommendations based on your budget\n• Market trends and growth potential\n• Regulatory and tax information\n\nWhat would you like to know about real estate investment?',
      sources: []
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [showProfile, setShowProfile] = useState(false)
  const [copiedId, setCopiedId] = useState(null)
  const messagesEndRef = useRef(null)
  const messageIdRef = useRef(2)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleProfileUpdate = (field, value) => {
    onProfileChange({ ...userProfile, [field]: value })
  }

  const handleSendMessage = (e) => {
    e.preventDefault()
    sendText(input)
  }

  const sendText = async (text) => {
    if (!text.trim() || loading) return

    const userMessage = {
      id: messageIdRef.current++,
      role: 'user',
      content: text,
      sources: []
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      const data = await api('/api/chat', {
        method: 'POST',
        token,
        body: {
          messages: messages.concat([userMessage]).map(m => ({ role: m.role, content: m.content })),
          user_profile: {
            budget: userProfile.budget || null,
            type: userProfile.type,
            risk_profile: userProfile.risk_profile
          },
          llm_id: llmId || null
        }
      })

      const assistantMessage = {
        id: messageIdRef.current++,
        role: 'assistant',
        content: data.message.content,
        sources: data.sources || [],
        usage: data.usage,
        llm: data.llm,
        questions: data.clarifying_questions || null,
        cached: !!data.cached
      }

      setMessages(prev => [...prev, assistantMessage])
      if (data.user_usage) onUsage(data.user_usage)
    } catch (error) {
      const errorMessage = {
        id: messageIdRef.current++,
        role: 'assistant',
        content: `Error: ${error.message}`,
        failed: true,
        sources: []
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  const copyToClipboard = (text, id) => {
    navigator.clipboard.writeText(text)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  return (
    <div className="chat-consultant">
      <div className="chat-heading"><h2>Investment workspace</h2><p>Explore markets. Compare opportunities. Follow the evidence.</p></div>
      <div className="chat-messages" role="log" aria-label="Conversation" aria-live="polite">
        {messages.map(msg => (
          <div key={msg.id} className={`message message-${msg.role} ${msg.failed ? 'message-failed' : ''}`}>
            <div className="message-avatar">
              {msg.role === 'user' ? 'You' : <MessageCircle size={20} />}
            </div>
            <div className="message-content">
              <div className="message-text">
                {msg.content.split('\n').map((line, idx) => (
                  <div key={idx}>{renderInline(line)}</div>
                ))}
              </div>
              {msg.questions && msg.id === messages[messages.length - 1].id && !loading && (
                <QuestionForm questions={msg.questions} onSubmit={sendText} />
              )}
              {msg.sources && msg.sources.length > 0 && (
                <div className="message-sources">
                  <div className="sources-title">Sources:</div>
                  {msg.sources.map((src, idx) => (
                    <div key={idx} className="source-item">
                      <span className="source-file">{src.file}</span>
                      <span className="source-badge">{src.region}</span>
                      <span className="source-type">{src.type}</span>
                    </div>
                  ))}
                </div>
              )}
              {msg.cached && (
                <div className="message-usage">Saved answer · no tokens used</div>
              )}
              {msg.usage && (
                <div className="message-usage">
                  {msg.llm} · {formatTokens(msg.usage.prompt_tokens)} in / {formatTokens(msg.usage.completion_tokens)} out · {formatTokens(msg.usage.total_tokens)} tokens
                </div>
              )}
              <button
                className="copy-button"
                onClick={() => copyToClipboard(msg.content, msg.id)}
                aria-label={copiedId === msg.id ? 'Message copied' : 'Copy message'} title="Copy message"
              >
                {copiedId === msg.id ? (
                  <Check size={16} />
                ) : (
                  <Copy size={16} />
                )}
              </button>
            </div>
          </div>
        ))}
        {loading && (
          <div className="message message-assistant">
            <div className="message-avatar">
              <MessageCircle size={20} />
            </div>
            <div className="typing-indicator" role="status" aria-label="Reviewing sources and preparing your answer">
              <span></span><span></span><span></span>
            </div>
          </div>
        )}
        {messages.length === 1 && <div className="starter-prompts" aria-label="Suggested questions">
          {['Compare rental yields across available markets', 'What costs should I consider when buying a property?'].map(prompt => <button key={prompt} type="button" onClick={() => sendText(prompt)}>{prompt}</button>)}
        </div>}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-section">
        <button
          className="profile-toggle"
          onClick={() => setShowProfile(!showProfile)}
          aria-expanded={showProfile} aria-controls="investor-profile" title="Toggle investor profile"
        >
          {showProfile ? 'Hide investor profile' : 'Investor profile'}
        </button>

        {showProfile && (
          <div id="investor-profile" className="profile-panel">
            <div className="profile-field">
              <label htmlFor="chatconsultant-field-1">Budget (USD)</label>
              <input id="chatconsultant-field-1"
                type="number"
                value={userProfile.budget || ''}
                onChange={(e) => handleProfileUpdate('budget', e.target.value ? parseInt(e.target.value) : null)}
                placeholder="e.g., 500000"
              />
            </div>
            <div className="profile-field">
              <label htmlFor="chatconsultant-field-2">Investor Type</label>
              <select id="chatconsultant-field-2"
                value={userProfile.type}
                onChange={(e) => handleProfileUpdate('type', e.target.value)}
              >
                <option value="individual">Individual Investor</option>
                <option value="wealth_advisor">Wealth Advisor</option>
                <option value="relocation">Relocation/Migration</option>
              </select>
            </div>
            <div className="profile-field">
              <label htmlFor="chatconsultant-field-3">Risk Profile</label>
              <select id="chatconsultant-field-3"
                value={userProfile.risk_profile}
                onChange={(e) => handleProfileUpdate('risk_profile', e.target.value)}
              >
                <option value="conservative">Conservative</option>
                <option value="moderate">Moderate</option>
                <option value="aggressive">Aggressive</option>
              </select>
            </div>
          </div>
        )}

        <form onSubmit={handleSendMessage} className="chat-input-form">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={hasLlm ? "Ask about property markets, or answer the questions above..." : "No LLM configured - ask an admin to add one (showing excerpts only)"}
            disabled={loading}
            aria-label="Your property investment question" className="chat-input"
          />
          <button type="submit" disabled={loading || !input.trim()} aria-label="Send message" className="send-button">
            <Send size={20} />
          </button>
        </form>
      </div>
    </div>
  )
}

export default ChatConsultant

// ConversationPanel.jsx — Atlas conversation history and composer.
import { useEffect, useRef, useState } from 'react'
import { Download, MessagesSquare, Send, Trash2 } from 'lucide-react'
import { Panel } from './ui'
import { T } from './theme'

const timeNow = () =>
  new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })

const SUGGESTIONS = ['System status report', "What's the weather?", 'Tell me a joke']

export default function ConversationPanel({
  messages,
  isProcessing,
  onSend,
  onClear,
  inputRef,
  isListening,
  userName = 'Boss',
}) {
  const [value, setValue] = useState('')
  const localRef = useRef(null)
  const scrollRef = useRef(null)
  const ref = inputRef || localRef

  useEffect(() => {
    const el = scrollRef.current
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  }, [messages.length, isProcessing])

  const submit = () => {
    const text = value.trim()
    if (!text || isProcessing) return
    setValue('')
    onSend?.(text)
  }

  const extract = () => {
    const header = [
      'ATLAS CONVERSATION EXPORT',
      `Exported: ${new Date().toLocaleString()}`,
      '='.repeat(52),
      '',
    ]
    const body = messages.length
      ? messages.map(m => `[${m.time}] ${m.role === 'user' ? userName : 'ATLAS'}: ${m.text}`)
      : [`[${timeNow()}] ATLAS: Hello, I am ATLAS. All systems online. How can I assist you today, ${userName}?`]
    const now = new Date()
    const dateStamp = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
    const blob = new Blob([[...header, ...body].join('\n')], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `atlas-conversation-${dateStamp}.txt`
    document.body.appendChild(a)
    a.click()
    a.remove()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }

  return (
    <Panel
      title="Conversation"
      icon={MessagesSquare}
      style={{ height: '100%' }}
      bodyStyle={{ padding: 0, flex: 1, minHeight: 0 }}
      action={
        <div style={{ display: 'flex', gap: 6 }}>
          <button type="button" className="jv-ghost-btn" title="Clear conversation" onClick={onClear}>
            <Trash2 size={12} />
            <span className="jv-clear-label">Clear</span>
          </button>
          <button type="button" className="jv-ghost-btn" title="Download conversation" onClick={extract}>
            <Download size={12} />
            <span className="jv-extract-label">Extract Conversation</span>
          </button>
        </div>
      }
    >
      <div
        ref={scrollRef}
        style={{ flex: 1, minHeight: 0, overflowY: 'auto', padding: '16px 16px 12px', display: 'flex', flexDirection: 'column', gap: 12 }}
      >
        {messages.length === 0 && (
          <>
            <div
              style={{
                alignSelf: 'flex-start',
                maxWidth: '92%',
                padding: '13px 15px',
                borderRadius: 12,
                border: '1px solid rgba(56,189,248,0.14)',
                background: 'rgba(14,28,42,0.72)',
                animation: 'jvFadeUp 0.35s ease-out',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  marginBottom: 7,
                  fontFamily: T.mono,
                  fontSize: 8.5,
                  letterSpacing: '0.12em',
                  color: 'rgba(134,239,172,0.72)',
                }}
              >
                <span
                  style={{
                    width: 5,
                    height: 5,
                    borderRadius: '50%',
                    background: T.green,
                    boxShadow: `0 0 7px ${T.green}`,
                  }}
                />
                ATLAS · SYSTEM ONLINE
              </div>
              <p style={{ margin: 0, fontSize: 13, lineHeight: 1.65, color: '#c9dceb' }}>
                Hello, I am ATLAS. All systems online. How can I assist you today, {userName}?
              </p>
              <div style={{ marginTop: 7, fontSize: 9.5, color: T.dim, fontFamily: T.mono }}>{timeNow()}</div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 7, marginTop: 1 }}>
              <span style={{ fontFamily: T.mono, fontSize: 8.5, letterSpacing: '0.18em', color: T.dim }}>
                SUGGESTED
              </span>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {SUGGESTIONS.map(s => (
                  <button
                    key={s}
                    type="button"
                    className="jv-ghost-btn"
                    onClick={() => onSend?.(s)}
                    style={{ fontSize: 10.5, padding: '6px 9px' }}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          </>
        )}

        {messages.map(msg => {
          const user = msg.role === 'user'
          return (
            <div
              key={msg.id}
              style={{
                alignSelf: user ? 'flex-end' : 'flex-start',
                maxWidth: '90%',
                padding: '11px 14px',
                borderRadius: 12,
                border: '1px solid',
                borderColor: user ? 'rgba(56,189,248,0.30)' : 'rgba(56,189,248,0.12)',
                background: user ? 'rgba(56,189,248,0.13)' : 'rgba(14,28,42,0.72)',
                animation: 'jvFadeUp 0.22s ease-out',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  marginBottom: 5,
                  fontFamily: T.mono,
                  fontSize: 8.5,
                  letterSpacing: '0.08em',
                  textTransform: 'uppercase',
                  color: user ? 'rgba(186,230,253,0.68)' : T.dim,
                }}
              >
                <span>{user ? userName : 'ATLAS'}</span>
              </div>
              <pre
                style={{
                  margin: 0,
                  fontFamily: T.font,
                  fontSize: 12.5,
                  lineHeight: 1.65,
                  color: user ? '#eaf7ff' : '#c9dceb',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                }}
              >
                {msg.text}
              </pre>
              <div
                style={{
                  marginTop: 6,
                  textAlign: user ? 'right' : 'left',
                  fontFamily: T.mono,
                  fontSize: 9,
                  color: T.dim,
                }}
              >
                {msg.time}
              </div>
            </div>
          )
        })}

        {isProcessing && (
          <div
            style={{
              alignSelf: 'flex-start',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '11px 14px',
              borderRadius: 12,
              border: '1px solid rgba(56,189,248,0.12)',
              background: 'rgba(14,28,42,0.72)',
            }}
          >
            <div style={{ display: 'flex', gap: 4 }}>
              {[0, 1, 2].map(i => (
                <span
                  key={i}
                  style={{
                    width: 5,
                    height: 5,
                    borderRadius: '50%',
                    background: T.accent,
                    animation: `jvBounce 1s ease-in-out ${i * 0.14}s infinite`,
                  }}
                />
              ))}
            </div>
            <span style={{ fontSize: 11, color: T.muted }}>ATLAS is thinking…</span>
          </div>
        )}

        <div />
      </div>

      <div
        style={{
          flexShrink: 0,
          display: 'flex',
          gap: 8,
          padding: 12,
          borderTop: `1px solid ${T.borderSoft}`,
          background: 'rgba(3,9,16,0.32)',
        }}
      >
        <div style={{ position: 'relative', flex: 1, minWidth: 0 }}>
          <input
            ref={ref}
            value={value}
            onChange={e => setValue(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                submit()
              }
            }}
            placeholder={isListening ? 'Listening… speak now' : 'Type a message...'}
            aria-label="Message Atlas"
            style={{
              width: '100%',
              height: 44,
              padding: '0 14px',
              borderRadius: 10,
              border: '1px solid',
              borderColor: isListening ? 'rgba(56,189,248,0.5)' : T.border,
              background: 'rgba(5,13,22,0.85)',
              color: T.text,
              fontFamily: T.font,
              fontSize: 12.5,
              outline: 'none',
              transition: 'border-color 0.18s ease, box-shadow 0.18s ease',
            }}
          />
          {isListening && (
            <span
              style={{
                position: 'absolute',
                right: 10,
                top: '50%',
                transform: 'translateY(-50%)',
                width: 6,
                height: 6,
                borderRadius: '50%',
                background: T.accent,
                boxShadow: `0 0 8px ${T.accent}`,
                animation: 'jvDotPulse 1.2s ease-in-out infinite',
              }}
            />
          )}
        </div>

        <button
          type="button"
          className="jv-send-btn"
          title="Send message"
          aria-label="Send message"
          onClick={submit}
          disabled={isProcessing || !value.trim()}
          style={{
            width: 44,
            height: 44,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderRadius: 10,
            border: '1px solid rgba(56,189,248,0.45)',
            background: 'linear-gradient(180deg, #0ea5e9 0%, #0284c7 100%)',
            color: '#f0fbff',
            cursor: isProcessing || !value.trim() ? 'not-allowed' : 'pointer',
            opacity: isProcessing || !value.trim() ? 0.42 : 1,
            boxShadow: '0 8px 24px rgba(14,165,233,0.24), inset 0 1px 0 rgba(255,255,255,0.2)',
            flexShrink: 0,
            transition: 'opacity 0.18s ease, transform 0.18s ease, box-shadow 0.18s ease',
          }}
        >
          <Send size={17} strokeWidth={1.9} />
        </button>
      </div>
    </Panel>
  )
}

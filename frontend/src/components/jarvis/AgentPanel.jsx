// AgentPanel.jsx — on/off control panel for every Atlas agent.
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import toast from 'react-hot-toast'
import {
  Bot, Search, X, Smartphone, Laptop, Cloud, Globe2, ChevronDown, ChevronUp,
  Loader2, Play, RefreshCw, PhoneCall, PhoneOutgoing, ShieldAlert, Plus, Trash2, Radio,
} from 'lucide-react'
import useAtlasStore from '../../store/useAtlasStore'
import { T } from './theme'
import {
  getAgents, toggleAgent, bulkToggleAgents, testAgent,
  getContacts, addContact, deleteContact,
  getReceptionistStatus, setReceptionistBusy, simulateReceptionistCall,
  getReceptionistCalls, receptionistCallback, getConnectorStatus,
} from '../../services/api'
import { runNativeAction } from '../../services/native'

const CATEGORIES = [
  { id: 'all', label: 'All' },
  { id: 'core', label: 'Core' },
  { id: 'call', label: 'Call' },
  { id: 'study', label: 'Study' },
  { id: 'productivity', label: 'Productivity' },
  { id: 'security', label: 'Security' },
  { id: 'advanced', label: 'Advanced' },
]

const RISK = {
  safe: { label: 'Safe', color: T.green },
  confirm: { label: 'Confirm', color: T.amber },
  danger: { label: 'Danger', color: T.red },
}

const HEALTH = {
  ready: { label: 'Ready', color: T.green },
  setup: { label: 'Setup', color: T.amber },
  missing: { label: 'Missing', color: T.red },
  disabled: { label: 'Off', color: T.dim },
}

function platformMeta(p) {
  if (p === 'android' || p === 'ios' || p === 'phone') return { icon: Smartphone, label: p === 'phone' ? 'Phone' : p }
  if (p === 'pc') return { icon: Laptop, label: 'PC' }
  if (p === 'web') return { icon: Globe2, label: 'Web' }
  return { icon: Cloud, label: 'Cloud' }
}

function Toggle({ on, onClick, disabled }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      aria-label={on ? 'Turn agent off' : 'Turn agent on'}
      disabled={disabled}
      onClick={onClick}
      style={{
        width: 38, height: 21, borderRadius: 999, padding: 2, flexShrink: 0,
        border: `1px solid ${on ? 'rgba(34,197,94,0.55)' : 'rgba(123,149,171,0.35)'}`,
        background: on ? 'rgba(34,197,94,0.2)' : 'rgba(8,18,30,0.9)',
        cursor: disabled ? 'wait' : 'pointer', opacity: disabled ? 0.6 : 1,
        transition: 'background 0.18s, border-color 0.18s',
      }}
    >
      <span
        style={{
          display: 'block', width: 15, height: 15, borderRadius: '50%',
          background: on ? T.green : '#5b7186',
          boxShadow: on ? `0 0 10px ${T.green}` : 'none',
          transform: on ? 'translateX(17px)' : 'translateX(0)',
          transition: 'transform 0.18s, background 0.18s',
        }}
      />
    </button>
  )
}

function Badge({ children, color = T.muted, bg = 'rgba(56,189,248,0.06)' }) {
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      padding: '3px 6px', borderRadius: 5, fontSize: 9,
      color, background: bg, border: `1px solid ${color}33`,
      whiteSpace: 'nowrap', lineHeight: 1.1,
    }}>
      {children}
    </span>
  )
}

function ContactSetup({ onChanged }) {
  const [contacts, setContacts] = useState([])
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    try {
      const data = await getContacts()
      setContacts(data.contacts || [])
    } catch { /* ignore */ }
  }, [])

  useEffect(() => { load() }, [load])

  const save = async () => {
    if (!name.trim() || !phone.trim()) {
      toast.error('Name and phone number are required')
      return
    }
    setSaving(true)
    try {
      await addContact(name.trim(), phone.trim())
      setName('')
      setPhone('')
      await load()
      onChanged?.()
      toast.success('Contact saved')
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Could not save contact')
    } finally {
      setSaving(false)
    }
  }

  const remove = async (contactName) => {
    try {
      await deleteContact(contactName)
      await load()
      onChanged?.()
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Could not delete contact')
    }
  }

  return (
    <div style={{ marginTop: 10, padding: 10, borderRadius: 8, background: 'rgba(3,9,16,0.55)', border: `1px solid ${T.borderSoft}` }}>
      <div style={{ fontSize: 10, color: T.muted, marginBottom: 7, display: 'flex', alignItems: 'center', gap: 5 }}>
        <PhoneCall size={12} color={T.accent} /> Saved contacts
      </div>
      {contacts.length === 0 ? (
        <div style={{ fontSize: 10, color: T.dim, marginBottom: 7 }}>No contacts yet. Add “Ammu” below.</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginBottom: 8 }}>
          {contacts.map(c => (
            <div key={c.name} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 10.5 }}>
              <span style={{ color: T.text, flex: 1 }}>{c.name}</span>
              <span style={{ color: T.muted, fontFamily: T.mono }}>{c.phone || 'no number'}</span>
              <button type="button" title="Delete contact" onClick={() => remove(c.name)} style={{ background: 'none', border: 0, color: T.dim, cursor: 'pointer', padding: 2 }}>
                <Trash2 size={11} />
              </button>
            </div>
          ))}
        </div>
      )}
      <div style={{ display: 'flex', gap: 5 }}>
        <input value={name} onChange={e => setName(e.target.value)} placeholder="Name (Ammu)" style={{ ...inputStyle, flex: 1 }} />
        <input value={phone} onChange={e => setPhone(e.target.value)} placeholder="+8801..." style={{ ...inputStyle, flex: 1.2 }} />
        <button type="button" onClick={save} disabled={saving} style={{ ...miniButton, color: T.accent, borderColor: 'rgba(56,189,248,0.35)' }} title="Add contact">
          {saving ? <Loader2 size={12} className="jv-spin" /> : <Plus size={13} />}
        </button>
      </div>
    </div>
  )
}

const inputStyle = {
  background: 'rgba(8,18,30,0.9)', border: `1px solid ${T.border}`,
  borderRadius: 6, color: T.text, padding: '6px 7px', fontSize: 10.5,
  outline: 'none', minWidth: 0,
}

const miniButton = {
  display: 'inline-flex', alignItems: 'center', gap: 4,
  padding: '5px 8px', borderRadius: 6, border: `1px solid ${T.border}`,
  background: 'rgba(8,18,30,0.8)', color: T.muted, cursor: 'pointer',
  fontSize: 10, whiteSpace: 'nowrap',
}

function AgentCard({ agent, onToggle, busy, expanded, onExpand, onTest, onRefresh }) {
  const risk = RISK[agent.risk] || RISK.safe
  const health = HEALTH[agent.health?.status] || HEALTH.disabled
  const isCallAgent = agent.id === 'whatsapp_call' || agent.id === 'call_receptionist'

  return (
    <div style={{
      border: `1px solid ${agent.enabled ? 'rgba(56,189,248,0.18)' : T.borderSoft}`,
      borderRadius: 10, padding: 10,
      background: agent.enabled ? 'rgba(12,25,38,0.72)' : 'rgba(7,14,23,0.55)',
      opacity: agent.enabled ? 1 : 0.78,
    }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
        <div style={{
          width: 30, height: 30, borderRadius: 8, flexShrink: 0,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: agent.enabled ? 'rgba(56,189,248,0.1)' : 'rgba(56,189,248,0.04)',
          border: `1px solid ${agent.enabled ? 'rgba(56,189,248,0.22)' : T.borderSoft}`,
          fontSize: 15,
        }}>
          {agent.icon || '🤖'}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: 11.5, fontWeight: 600, color: T.text, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {agent.name}
            </span>
            <span style={{ width: 5, height: 5, borderRadius: '50%', background: risk.color, boxShadow: `0 0 5px ${risk.color}`, flexShrink: 0 }} />
          </div>
          <div style={{ fontSize: 9.8, color: T.muted, lineHeight: 1.4, marginTop: 2 }}>
            {agent.description}
          </div>
        </div>
        <Toggle on={agent.enabled} disabled={busy} onClick={() => onToggle(agent)} />
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 7, paddingLeft: 38 }}>
        {(agent.platforms || []).map(p => {
          const meta = platformMeta(p)
          const Icon = meta.icon
          return <Badge key={p} color={T.muted}><Icon size={9} /> {meta.label}</Badge>
        })}
        <Badge color={risk.color}>{risk.label}</Badge>
        <Badge color={health.color}>{health.label}</Badge>
      </div>

      <div style={{ marginTop: 6, paddingLeft: 38, display: 'flex', alignItems: 'center', gap: 6 }}>
        <div style={{ flex: 1, fontSize: 9.3, color: T.dim, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {(agent.steps || []).join(' → ')}
        </div>
        <button type="button" onClick={() => onExpand(agent.id)} style={{ background: 'none', border: 0, color: T.muted, cursor: 'pointer', padding: 2 }} title="Details">
          {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        </button>
      </div>

      {expanded && (
        <div style={{ marginTop: 8, paddingLeft: 38 }}>
          {agent.health?.note && (
            <div style={{ fontSize: 9.5, color: agent.health.status === 'ready' ? '#86efac' : T.amber, marginBottom: 7, lineHeight: 1.4 }}>
              {agent.health.note}
            </div>
          )}
          {(agent.health?.missing || []).length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginBottom: 7 }}>
              {agent.health.missing.map(m => <Badge key={m} color={T.amber}><ShieldAlert size={9} /> {m}</Badge>)}
            </div>
          )}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
            <button type="button" onClick={() => onTest(agent.id)} style={miniButton}>
              <Play size={11} /> Test
            </button>
            {isCallAgent && (
              <button type="button" onClick={onRefresh} style={miniButton}>
                <RefreshCw size={11} /> Refresh
              </button>
            )}
          </div>
          {agent.id === 'whatsapp_call' && <ContactSetup onChanged={onRefresh} />}
          {agent.id === 'call_receptionist' && <ReceptionistControls onChanged={onRefresh} />}
        </div>
      )}
    </div>
  )
}

function ReceptionistControls({ onChanged }) {
  const [status, setStatus] = useState(null)
  const [calls, setCalls] = useState([])
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    try {
      const [data, callData] = await Promise.all([
        getReceptionistStatus(),
        getReceptionistCalls(5),
      ])
      setStatus(data)
      setBusy(Boolean(data.busy))
      setCalls(callData.calls || [])
    } catch { /* ignore */ }
  }, [])

  useEffect(() => { load() }, [load])

  const toggleBusy = async () => {
    setLoading(true)
    try {
      const data = await setReceptionistBusy(!busy)
      setBusy(Boolean(data.busy))
      toast.success(data.message || 'Busy mode updated')
      await load()
      onChanged?.()
    } catch {
      toast.error('Could not update busy mode')
    } finally {
      setLoading(false)
    }
  }

  const simulate = async () => {
    setLoading(true)
    try {
      const data = await simulateReceptionistCall({
        caller_name: 'Test Caller',
        caller_number: '+8801000000000',
        message: 'I need a callback about the project.',
        urgency: 'normal',
      })
      toast.success('Test call saved to the call inbox')
      await load()
      onChanged?.()
      return data
    } catch {
      toast.error('Could not simulate a call')
    } finally {
      setLoading(false)
    }
  }

  const callBack = async (call) => {
    setLoading(true)
    try {
      const res = await receptionistCallback(call.id)
      const nativeRes = await runNativeAction(res)
      toast.success((nativeRes || res)?.message || 'Callback started')
      await load()
      onChanged?.()
    } catch {
      toast.error('Could not start callback')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ marginTop: 9, padding: 9, borderRadius: 8, background: 'rgba(3,9,16,0.55)', border: `1px solid ${T.borderSoft}` }}>
      <div style={{ display: 'flex', gap: 5, marginBottom: 7 }}>
        <button type="button" onClick={toggleBusy} disabled={loading} style={{ ...miniButton, color: busy ? '#fca5a5' : '#86efac', borderColor: busy ? 'rgba(239,68,68,0.35)' : 'rgba(34,197,94,0.35)' }}>
          <Radio size={11} /> Busy {busy ? 'ON' : 'OFF'}
        </button>
        <button type="button" onClick={simulate} disabled={loading} style={miniButton}>
          {loading ? <Loader2 size={11} className="jv-spin" /> : <PhoneCall size={11} />} Simulate call
        </button>
      </div>
      <div style={{ fontSize: 9.5, color: T.muted, lineHeight: 1.45 }}>
        Provider: <span style={{ color: status?.provider?.real_calls ? T.green : T.amber }}>{status?.provider?.provider || 'simulator'}</span>
        {status?.provider?.number ? ` · ${status.provider.number}` : ' · virtual number not configured'}
        <br />Calls saved: {status?.calls_count ?? 0}
      </div>

      {calls.length > 0 && (
        <div style={{ marginTop: 7, display: 'flex', flexDirection: 'column', gap: 4 }}>
          {calls.map(call => (
            <div key={call.id} style={{
              display: 'flex', alignItems: 'center', gap: 5, padding: '4px 5px',
              borderRadius: 5, background: 'rgba(8,18,30,0.7)', border: `1px solid ${T.borderSoft}`,
            }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 9.8, color: T.text, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {call.caller_name || call.caller_number}
                  {call.urgency === 'urgent' ? <span style={{ color: '#fca5a5' }}> · urgent</span> : null}
                </div>
                <div style={{ fontSize: 8.8, color: T.dim, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {call.summary || call.notification || 'No summary'}
                </div>
              </div>
              <button
                type="button"
                onClick={() => callBack(call)}
                disabled={loading}
                style={{ ...miniButton, padding: '4px 6px', color: T.accent, borderColor: 'rgba(56,189,248,0.3)' }}
                title={`Call back ${call.caller_name || call.caller_number}`}
              >
                <PhoneOutgoing size={11} /> Call back
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function AgentPanel({ open, onClose }) {
  const {
    agents, setAgents, agentsLoading, setAgentsLoading, updateAgent,
  } = useAtlasStore()
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('all')
  const [busyId, setBusyId] = useState('')
  const [expanded, setExpanded] = useState('')
  const [bulkBusy, setBulkBusy] = useState(false)
  const [connector, setConnector] = useState(null)
  const ref = useRef(null)

  const load = useCallback(async () => {
    setAgentsLoading(true)
    try {
      const data = await getAgents()
      setAgents(data.agents || [])
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Could not load agents')
    } finally {
      setAgentsLoading(false)
    }
    try {
      setConnector(await getConnectorStatus())
    } catch { /* connector is optional */ }
  }, [setAgents, setAgentsLoading])

  useEffect(() => {
    if (!open) return
    if (!agents.length) load()
  }, [open, agents.length, load])

  useEffect(() => {
    if (!open) return
    const onPointer = e => {
      if (ref.current && !ref.current.contains(e.target)) onClose()
    }
    const onKey = e => { if (e.key === 'Escape') onClose() }
    document.addEventListener('mousedown', onPointer)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onPointer)
      document.removeEventListener('keydown', onKey)
    }
  }, [open, onClose])

  const enabledCount = agents.filter(a => a.enabled).length

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return agents.filter(a => {
      if (category !== 'all' && a.category !== category) return false
      if (!q) return true
      return `${a.name} ${a.description} ${(a.steps || []).join(' ')}`.toLowerCase().includes(q)
    })
  }, [agents, category, query])

  const counts = useMemo(() => {
    const out = { all: agents.length }
    agents.forEach(a => { out[a.category] = (out[a.category] || 0) + 1 })
    return out
  }, [agents])

  if (!open) return null

  const handleToggle = async (agent) => {
    const next = !agent.enabled
    setBusyId(agent.id)
    updateAgent(agent.id, { enabled: next })
    try {
      const res = await toggleAgent(agent.id, next)
      if (!res.success) throw new Error(res.error || 'Toggle failed')
      if (res.agent_info) updateAgent(agent.id, res.agent_info)
      toast.success(`${agent.name} ${next ? 'ON' : 'OFF'}`)
    } catch (e) {
      updateAgent(agent.id, { enabled: agent.enabled })
      toast.error(e?.response?.data?.detail || e.message || 'Toggle failed')
    } finally {
      setBusyId('')
    }
  }

  const handleBulk = async (enabled) => {
    setBulkBusy(true)
    try {
      await bulkToggleAgents(enabled, category === 'all' ? undefined : category)
      await load()
      toast.success(`${category === 'all' ? 'All agents' : category} turned ${enabled ? 'ON' : 'OFF'}`)
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Bulk toggle failed')
    } finally {
      setBulkBusy(false)
    }
  }

  const handleTest = async (id) => {
    setBusyId(id)
    try {
      const res = await testAgent(id)
      if (res.success) toast.success(res.message || 'Agent is ready')
      else toast.error(res.message || res.error || 'Agent test failed')
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Agent test failed')
    } finally {
      setBusyId('')
    }
  }

  return (
    <div
      ref={ref}
      className="jv-agent-popover"
      style={{
        position: 'absolute', top: 'calc(100% + 10px)', right: 0,
        width: 474, maxWidth: 'calc(100vw - 24px)',
        maxHeight: 'calc(100vh - 84px)',
        display: 'flex', flexDirection: 'column',
        borderRadius: 12,
        background: 'linear-gradient(180deg, rgba(13,27,42,0.99) 0%, rgba(8,17,28,0.99) 100%)',
        border: `1px solid ${T.border}`,
        boxShadow: '0 24px 60px rgba(0,0,0,0.6), 0 0 0 1px rgba(56,189,248,0.05)',
        zIndex: 120, overflow: 'hidden', animation: 'jvPop 0.18s ease-out',
      }}
    >
      {/* Header */}
      <div style={{ padding: '12px 13px 10px', borderBottom: `1px solid ${T.borderSoft}`, flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ width: 28, height: 28, borderRadius: 8, background: T.accentSoft, border: '1px solid rgba(56,189,248,0.25)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Bot size={15} color={T.accent} />
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 11.5, fontWeight: 600, color: T.text, letterSpacing: '0.06em' }}>AGENT CONTROL</div>
            <div style={{ fontSize: 9.5, color: T.muted, marginTop: 1 }}>{enabledCount} of {agents.length} agents active</div>
          </div>
          <button type="button" onClick={onClose} style={{ background: 'none', border: 0, color: T.muted, cursor: 'pointer', padding: 2 }} title="Close">
            <X size={16} />
          </button>
        </div>

        <div style={{ display: 'flex', gap: 6, marginTop: 10 }}>
          <div style={{ flex: 1, position: 'relative' }}>
            <Search size={12} color={T.dim} style={{ position: 'absolute', left: 8, top: '50%', transform: 'translateY(-50%)' }} />
            <input
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="Search agents..."
              style={{ ...inputStyle, width: '100%', paddingLeft: 25, boxSizing: 'border-box' }}
            />
          </div>
          <button type="button" disabled={bulkBusy} onClick={() => handleBulk(true)} style={{ ...miniButton, color: '#86efac', borderColor: 'rgba(34,197,94,0.3)' }}>
            {bulkBusy ? <Loader2 size={11} className="jv-spin" /> : null} All On
          </button>
          <button type="button" disabled={bulkBusy} onClick={() => handleBulk(false)} style={{ ...miniButton, color: '#fca5a5', borderColor: 'rgba(239,68,68,0.25)' }}>
            All Off
          </button>
        </div>

        <div style={{ display: 'flex', gap: 4, marginTop: 8, overflowX: 'auto', paddingBottom: 2 }}>
          {CATEGORIES.map(cat => {
            const active = category === cat.id
            const count = counts[cat.id] || 0
            return (
              <button
                key={cat.id}
                type="button"
                onClick={() => setCategory(cat.id)}
                style={{
                  padding: '4px 7px', borderRadius: 6, fontSize: 9.5, cursor: 'pointer',
                  border: `1px solid ${active ? 'rgba(56,189,248,0.4)' : T.borderSoft}`,
                  background: active ? 'rgba(56,189,248,0.12)' : 'transparent',
                  color: active ? '#c9edff' : T.muted, whiteSpace: 'nowrap',
                }}
              >
                {cat.label} {count > 0 ? <span style={{ opacity: 0.65 }}>{count}</span> : null}
              </button>
            )
          })}
        </div>
      </div>

      {/* List */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '9px 10px', display: 'flex', flexDirection: 'column', gap: 7 }}>
        {agentsLoading && !agents.length ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, padding: 30, color: T.muted, fontSize: 11 }}>
            <Loader2 size={15} className="jv-spin" /> Loading agents...
          </div>
        ) : filtered.length === 0 ? (
          <div style={{ padding: 26, textAlign: 'center', color: T.dim, fontSize: 11 }}>No agents match this filter.</div>
        ) : (
          filtered.map(agent => (
            <AgentCard
              key={agent.id}
              agent={agent}
              busy={busyId === agent.id}
              expanded={expanded === agent.id}
              onToggle={handleToggle}
              onExpand={id => setExpanded(prev => prev === id ? '' : id)}
              onTest={handleTest}
              onRefresh={load}
            />
          ))
        )}
      </div>

      {/* Footer */}
      <div style={{ padding: '8px 12px', borderTop: `1px solid ${T.borderSoft}`, display: 'flex', alignItems: 'center', gap: 7, flexShrink: 0 }}>
        <span style={{ fontSize: 9.5, color: T.dim, flex: 1, display: 'flex', alignItems: 'center', gap: 5 }}>
          <span style={{
            width: 5, height: 5, borderRadius: '50%',
            background: connector?.connected ? T.green : T.dim,
            boxShadow: connector?.connected ? `0 0 6px ${T.green}` : 'none',
          }} />
          {connector?.connected
            ? `Laptop relay: ${connector.name || 'connected'}`
            : 'Laptop relay: offline'}
        </span>
        <button type="button" onClick={load} disabled={agentsLoading} style={{ ...miniButton, padding: '4px 7px' }}>
          <RefreshCw size={11} className={agentsLoading ? 'jv-spin' : ''} /> Refresh
        </button>
      </div>
    </div>
  )
}

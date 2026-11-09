// Small shared primitives for the Atlas JARVIS interface.

import { T, panelStyle, headerStyle, titleStyle, iconButtonStyle, miniStat, miniLabel, miniValue } from './theme'

export function Panel({ title, icon: Icon, action, children, style, bodyStyle, accent }) {
  return (
    <section className="jv-panel" style={{ ...panelStyle, ...style }}>
      <div style={headerStyle}>
        {Icon && <Icon size={15} color={accent || T.accent} strokeWidth={1.8} />}
        <span style={titleStyle}>{title}</span>
        {action}
      </div>
      <div style={{ padding: 10, display: 'flex', flexDirection: 'column', minHeight: 0, ...bodyStyle }}>
        {children}
      </div>
    </section>
  )
}

export function IconButton({ children, title, onClick, active, disabled, style }) {
  return (
    <button
      type="button"
      className="jv-icon-btn"
      title={title}
      onClick={onClick}
      disabled={disabled}
      style={{
        ...iconButtonStyle,
        color: active ? T.accent : T.muted,
        background: active ? T.accentSoft : 'transparent',
        borderColor: active ? 'rgba(56,189,248,0.35)' : 'transparent',
        opacity: disabled ? 0.5 : 1,
        ...style,
      }}
    >
      {children}
    </button>
  )
}

export function Bar({ value = 0, color = T.accent, height = 6, track = 'rgba(255,255,255,0.06)' }) {
  const v = Math.max(0, Math.min(100, Number(value) || 0))
  return (
    <div style={{ height, borderRadius: height, background: track, overflow: 'hidden', width: '100%' }}>
      <div
        style={{
          height: '100%',
          width: `${v}%`,
          borderRadius: height,
          background: color,
          boxShadow: `0 0 12px ${color}66`,
          transition: 'width 0.55s cubic-bezier(.4,0,.2,1)',
        }}
      />
    </div>
  )
}

export function MiniStat({ label, value, color = T.text, style }) {
  return (
    <div style={{ ...miniStat, ...style }}>
      <div style={miniLabel}>{label}</div>
      <div style={{ ...miniValue, color }}>{value}</div>
    </div>
  )
}

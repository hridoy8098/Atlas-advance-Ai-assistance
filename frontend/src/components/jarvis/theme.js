// Shared design tokens for the JARVIS-style Atlas interface.

export const T = {
  bg: '#050b14',
  bgDeep: '#03070d',
  panel: 'rgba(10,20,32,0.86)',
  panelSolid: '#0a1420',
  panelAlt: '#0c1926',
  border: '#182b3e',
  borderSoft: 'rgba(56,189,248,0.10)',
  accent: '#38bdf8',
  accent2: '#0ea5e9',
  accentSoft: 'rgba(56,189,248,0.12)',
  text: '#dbe9f5',
  muted: '#7b95ab',
  dim: '#4e667a',
  green: '#22c55e',
  amber: '#f59e0b',
  red: '#ef4444',
  font: "'Inter', system-ui, -apple-system, sans-serif",
  mono: "'JetBrains Mono', monospace",
  display: "'Orbitron', sans-serif",
  radius: 12,
}

export const panelStyle = {
  position: 'relative',
  display: 'flex',
  flexDirection: 'column',
  minHeight: 0,
  background: 'linear-gradient(180deg, rgba(12,25,38,0.94) 0%, rgba(8,17,28,0.94) 100%)',
  border: `1px solid ${T.border}`,
  borderRadius: T.radius,
  boxShadow: '0 18px 40px rgba(0,0,0,0.28), inset 0 1px 0 rgba(255,255,255,0.03)',
  overflow: 'hidden',
}

export const headerStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: 8,
  padding: '12px 13px 10px',
  borderBottom: `1px solid ${T.borderSoft}`,
  flexShrink: 0,
}

export const titleStyle = {
  fontFamily: T.font,
  fontSize: 11.5,
  fontWeight: 600,
  letterSpacing: '0.06em',
  color: T.text,
  textTransform: 'uppercase',
  flex: 1,
  whiteSpace: 'nowrap',
}

export const mutedStyle = {
  color: T.muted,
  fontSize: 11,
  fontFamily: T.font,
}

export const miniStat = {
  flex: 1,
  padding: '7px 9px',
  borderRadius: 8,
  background: 'rgba(56,189,248,0.035)',
  border: '1px solid rgba(56,189,248,0.09)',
  minWidth: 0,
}

export const miniLabel = {
  fontSize: 9,
  letterSpacing: '0.08em',
  textTransform: 'uppercase',
  color: T.dim,
  marginBottom: 4,
  whiteSpace: 'nowrap',
}

export const miniValue = {
  fontFamily: T.mono,
  fontSize: 12,
  fontWeight: 500,
  color: T.text,
  whiteSpace: 'nowrap',
  overflow: 'hidden',
  textOverflow: 'ellipsis',
}

export const iconButtonStyle = {
  width: 28,
  height: 28,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  borderRadius: 7,
  border: '1px solid transparent',
  background: 'transparent',
  color: T.muted,
  cursor: 'pointer',
  padding: 0,
  flexShrink: 0,
}

export const pillStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: 8,
  padding: '7px 12px',
  borderRadius: 999,
  border: `1px solid ${T.border}`,
  background: 'rgba(8,18,30,0.72)',
  color: T.text,
  fontFamily: T.font,
  fontSize: 12,
  lineHeight: 1,
  whiteSpace: 'nowrap',
}

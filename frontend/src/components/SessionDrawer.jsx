import React, { useState, useEffect, useRef } from 'react'
import { API } from '../config.js'

function formatRelativeTime(isoString) {
  const d = new Date(isoString)
  const diff = Date.now() - d.getTime()
  if (diff < 60000) return 'just now'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
  if (diff < 172800000) return 'yesterday'
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

function groupSessions(sessions) {
  const groups = [
    { label: 'Today', items: [] },
    { label: 'Yesterday', items: [] },
    { label: 'This week', items: [] },
    { label: 'Older', items: [] },
  ]
  const now = Date.now()
  sessions.forEach(s => {
    const diff = now - new Date(s.updated_at).getTime()
    const days = diff / 86400000
    if (days < 1) groups[0].items.push(s)
    else if (days < 2) groups[1].items.push(s)
    else if (days < 7) groups[2].items.push(s)
    else groups[3].items.push(s)
  })
  return groups.filter(g => g.items.length > 0)
}

const s = {
  overlay: {
    position: 'absolute',
    inset: 0,
    zIndex: 20,
    display: 'flex',
  },
  drawer: {
    width: '100%',
    height: '100%',
    background: 'var(--bg)',
    display: 'flex',
    flexDirection: 'column',
    transition: 'transform 0.22s cubic-bezier(0.4,0,0.2,1)',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '12px 16px',
    borderBottom: '1px solid var(--border)',
    background: 'var(--bg2)',
    flexShrink: 0,
  },
  title: {
    flex: 1,
    fontSize: '13px',
    fontWeight: '600',
    color: 'var(--text)',
  },
  closeBtn: {
    background: 'none',
    border: 'none',
    color: 'var(--text-dim)',
    cursor: 'pointer',
    fontSize: '16px',
    padding: '2px 6px',
    borderRadius: '4px',
    lineHeight: 1,
    fontFamily: 'inherit',
  },
  searchWrap: {
    padding: '10px 16px',
    borderBottom: '1px solid var(--border)',
    flexShrink: 0,
  },
  searchInput: {
    width: '100%',
    padding: '7px 10px',
    background: 'var(--bg2)',
    border: '1px solid var(--border)',
    borderRadius: '6px',
    color: 'var(--text)',
    fontSize: '12px',
    fontFamily: 'var(--font-ui)',
    outline: 'none',
    boxSizing: 'border-box',
  },
  list: {
    flex: 1,
    overflowY: 'auto',
    padding: '8px 12px',
    minHeight: 0,
  },
  groupLabel: {
    fontSize: '10px',
    fontWeight: '700',
    color: 'var(--text-dim)',
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
    padding: '10px 4px 6px',
  },
  card: {
    padding: '10px 12px',
    marginBottom: '4px',
    background: 'var(--bg2)',
    border: '1px solid var(--border)',
    borderRadius: '6px',
    cursor: 'pointer',
    transition: 'border-color 0.12s',
  },
  cardActive: {
    borderColor: 'var(--accent)',
    background: 'var(--accent-glow)',
  },
  cardRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '4px',
  },
  cardId: {
    fontSize: '11px',
    color: 'var(--accent)',
    fontFamily: 'monospace',
  },
  cardTime: {
    fontSize: '10px',
    color: 'var(--text-dim)',
  },
  cardPreview: {
    fontSize: '12px',
    color: 'var(--text)',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    marginBottom: '4px',
  },
  cardMeta: {
    fontSize: '10px',
    color: 'var(--text-dim)',
  },
  empty: {
    textAlign: 'center',
    color: 'var(--text-dim)',
    fontSize: '12px',
    marginTop: '40px',
  },
  footer: {
    padding: '12px 16px',
    borderTop: '1px solid var(--border)',
    background: 'var(--bg2)',
    flexShrink: 0,
  },
  newBtn: {
    width: '100%',
    padding: '8px',
    background: 'var(--accent-glow)',
    border: '1px solid var(--accent)',
    borderRadius: '6px',
    color: 'var(--accent)',
    fontSize: '12px',
    fontWeight: '600',
    cursor: 'pointer',
    fontFamily: 'var(--font-ui)',
  },
}

export default function SessionDrawer({ open, currentSessionId, onResume, onNewSession, onClose }) {
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const searchRef = useRef(null)

  useEffect(() => {
    if (!open) return
    setLoading(true)
    fetch(API.sessions)
      .then(r => r.json())
      .then(setSessions)
      .catch(() => {})
      .finally(() => setLoading(false))
    // Focus search after transition
    setTimeout(() => searchRef.current?.focus(), 250)
  }, [open])

  const filtered = search.trim()
    ? sessions.filter(s =>
        s.session_id.includes(search) ||
        (s.preview || '').toLowerCase().includes(search.toLowerCase())
      )
    : sessions

  const groups = groupSessions(filtered)

  const handleResume = (sid) => {
    onResume(sid)
    onClose()
  }

  const handleNew = () => {
    onNewSession()
    onClose()
  }

  return (
    <div
      style={{
        ...s.overlay,
        pointerEvents: open ? 'all' : 'none',
      }}
    >
      <div
        style={{
          ...s.drawer,
          transform: open ? 'translateX(0)' : 'translateX(-100%)',
        }}
      >
        {/* Header */}
        <div style={s.header}>
          <span style={s.title}>Session History</span>
          <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
            {sessions.length} session{sessions.length !== 1 ? 's' : ''}
          </span>
          <button style={s.closeBtn} onClick={onClose}>✕</button>
        </div>

        {/* Search */}
        <div style={s.searchWrap}>
          <input
            ref={searchRef}
            style={s.searchInput}
            placeholder="Search sessions…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>

        {/* Session list */}
        <div style={s.list}>
          {loading && (
            <div style={s.empty}>Loading…</div>
          )}
          {!loading && filtered.length === 0 && (
            <div style={s.empty}>
              {search ? 'No sessions match your search' : 'No past sessions yet'}
            </div>
          )}
          {!loading && groups.map(group => (
            <div key={group.label}>
              <div style={s.groupLabel}>{group.label}</div>
              {group.items.map(sess => {
                const isActive = sess.session_id === currentSessionId
                return (
                  <div
                    key={sess.session_id}
                    style={{ ...s.card, ...(isActive ? s.cardActive : {}) }}
                    onClick={() => handleResume(sess.session_id)}
                  >
                    <div style={s.cardRow}>
                      <span style={s.cardId}>
                        {isActive ? '▶ ' : ''}{sess.session_id.slice(0, 8)}…
                      </span>
                      <span style={s.cardTime}>{formatRelativeTime(sess.updated_at)}</span>
                    </div>
                    <div style={s.cardPreview}>
                      {sess.preview || '(no messages)'}
                    </div>
                    <div style={s.cardMeta}>
                      {sess.user_turns} message{sess.user_turns !== 1 ? 's' : ''} · {sess.assistant_turns} response{sess.assistant_turns !== 1 ? 's' : ''}
                    </div>
                  </div>
                )
              })}
            </div>
          ))}
        </div>

        {/* Footer — New Session */}
        <div style={s.footer}>
          <button style={s.newBtn} onClick={handleNew}>+ New Session</button>
        </div>
      </div>
    </div>
  )
}

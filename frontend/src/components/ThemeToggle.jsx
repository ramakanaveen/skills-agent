import React, { useState, useRef, useEffect } from 'react'
import { THEMES, applyTheme, getStoredTheme } from '../themes.js'

export default function ThemeToggle() {
  const [current, setCurrent] = useState(getStoredTheme)
  const [open, setOpen] = useState(false)
  const ref = useRef()

  useEffect(() => {
    const handler = (e) => { if (!ref.current?.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const select = (key) => {
    applyTheme(key)
    setCurrent(key)
    setOpen(false)
  }

  const theme = THEMES[current]

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '4px 10px',
          background: 'var(--bg3)',
          border: '1px solid var(--border)',
          borderRadius: '6px',
          color: 'var(--text-dim)',
          fontSize: '12px',
          cursor: 'pointer',
          fontFamily: 'var(--font-ui)',
        }}
      >
        <span>{theme.icon}</span>
        <span>{theme.label}</span>
        <span style={{ opacity: 0.5, fontSize: '10px' }}>{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div style={{
          position: 'absolute',
          top: 'calc(100% + 6px)',
          right: 0,
          background: 'var(--bg2)',
          border: '1px solid var(--border)',
          borderRadius: '8px',
          overflow: 'hidden',
          boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
          zIndex: 100,
          minWidth: '140px',
        }}>
          {Object.entries(THEMES).map(([key, t]) => (
            <div
              key={key}
              onClick={() => select(key)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '9px 14px',
                cursor: 'pointer',
                fontSize: '12px',
                color: key === current ? 'var(--accent)' : 'var(--text)',
                background: key === current ? 'var(--accent-glow)' : 'transparent',
                fontFamily: 'var(--font-ui)',
              }}
              onMouseEnter={e => { if (key !== current) e.currentTarget.style.background = 'var(--bg3)' }}
              onMouseLeave={e => { if (key !== current) e.currentTarget.style.background = 'transparent' }}
            >
              <span>{t.icon}</span>
              <span>{t.label}</span>
              {key === current && <span style={{ marginLeft: 'auto', fontSize: '10px' }}>✓</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

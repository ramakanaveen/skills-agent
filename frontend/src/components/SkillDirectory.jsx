import React, { useState, useEffect } from 'react'
import { API } from '../config.js'

const CATEGORY_META = {
  utility:     { label: 'Utility',     color: 'var(--cat-utility)',     icon: '⚙️' },
  creation:    { label: 'Creation',    color: 'var(--cat-creation)',    icon: '✏️' },
  planning:    { label: 'Planning',    color: 'var(--cat-planning)',    icon: '📋' },
  development: { label: 'Development', color: 'var(--cat-development)', icon: '💻' },
}

const SKILL_ICONS = {
  docx:          '📄',
  resume:        '👤',
  'travel-planner': '✈️',
  scripture:     '📖',
  'skill-creator': '🧠',
  'code-architect': '🏗️',
}

const s = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    flex: 1,
    minHeight: 0,
    overflow: 'hidden',
    background: 'var(--bg)',
  },
  header: {
    padding: '20px 24px 0',
    flexShrink: 0,
  },
  titleRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: '6px',
  },
  title: {
    fontSize: '22px',
    fontWeight: '700',
    color: 'var(--text)',
    letterSpacing: '-0.3px',
  },
  subtitle: {
    fontSize: '12px',
    color: 'var(--text-dim)',
    marginBottom: '16px',
  },
  deployBtn: {
    padding: '8px 16px',
    background: 'linear-gradient(135deg, var(--accent), var(--accent2))',
    border: 'none',
    borderRadius: '8px',
    color: '#fff',
    fontSize: '12px',
    fontWeight: '600',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    boxShadow: '0 0 16px var(--accent-glow)',
  },
  searchRow: {
    display: 'flex',
    gap: '10px',
    marginBottom: '14px',
    alignItems: 'center',
  },
  searchInput: {
    flex: 1,
    padding: '8px 12px 8px 32px',
    background: 'var(--bg3)',
    border: '1px solid var(--border2)',
    borderRadius: '8px',
    color: 'var(--text)',
    fontSize: '12px',
    fontFamily: 'var(--font-ui)',
    outline: 'none',
    position: 'relative',
  },
  searchWrap: {
    flex: 1,
    position: 'relative',
  },
  searchIcon: {
    position: 'absolute',
    left: '10px',
    top: '50%',
    transform: 'translateY(-50%)',
    color: 'var(--text-dim)',
    fontSize: '12px',
    pointerEvents: 'none',
  },
  filterRow: {
    display: 'flex',
    gap: '6px',
    marginBottom: '16px',
  },
  filterPill: {
    padding: '5px 12px',
    borderRadius: '20px',
    fontSize: '11px',
    fontWeight: '600',
    cursor: 'pointer',
    border: '1px solid var(--border2)',
    background: 'transparent',
    color: 'var(--text-dim)',
    letterSpacing: '0.02em',
    transition: 'all 0.15s',
  },
  filterPillActive: {
    background: 'var(--accent)',
    border: '1px solid var(--accent)',
    color: '#fff',
    boxShadow: '0 0 12px var(--accent-glow)',
  },
  body: {
    display: 'flex',
    flex: 1,
    overflow: 'hidden',
    minHeight: 0,
    gap: '0',
  },
  grid: {
    flex: 1,
    overflowY: 'auto',
    padding: '0 16px 16px 24px',
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
    gap: '12px',
    alignContent: 'start',
  },
  card: {
    background: 'var(--bg2)',
    border: '1px solid var(--border)',
    borderRadius: '12px',
    padding: '16px',
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
    cursor: 'pointer',
    transition: 'border-color 0.2s, box-shadow 0.2s',
    position: 'relative',
    overflow: 'hidden',
  },
  cardHover: {
    borderColor: 'var(--accent)',
    boxShadow: '0 0 20px var(--accent-glow)',
  },
  cardTop: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  iconBox: {
    width: '36px',
    height: '36px',
    borderRadius: '8px',
    background: 'var(--bg3)',
    border: '1px solid var(--border2)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '18px',
  },
  statusBadge: {
    padding: '3px 8px',
    borderRadius: '20px',
    fontSize: '10px',
    fontWeight: '700',
    letterSpacing: '0.05em',
    textTransform: 'uppercase',
  },
  cardName: {
    fontSize: '13px',
    fontWeight: '700',
    color: 'var(--text)',
  },
  cardDesc: {
    fontSize: '11px',
    color: 'var(--text-dim)',
    lineHeight: '1.5',
    flex: 1,
    display: '-webkit-box',
    WebkitLineClamp: 3,
    WebkitBoxOrient: 'vertical',
    overflow: 'hidden',
  },
  cardFooter: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: '8px',
    borderTop: '1px solid var(--border)',
  },
  catBadge: {
    padding: '2px 8px',
    borderRadius: '4px',
    fontSize: '10px',
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  useBtn: {
    fontSize: '11px',
    color: 'var(--accent)',
    fontWeight: '600',
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '3px',
    padding: 0,
    fontFamily: 'var(--font-ui)',
  },
  visBadge: {
    position: 'absolute',
    top: '10px',
    right: '10px',
    fontSize: '9px',
    padding: '2px 6px',
    borderRadius: '3px',
  },
  // Feed panel
  feed: {
    width: '220px',
    flexShrink: 0,
    borderLeft: '1px solid var(--border)',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  },
  feedHeader: {
    padding: '16px 16px 10px',
    fontSize: '11px',
    fontWeight: '700',
    color: 'var(--text-dim)',
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    borderBottom: '1px solid var(--border)',
    flexShrink: 0,
  },
  feedList: {
    flex: 1,
    overflowY: 'auto',
    padding: '10px 12px',
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  feedItem: {
    padding: '8px 10px',
    background: 'var(--bg2)',
    borderRadius: '8px',
    border: '1px solid var(--border)',
    fontSize: '11px',
  },
  feedDot: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    background: 'var(--active)',
    display: 'inline-block',
    marginRight: '6px',
    boxShadow: '0 0 6px var(--active-glow)',
  },
  feedSkill: {
    fontWeight: '600',
    color: 'var(--text)',
  },
  feedAction: {
    color: 'var(--text-dim)',
    marginTop: '2px',
  },
  feedTime: {
    color: 'var(--text-dim)',
    fontSize: '10px',
    marginTop: '3px',
  },
  empty: {
    color: 'var(--text-dim)',
    fontSize: '12px',
    textAlign: 'center',
    marginTop: '40px',
    gridColumn: '1 / -1',
  },
}

function getStatus(skillName, stats) {
  const count = stats[skillName] || 0
  if (count >= 3) return 'active'
  if (count >= 1) return 'ready'
  return 'ready'
}

const STATUS_STYLE = {
  active:   { label: 'ACTIVE',   bg: 'var(--active-bg)',   color: 'var(--active)',   glow: '0 0 8px var(--active-glow)' },
  ready:    { label: 'READY',    bg: 'var(--ready-bg)',    color: 'var(--ready)',    glow: 'none' },
  learning: { label: 'LEARNING', bg: 'var(--learning-bg)', color: 'var(--learning)', glow: 'none' },
}

function SkillCard({ skill, stats, onUse }) {
  const [hovered, setHovered] = useState(false)
  const status = getStatus(skill.name, stats)
  const st = STATUS_STYLE[status]
  const cat = CATEGORY_META[skill.category] || CATEGORY_META.utility
  const icon = SKILL_ICONS[skill.name] || cat.icon
  const isPrivate = skill.visibility === 'private'

  return (
    <div
      style={{ ...s.card, ...(hovered ? s.cardHover : {}) }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {/* Visibility watermark */}
      {isPrivate && (
        <span style={{ ...s.visBadge, color: 'var(--yellow)', background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.2)' }}>
          🔒 private
        </span>
      )}
      <div style={s.cardTop}>
        <div style={s.iconBox}>{icon}</div>
        <span style={{ ...s.statusBadge, background: st.bg, color: st.color, boxShadow: st.glow }}>
          {st.label}
        </span>
      </div>
      <div style={s.cardName}>{skill.name}</div>
      <div style={s.cardDesc}>{skill.description}</div>
      <div style={s.cardFooter}>
        <span style={{ ...s.catBadge, background: `${cat.color}18`, color: cat.color }}>
          {cat.label}
        </span>
        <button style={s.useBtn} onClick={() => onUse(skill)}>
          USE SKILL →
        </button>
      </div>
    </div>
  )
}

function DeploymentFeed({ skills, stats }) {
  // Build feed from skills sorted by usage
  const items = [...skills]
    .filter(sk => (stats[sk.name] || 0) > 0)
    .sort((a, b) => (stats[b.name] || 0) - (stats[a.name] || 0))
    .slice(0, 8)
    .map(sk => ({
      skill: sk.name,
      action: `used ${stats[sk.name]} time${stats[sk.name] !== 1 ? 's' : ''}`,
    }))

  return (
    <div style={s.feed}>
      <div style={s.feedHeader}>Deployment Feed</div>
      <div style={s.feedList}>
        {items.length === 0 && (
          <div style={{ ...s.feedTime, textAlign: 'center', marginTop: '20px' }}>
            No activity yet
          </div>
        )}
        {items.map((item, i) => (
          <div key={i} style={s.feedItem}>
            <span style={s.feedDot} />
            <span style={s.feedSkill}>{item.skill}</span>
            <div style={s.feedAction}>{item.action}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

const FILTERS = ['all', 'utility', 'creation', 'planning', 'development']

export default function SkillDirectory({ skills, onUseSkill }) {
  const [filter, setFilter] = useState('all')
  const [search, setSearch] = useState('')
  const [stats, setStats] = useState({})

  useEffect(() => {
    fetch(API.skillStats).then(r => r.json()).then(setStats).catch(() => {})
  }, [skills])

  const filtered = skills.filter(sk => {
    const matchCat = filter === 'all' || sk.category === filter
    const matchSearch = !search ||
      sk.name.toLowerCase().includes(search.toLowerCase()) ||
      sk.description.toLowerCase().includes(search.toLowerCase())
    return matchCat && matchSearch
  })

  return (
    <div style={s.container}>
      <div style={s.header}>
        <div style={s.titleRow}>
          <h1 style={s.title}>Skill Directory</h1>
          <button style={s.deployBtn} onClick={() => onUseSkill(null)}>
            + Deploy New Skill
          </button>
        </div>
        <div style={s.subtitle}>
          Manage and deploy autonomous intelligence capabilities · {skills.length} skill{skills.length !== 1 ? 's' : ''} loaded
        </div>
        <div style={s.searchRow}>
          <div style={s.searchWrap}>
            <span style={s.searchIcon}>🔍</span>
            <input
              style={s.searchInput}
              placeholder="Search skills..."
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
        </div>
        <div style={s.filterRow}>
          {FILTERS.map(f => (
            <button
              key={f}
              style={{ ...s.filterPill, ...(filter === f ? s.filterPillActive : {}) }}
              onClick={() => setFilter(f)}
            >
              {f === 'all' ? 'ALL SKILLS' : f.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      <div style={s.body}>
        <div style={s.grid}>
          {filtered.length === 0 && (
            <div style={s.empty}>No skills match your filter</div>
          )}
          {filtered.map(skill => (
            <SkillCard
              key={skill.name}
              skill={skill}
              stats={stats}
              onUse={onUseSkill}
            />
          ))}
        </div>
        <DeploymentFeed skills={skills} stats={stats} />
      </div>
    </div>
  )
}

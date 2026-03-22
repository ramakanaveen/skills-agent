import React, { useState, useEffect, useRef } from 'react'
import ChatView from './components/ChatView.jsx'
import ReplyBar from './components/ReplyBar.jsx'
import SkillDirectory from './components/SkillDirectory.jsx'
import OutputPanel from './components/OutputPanel.jsx'
import ThemeToggle from './components/ThemeToggle.jsx'
import { API, UI } from './config.js'

const s = {
  app: {
    display: 'flex',
    flexDirection: 'column',
    height: '100vh',
    overflow: 'hidden',
    background: 'var(--bg)',
    fontFamily: 'var(--font-ui)',
  },
  header: {
    padding: '0 24px',
    height: '48px',
    borderBottom: '1px solid var(--border)',
    background: 'var(--bg2)',
    display: 'flex',
    alignItems: 'center',
    gap: '24px',
    flexShrink: 0,
  },
  logo: {
    fontSize: '14px',
    fontWeight: '700',
    color: 'var(--text)',
    letterSpacing: '-0.2px',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  logoAccent: {
    color: 'var(--accent)',
  },
  navItem: {
    fontSize: '12px',
    color: 'var(--text-dim)',
    cursor: 'pointer',
    padding: '4px 8px',
    borderRadius: '6px',
  },
  navItemActive: {
    color: 'var(--accent)',
    background: 'var(--accent-glow)',
  },
  statusPill: {
    marginLeft: 'auto',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '4px 10px',
    background: 'rgba(34,197,94,0.08)',
    border: '1px solid rgba(34,197,94,0.2)',
    borderRadius: '20px',
    fontSize: '11px',
    color: 'var(--active)',
    fontWeight: '600',
  },
  statusDot: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    background: 'var(--active)',
    boxShadow: '0 0 6px var(--active-glow)',
  },
  versionBadge: {
    fontSize: '10px',
    padding: '2px 6px',
    background: 'var(--bg3)',
    border: '1px solid var(--border2)',
    borderRadius: '4px',
    color: 'var(--text-dim)',
    marginLeft: '4px',
  },
  body: {
    display: 'flex',
    flex: 1,
    overflow: 'hidden',
    minHeight: 0,
  },
  left: {
    display: 'flex',
    flexDirection: 'column',
    borderRight: '1px solid var(--border)',
    overflow: 'hidden',
    minHeight: 0,
    height: '100%',
  },
  right: {
    display: 'flex',
    flexDirection: 'column',
    flex: 1,
    overflow: 'hidden',
    minHeight: 0,
  },
  // Right panel tabs
  rightTabs: {
    display: 'flex',
    borderBottom: '1px solid var(--border)',
    background: 'var(--bg2)',
    padding: '0 16px',
    flexShrink: 0,
  },
  rightTab: {
    padding: '12px 14px',
    fontSize: '12px',
    fontWeight: '500',
    color: 'var(--text-dim)',
    cursor: 'pointer',
    borderBottom: '2px solid transparent',
    userSelect: 'none',
  },
  rightTabActive: {
    color: 'var(--accent)',
    borderBottom: '2px solid var(--accent)',
  },
  rightPanel: {
    flex: 1,
    overflow: 'hidden',
    minHeight: 0,
    display: 'flex',
    flexDirection: 'column',
  },
  newSessionBtn: {
    marginLeft: 'auto',
    marginRight: '12px',
    padding: '3px 10px',
    background: 'var(--bg3)',
    border: '1px solid var(--border2)',
    borderRadius: '6px',
    color: 'var(--text-dim)',
    fontSize: '11px',
    cursor: 'pointer',
    fontFamily: 'var(--font-ui)',
  },
}

const NAV = ['Workspace', 'Skill Directory', 'Agent Logs', 'Artifacts']

export default function App2() {
  const [activeNav, setActiveNav] = useState('Workspace')
  const [rightTab, setRightTab] = useState(0)
  const [turns, setTurns] = useState([])
  const [sessionId, setSessionId] = useState(null)
  const [outputFiles, setOutputFiles] = useState([])
  const [skills, setSkills] = useState([])
  const [readSkills, setReadSkills] = useState(new Set())
  const [transcript, setTranscript] = useState([])
  const [uploadedFiles, setUploadedFiles] = useState([])
  const [running, setRunning] = useState(false)
  const [previewReady, setPreviewReady] = useState(0)
  const [leftWidth, setLeftWidth] = useState(() => {
    const saved = localStorage.getItem('skills-agent-left-width')
    return saved ? parseFloat(saved) : 50
  })
  const isDragging = useRef(false)
  const dragStartX = useRef(0)
  const dragStartWidth = useRef(0)
  const leftWidthRef = useRef(leftWidth)
  const liveTurnRef = useRef(null)

  useEffect(() => { leftWidthRef.current = leftWidth }, [leftWidth])

  useEffect(() => {
    const onMove = (e) => {
      if (!isDragging.current) return
      const container = document.getElementById('skills-agent-body')
      if (!container) return
      const totalWidth = container.offsetWidth
      const delta = e.clientX - dragStartX.current
      const newWidth = Math.min(80, Math.max(20,
        dragStartWidth.current + (delta / totalWidth) * 100
      ))
      setLeftWidth(newWidth)
    }
    const onUp = () => {
      if (isDragging.current) {
        isDragging.current = false
        localStorage.setItem('skills-agent-left-width', String(leftWidthRef.current))
      }
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    return () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
  }, [])

  useEffect(() => {
    fetch(API.skills).then(r => r.json()).then(setSkills).catch(() => {})
  }, [])

  const newSession = () => {
    setTurns([])
    setSessionId(null)
    setOutputFiles([])
    setTranscript([])
    setReadSkills(new Set())
  }

  const reconstructTurns = (records) => {
    const result = []
    let pendingEvents = []
    for (const r of records) {
      if (r.role === 'user') {
        result.push({ id: Math.random(), role: 'user', text: r.content })
        pendingEvents = []
      } else if (r.role === 'tool') {
        pendingEvents.push({ id: Math.random(), stage: 'tool_result', tool: r.tool_name, result: r.tool_result?.slice(0, UI.sessionToolResultChars) || '', full_length: r.tool_result?.length || 0 })
      } else if (r.role === 'assistant') {
        result.push({ id: Math.random(), role: 'agent', text: r.content, events: pendingEvents, done: true })
        pendingEvents = []
      }
    }
    return result
  }

  const loadSession = async (sid) => {
    try {
      const [transcriptData, files] = await Promise.all([
        fetch(API.session(sid)).then(r => r.json()),
        fetch(API.outputs(sid)).then(r => r.json()).catch(() => []),
      ])
      setSessionId(sid)
      setTranscript(transcriptData)
      setTurns(reconstructTurns(transcriptData))
      setOutputFiles(files)
      setReadSkills(new Set())
    } catch (e) { console.error(e) }
  }

  const handleSend = async (task) => {
    if (!task.trim() || running) return
    setRunning(true)
    setActiveNav('Workspace')

    const userTurnId = Date.now()
    const agentTurnId = Date.now() + 1
    setTurns(prev => [...prev, { id: userTurnId, role: 'user', text: task }])
    const agentTurn = { id: agentTurnId, role: 'agent', text: '', events: [], done: false }
    liveTurnRef.current = { ...agentTurn }
    setTurns(prev => [...prev, agentTurn])

    const newReadSkills = new Set(readSkills)
    const updateLive = (updater) => {
      liveTurnRef.current = updater(liveTurnRef.current)
      const snap = { ...liveTurnRef.current }
      setTurns(prev => prev.map(t => t.id === agentTurnId ? snap : t))
    }

    try {
      const res = await fetch(API.run, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task, session_id: sessionId, uploaded_files: uploadedFiles.map(f => ({ name: f.name })) }),
      })
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n\n')
        buffer = lines.pop()
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const evt = JSON.parse(line.slice(6))
            if (evt.stage === 'start') setSessionId(evt.session_id)
            if (evt.stage === 'thinking') updateLive(t => ({ ...t, text: t.text + evt.text }))
            if (['tool_call', 'tool_result', 'warning', 'error'].includes(evt.stage)) {
              updateLive(t => ({ ...t, events: [...t.events, { ...evt, id: Date.now() + Math.random() }] }))
            }
            if (evt.stage === 'tool_result' && evt.tool === 'read_file') {
              skills.forEach(sk => { if (evt.result?.includes(sk.name)) newReadSkills.add(sk.name) })
              setReadSkills(new Set(newReadSkills))
            }
            if (evt.stage === 'complete') {
              setOutputFiles(evt.output_files || [])
              setPreviewReady(n => n + 1)
              updateLive(t => ({ ...t, done: true }))
              fetch(API.skills).then(r => r.json()).then(setSkills)
              if (evt.session_id) fetch(API.session(evt.session_id))
                .then(r => r.json()).then(setTranscript).catch(() => {})
            }
          } catch (e) { /* ignore */ }
        }
      }
    } catch (e) {
      updateLive(t => ({ ...t, events: [...t.events, { stage: 'error', text: String(e), id: Date.now() }], done: true }))
    }
    setRunning(false)
  }

  // "USE SKILL →" handler — pre-fills chat
  // Nav → right tab mapping
  const NAV_TAB = {
    'Workspace':       null,   // no right tab change, just focus chat
    'Skill Directory': 0,
    'Artifacts':       1,
    'Agent Logs':      3,
  }

  const handleNav = (nav) => {
    setActiveNav(nav)
    const tab = NAV_TAB[nav]
    if (tab !== null && tab !== undefined) setRightTab(tab)
  }

  const handleUseSkill = (skill) => {
    setActiveNav('Workspace')
    if (!skill) {
      // Deploy New Skill button
      handleSend('Create a new skill for me. Ask me what it should do.')
    } else {
      handleSend(`Use the ${skill.name} skill to help me.`)
    }
  }

  const rightTabs = [
    { label: 'Skill Directory' },
    { label: `Outputs${outputFiles.length ? ` (${outputFiles.length})` : ''}` },
    { label: 'Sessions' },
    { label: `Transcript${transcript.length ? ` (${transcript.length})` : ''}` },
  ]

  return (
    <div style={s.app}>
      <div style={s.header}>
        <div style={s.logo}>
          <span>⚡</span>
          <span>Skills<span style={s.logoAccent}>Agent</span></span>
          <span style={s.versionBadge}>2.0</span>
        </div>
        {NAV.map(n => (
          <div
            key={n}
            style={{ ...s.navItem, ...(activeNav === n ? s.navItemActive : {}) }}
            onClick={() => handleNav(n)}
          >
            {n}
          </div>
        ))}
        <div style={s.statusPill}>
          <span style={s.statusDot} />
          SYSTEM CORE: STABLE
        </div>
        <ThemeToggle />
      </div>

      <div id="skills-agent-body" style={s.body}>
        {/* Left — chat */}
        <div style={{ ...s.left, width: `${leftWidth}%` }}>
          <div style={{ display: 'flex', alignItems: 'center', padding: '8px 16px', borderBottom: '1px solid var(--border)', background: 'var(--bg2)', flexShrink: 0 }}>
            <span style={{ fontSize: '12px', color: 'var(--text-dim)' }}>
              {sessionId ? `Session ${sessionId.slice(0, 8)}…` : 'New session'}
            </span>
            {turns.length > 0 && (
              <button style={s.newSessionBtn} onClick={newSession}>+ New</button>
            )}
          </div>
          <ChatView turns={turns} running={running} sessionId={sessionId} />
          <ReplyBar
            onSend={handleSend}
            running={running}
            uploadedFiles={uploadedFiles}
            setUploadedFiles={setUploadedFiles}
            hasHistory={turns.length > 0}
          />
        </div>

        {/* Draggable divider */}
        <div
          style={{
            width: '4px',
            background: 'var(--border)',
            cursor: 'col-resize',
            flexShrink: 0,
            transition: 'background 0.15s',
          }}
          onMouseEnter={e => e.currentTarget.style.background = 'var(--accent)'}
          onMouseLeave={e => { if (!isDragging.current) e.currentTarget.style.background = 'var(--border)' }}
          onMouseDown={e => {
            isDragging.current = true
            dragStartX.current = e.clientX
            dragStartWidth.current = leftWidth
            e.preventDefault()
          }}
        />

        {/* Right — skill directory + outputs */}
        <div style={s.right}>
          <div style={s.rightTabs}>
            {rightTabs.map((t, i) => (
              <div
                key={t.label}
                style={{ ...s.rightTab, ...(rightTab === i ? s.rightTabActive : {}) }}
                onClick={() => setRightTab(i)}
              >
                {t.label}
              </div>
            ))}
          </div>
          <div style={s.rightPanel}>
            {rightTab === 0 && (
              <SkillDirectory skills={skills} onUseSkill={handleUseSkill} />
            )}
            {rightTab !== 0 && (
              <OutputPanel
                outputFiles={outputFiles}
                sessionId={sessionId}
                transcript={transcript}
                skills={skills}
                readSkills={readSkills}
                uploadedFiles={uploadedFiles}
                onResumeSession={loadSession}
                forcePreview={previewReady}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

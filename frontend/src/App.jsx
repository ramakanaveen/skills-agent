import React, { useState, useEffect, useRef } from 'react'
import ChatView from './components/ChatView.jsx'
import ReplyBar from './components/ReplyBar.jsx'
import OutputPanel from './components/OutputPanel.jsx'

const styles = {
  app: {
    display: 'flex',
    flexDirection: 'column',
    minHeight: '100vh',
    background: 'var(--bg)',
  },
  header: {
    padding: '10px 20px',
    borderBottom: '1px solid var(--border)',
    background: 'var(--bg2)',
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    flexShrink: 0,
  },
  title: {
    fontSize: '15px',
    color: 'var(--accent)',
    fontWeight: 'bold',
  },
  subtitle: {
    fontSize: '12px',
    color: 'var(--text-dim)',
  },
  newBtn: {
    marginLeft: 'auto',
    padding: '4px 12px',
    background: 'var(--bg3)',
    border: '1px solid var(--border)',
    borderRadius: '4px',
    color: 'var(--text-dim)',
    fontSize: '11px',
    cursor: 'pointer',
  },
  body: {
    display: 'flex',
    flex: 1,
    overflow: 'hidden',
    height: 'calc(100vh - 41px)',
  },
  left: {
    display: 'flex',
    flexDirection: 'column',
    width: '50%',
    borderRight: '1px solid var(--border)',
    overflow: 'hidden',
  },
  right: {
    display: 'flex',
    flexDirection: 'column',
    width: '50%',
    overflow: 'hidden',
  },
}

export default function App() {
  const [turns, setTurns] = useState([])       // { id, role, text, events, done }
  const [sessionId, setSessionId] = useState(null)
  const [outputFiles, setOutputFiles] = useState([])
  const [skills, setSkills] = useState([])
  const [readSkills, setReadSkills] = useState(new Set())
  const [transcript, setTranscript] = useState([])
  const [uploadedFiles, setUploadedFiles] = useState([])
  const [running, setRunning] = useState(false)

  // Use a ref to mutate the live agent turn without stale closures
  const liveTurnRef = useRef(null)

  useEffect(() => {
    fetch('/api/skills').then(r => r.json()).then(setSkills).catch(() => {})
  }, [])

  const newSession = () => {
    setTurns([])
    setSessionId(null)
    setOutputFiles([])
    setTranscript([])
    setReadSkills(new Set())
  }

  // Reconstruct chat turns from a saved transcript
  const reconstructTurns = (records) => {
    const result = []
    let pendingEvents = []
    for (const r of records) {
      if (r.role === 'user') {
        result.push({ id: Math.random(), role: 'user', text: r.content })
        pendingEvents = []
      } else if (r.role === 'tool') {
        pendingEvents.push({
          id: Math.random(),
          stage: 'tool_result',
          tool: r.tool_name,
          result: r.tool_result?.slice(0, 500) || '',
          full_length: r.tool_result?.length || 0,
        })
      } else if (r.role === 'assistant') {
        result.push({
          id: Math.random(),
          role: 'agent',
          text: r.content,
          events: pendingEvents,
          done: true,
        })
        pendingEvents = []
      }
    }
    return result
  }

  const loadSession = async (sid) => {
    try {
      const [transcriptData, files] = await Promise.all([
        fetch(`/api/session/${sid}`).then(r => r.json()),
        fetch(`/api/outputs/${sid}`).then(r => r.json()).catch(() => []),
      ])
      setSessionId(sid)
      setTranscript(transcriptData)
      setTurns(reconstructTurns(transcriptData))
      setOutputFiles(files)
      setReadSkills(new Set())
    } catch (e) {
      console.error('Failed to load session', e)
    }
  }

  const handleSend = async (task) => {
    if (!task.trim() || running) return
    setRunning(true)

    const userTurnId = Date.now()
    const agentTurnId = Date.now() + 1

    // Add user turn immediately
    setTurns(prev => [...prev, { id: userTurnId, role: 'user', text: task }])

    // Add empty agent turn (will fill as we stream)
    const agentTurn = { id: agentTurnId, role: 'agent', text: '', events: [], done: false }
    liveTurnRef.current = { ...agentTurn }
    setTurns(prev => [...prev, agentTurn])

    const newReadSkills = new Set(readSkills)

    const updateLiveTurn = (updater) => {
      liveTurnRef.current = updater(liveTurnRef.current)
      const snapshot = { ...liveTurnRef.current }
      setTurns(prev => prev.map(t => t.id === agentTurnId ? snapshot : t))
    }

    try {
      const res = await fetch('/api/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task,
          session_id: sessionId,
          uploaded_files: uploadedFiles.map(f => ({ name: f.name })),
        }),
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

            if (evt.stage === 'start') {
              setSessionId(evt.session_id)
            }

            if (evt.stage === 'thinking') {
              updateLiveTurn(t => ({ ...t, text: t.text + evt.text }))
            }

            if (evt.stage === 'tool_call' || evt.stage === 'tool_result' ||
                evt.stage === 'warning' || evt.stage === 'error') {
              updateLiveTurn(t => ({
                ...t,
                events: [...t.events, { ...evt, id: Date.now() + Math.random() }]
              }))
            }

            if (evt.stage === 'tool_result' && evt.tool === 'read_file') {
              skills.forEach(s => {
                if (evt.result && evt.result.includes(s.name)) newReadSkills.add(s.name)
              })
              setReadSkills(new Set(newReadSkills))
            }

            if (evt.stage === 'complete') {
              setOutputFiles(evt.output_files || [])
              updateLiveTurn(t => ({ ...t, done: true }))
              fetch('/api/skills').then(r => r.json()).then(setSkills)
              if (evt.session_id) {
                fetch(`/api/session/${evt.session_id}`)
                  .then(r => r.json()).then(setTranscript).catch(() => {})
              }
            }
          } catch (e) { /* ignore parse errors */ }
        }
      }
    } catch (e) {
      updateLiveTurn(t => ({
        ...t,
        events: [...t.events, { stage: 'error', text: String(e), id: Date.now() }],
        done: true,
      }))
    }

    setRunning(false)
  }

  return (
    <div style={styles.app}>
      <div style={styles.header}>
        <span style={styles.title}>⚡ Skills Agent</span>
        <span style={styles.subtitle}>
          {skills.length} skill{skills.length !== 1 ? 's' : ''} loaded
          {sessionId && ` · session ${sessionId.slice(0, 8)}`}
        </span>
        {turns.length > 0 && (
          <button style={styles.newBtn} onClick={newSession}>+ New session</button>
        )}
      </div>
      <div style={styles.body}>
        <div style={styles.left}>
          <ChatView turns={turns} running={running} />
          <ReplyBar
            onSend={handleSend}
            running={running}
            uploadedFiles={uploadedFiles}
            setUploadedFiles={setUploadedFiles}
            hasHistory={turns.length > 0}
          />
        </div>
        <div style={styles.right}>
          <OutputPanel
            outputFiles={outputFiles}
            sessionId={sessionId}
            transcript={transcript}
            skills={skills}
            readSkills={readSkills}
            uploadedFiles={uploadedFiles}
            onResumeSession={loadSession}
          />
        </div>
      </div>
    </div>
  )
}

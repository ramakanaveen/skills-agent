import React, { useState, useEffect } from 'react'
import ContextInspector from './ContextInspector.jsx'
import { API, UI } from '../config.js'

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    flex: 1,
    overflow: 'hidden',
  },
  tabs: {
    display: 'flex',
    borderBottom: '1px solid var(--border)',
    background: 'var(--bg2)',
    overflowX: 'auto',
  },
  tab: {
    padding: '8px 14px',
    cursor: 'pointer',
    fontSize: '12px',
    color: 'var(--text-dim)',
    borderBottom: '2px solid transparent',
    userSelect: 'none',
    whiteSpace: 'nowrap',
  },
  tabActive: {
    color: 'var(--accent)',
    borderBottom: '2px solid var(--accent)',
  },
  panel: {
    flex: 1,
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
  },
  fileList: {
    flex: 1,
    overflowY: 'auto',
    padding: '12px 16px',
  },
  fileRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '8px 10px',
    background: 'var(--bg2)',
    border: '1px solid var(--border)',
  },
  filename: {
    fontSize: '13px',
    color: 'var(--accent)',
    wordBreak: 'break-all',
  },
  downloadBtn: {
    padding: '4px 10px',
    background: 'var(--bg3)',
    border: '1px solid var(--border)',
    borderRadius: '3px',
    color: 'var(--text)',
    fontSize: '11px',
    cursor: 'pointer',
    flexShrink: 0,
    marginLeft: '8px',
  },
  previewToggle: {
    fontSize: '11px',
    color: 'var(--text-dim)',
    cursor: 'pointer',
    marginLeft: '8px',
    flexShrink: 0,
  },
  preview: {
    padding: '8px 10px',
    background: 'var(--bg)',
    borderTop: '1px solid var(--border)',
    fontSize: '11px',
    color: 'var(--text)',
    whiteSpace: 'pre-wrap',
    maxHeight: '200px',
    overflowY: 'auto',
    fontFamily: 'var(--font)',
  },
  fileCard: {
    marginBottom: '8px',
    border: '1px solid var(--border)',
    borderRadius: '4px',
    overflow: 'hidden',
    background: 'var(--bg2)',
  },
  empty: {
    color: 'var(--text-dim)',
    fontSize: '12px',
    textAlign: 'center',
    marginTop: '40px',
  },
  transcriptEntry: {
    marginBottom: '6px',
    padding: '8px 10px',
    background: 'var(--bg2)',
    border: '1px solid var(--border)',
    borderRadius: '4px',
    fontSize: '11px',
  },
  transcriptRole: { fontWeight: 'bold', marginRight: '8px' },
  transcriptTs: { color: 'var(--text-dim)', fontSize: '10px', marginRight: '8px' },
  transcriptTool: { color: 'var(--yellow)', fontSize: '10px', marginRight: '8px' },
  transcriptContent: {
    color: 'var(--text)',
    marginTop: '3px',
    whiteSpace: 'pre-wrap',
    maxHeight: '80px',
    overflowY: 'auto',
    wordBreak: 'break-word',
  },
  downloadAllBtn: {
    padding: '5px 12px',
    background: 'var(--bg3)',
    border: '1px solid var(--border)',
    borderRadius: '3px',
    color: 'var(--text)',
    fontSize: '11px',
    cursor: 'pointer',
    marginLeft: 'auto',
  },
  transcriptPanel: { flex: 1, overflowY: 'auto', padding: '12px 16px' },
  transcriptHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '10px',
  },
  // Sessions tab
  sessionsPanel: { flex: 1, overflowY: 'auto', padding: '12px 16px' },
  sessionCard: {
    padding: '10px 12px',
    marginBottom: '8px',
    background: 'var(--bg2)',
    border: '1px solid var(--border)',
    borderRadius: '4px',
    cursor: 'pointer',
    transition: 'border-color 0.15s',
  },
  sessionCardActive: {
    borderColor: 'var(--accent)',
  },
  sessionHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '4px',
  },
  sessionId: { fontSize: '11px', color: 'var(--accent)', fontFamily: 'monospace' },
  sessionTime: { fontSize: '10px', color: 'var(--text-dim)' },
  sessionPreview: {
    fontSize: '12px',
    color: 'var(--text)',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  sessionMeta: { fontSize: '10px', color: 'var(--text-dim)', marginTop: '4px' },
  refreshBtn: {
    padding: '4px 10px',
    background: 'var(--bg3)',
    border: '1px solid var(--border)',
    borderRadius: '3px',
    color: 'var(--text-dim)',
    fontSize: '11px',
    cursor: 'pointer',
  },
  sessionsHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '10px',
  },
}

const PREVIEWABLE = ['.md', '.txt', '.py', '.js', '.ts', '.jsx', '.tsx', '.json', '.yaml', '.yml', '.html', '.css']

function FileCard({ filename, sessionId }) {
  const [expanded, setExpanded] = useState(false)
  const [preview, setPreview] = useState(null)
  const [loading, setLoading] = useState(false)

  const ext = '.' + filename.split('.').pop()
  const canPreview = PREVIEWABLE.includes(ext)
  const downloadUrl = sessionId ? `/api/download/${sessionId}/${filename}` : `/api/download/${filename}`

  const loadPreview = async () => {
    if (preview !== null) { setExpanded(e => !e); return }
    setLoading(true)
    try {
      const res = await fetch(downloadUrl)
      const text = await res.text()
      setPreview(text.slice(0, UI.filePreviewChars))
      setExpanded(true)
    } catch {
      setPreview('(could not load preview)')
      setExpanded(true)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={styles.fileCard}>
      <div style={styles.fileRow}>
        <span style={styles.filename}>{filename}</span>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          {canPreview && (
            <span style={styles.previewToggle} onClick={loadPreview}>
              {loading ? '…' : expanded ? '▲ hide' : '▼ preview'}
            </span>
          )}
          <a href={downloadUrl} download={filename}>
            <button style={styles.downloadBtn}>⬇ Download</button>
          </a>
        </div>
      </div>
      {expanded && preview !== null && (
        <div style={styles.preview}>{preview}</div>
      )}
    </div>
  )
}

const ROLE_COLORS = { user: 'var(--accent)', assistant: 'var(--green)', tool: 'var(--yellow)' }

function TranscriptEntry({ record }) {
  return (
    <div style={styles.transcriptEntry}>
      <div>
        <span style={{ ...styles.transcriptRole, color: ROLE_COLORS[record.role] || 'var(--text)' }}>
          {record.role}
        </span>
        <span style={styles.transcriptTs}>{record.ts?.slice(11, 19)}</span>
        {record.tool_name && <span style={styles.transcriptTool}>[{record.tool_name}]</span>}
      </div>
      <div style={styles.transcriptContent}>
        {record.content?.slice(0, UI.transcriptEntryChars) || '(no content)'}
      </div>
    </div>
  )
}

function formatRelativeTime(isoString) {
  const d = new Date(isoString)
  const diff = Date.now() - d.getTime()
  if (diff < 60000) return 'just now'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
  return d.toLocaleDateString()
}

function SessionsPanel({ currentSessionId, onResume }) {
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const res = await fetch(API.sessions)
      setSessions(await res.json())
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [currentSessionId])

  return (
    <div style={styles.sessionsPanel}>
      <div style={styles.sessionsHeader}>
        <span style={{ fontSize: '12px', color: 'var(--text-dim)' }}>
          {sessions.length} session{sessions.length !== 1 ? 's' : ''}
        </span>
        <button style={styles.refreshBtn} onClick={load} disabled={loading}>
          {loading ? '…' : '↺ Refresh'}
        </button>
      </div>
      {sessions.length === 0 && !loading && (
        <div style={styles.empty}>No past sessions yet</div>
      )}
      {sessions.map(s => {
        const isActive = s.session_id === currentSessionId
        return (
          <div
            key={s.session_id}
            style={{ ...styles.sessionCard, ...(isActive ? styles.sessionCardActive : {}) }}
            onClick={() => onResume(s.session_id)}
          >
            <div style={styles.sessionHeader}>
              <span style={styles.sessionId}>
                {isActive ? '▶ ' : ''}{s.session_id.slice(0, 8)}…
              </span>
              <span style={styles.sessionTime}>{formatRelativeTime(s.updated_at)}</span>
            </div>
            <div style={styles.sessionPreview}>
              {s.preview || '(no messages)'}
            </div>
            <div style={styles.sessionMeta}>
              {s.user_turns} message{s.user_turns !== 1 ? 's' : ''} · {s.assistant_turns} response{s.assistant_turns !== 1 ? 's' : ''}
            </div>
          </div>
        )
      })}
    </div>
  )
}

export default function OutputPanel({
  outputFiles, sessionId, transcript, skills, readSkills, uploadedFiles, onResumeSession
}) {
  const [activeTab, setActiveTab] = useState(0)

  const tabs = [
    { label: 'Output Files', badge: outputFiles.length || null },
    { label: 'Sessions', badge: null },
    { label: 'Context', badge: null },
    { label: 'Transcript', badge: transcript.length || null },
  ]

  return (
    <div style={styles.container}>
      <div style={styles.tabs}>
        {tabs.map((t, i) => (
          <div
            key={t.label}
            style={{ ...styles.tab, ...(activeTab === i ? styles.tabActive : {}) }}
            onClick={() => setActiveTab(i)}
          >
            {t.label}{t.badge ? ` (${t.badge})` : ''}
          </div>
        ))}
      </div>

      <div style={styles.panel}>
        {activeTab === 0 && (
          <div style={styles.fileList}>
            {outputFiles.length === 0
              ? <div style={styles.empty}>No output files yet</div>
              : outputFiles.map(f => <FileCard key={f} filename={f} sessionId={sessionId} />)
            }
          </div>
        )}

        {activeTab === 1 && (
          <SessionsPanel
            currentSessionId={sessionId}
            onResume={onResumeSession}
          />
        )}

        {activeTab === 2 && (
          <ContextInspector skills={skills} readSkills={readSkills} uploadedFiles={uploadedFiles} />
        )}

        {activeTab === 3 && (
          <div style={styles.transcriptPanel}>
            <div style={styles.transcriptHeader}>
              <span style={{ fontSize: '12px', color: 'var(--text-dim)' }}>{transcript.length} events</span>
              {sessionId && (
                <a href={`/api/session/${sessionId}`} target="_blank" rel="noreferrer">
                  <button style={styles.downloadAllBtn}>⬇ Download JSONL</button>
                </a>
              )}
            </div>
            {transcript.length === 0
              ? <div style={styles.empty}>No transcript yet. Run a task first.</div>
              : transcript.map((record, i) => <TranscriptEntry key={i} record={record} />)
            }
          </div>
        )}
      </div>
    </div>
  )
}

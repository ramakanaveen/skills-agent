import React, { useEffect, useRef } from 'react'

const ICONS = {
  thinking: '🧠',
  tool_call: '🔧',
  tool_result: '📤',
  start: '🚀',
  complete: '✅',
  error: '❌',
  warning: '⚠️',
}

const TOOL_ICONS = {
  read_file: '📂',
  write_file: '✍️',
  run_code: '⚙️',
  list_files: '📋',
  scan_folder: '📁',
  analyze_file: '🔍',
  spawn_agent: '🤖',
}

const COLORS = {
  thinking: 'var(--accent)',
  tool_call: 'var(--yellow)',
  tool_result: 'var(--green)',
  start: 'var(--text-dim)',
  complete: 'var(--green)',
  error: 'var(--red)',
  warning: 'var(--orange)',
}

const styles = {
  container: {
    flex: 1,
    overflowY: 'auto',
    padding: '12px 16px',
    background: 'var(--bg)',
  },
  entry: {
    marginBottom: '8px',
    padding: '8px 10px',
    borderRadius: '4px',
    background: 'var(--bg2)',
    border: '1px solid var(--border)',
    wordBreak: 'break-word',
  },
  header: {
    display: 'flex',
    alignItems: 'baseline',
    gap: '6px',
    marginBottom: '2px',
  },
  stage: {
    fontSize: '11px',
    fontWeight: 'bold',
    textTransform: 'uppercase',
  },
  tool: {
    fontSize: '12px',
    color: 'var(--text-dim)',
  },
  text: {
    fontSize: '12px',
    color: 'var(--text)',
    whiteSpace: 'pre-wrap',
    maxHeight: '200px',
    overflowY: 'auto',
  },
  dim: {
    fontSize: '11px',
    color: 'var(--text-dim)',
    marginTop: '2px',
  },
  empty: {
    color: 'var(--text-dim)',
    fontSize: '12px',
    textAlign: 'center',
    marginTop: '40px',
  },
}

function EventEntry({ evt }) {
  const icon = evt.tool ? TOOL_ICONS[evt.tool] || '🔧' : ICONS[evt.stage] || '•'
  const color = COLORS[evt.stage] || 'var(--text)'

  let content = null
  if (evt.stage === 'thinking' && evt.text) {
    content = <div style={styles.text}>{evt.text}</div>
  } else if (evt.stage === 'tool_call' && evt.input) {
    const inputStr = typeof evt.input === 'object'
      ? JSON.stringify(evt.input, null, 2)
      : String(evt.input)
    content = <div style={styles.text}>{inputStr.slice(0, 300)}</div>
  } else if (evt.stage === 'tool_result' && evt.result) {
    const preview = evt.result.slice(0, 200)
    const truncated = evt.full_length > 200
    content = (
      <div>
        <div style={styles.text}>{preview}{truncated ? '…' : ''}</div>
        {truncated && (
          <div style={styles.dim}>{evt.full_length} chars total</div>
        )}
      </div>
    )
  } else if (evt.stage === 'complete') {
    content = (
      <div style={styles.dim}>
        {evt.output_files?.length || 0} output file(s) · session {evt.session_id?.slice(0, 8)}
      </div>
    )
  } else if (evt.text) {
    content = <div style={styles.text}>{evt.text}</div>
  }

  return (
    <div style={styles.entry}>
      <div style={styles.header}>
        <span>{icon}</span>
        <span style={{ ...styles.stage, color }}>{evt.stage}</span>
        {evt.tool && <span style={styles.tool}>{evt.tool}</span>}
      </div>
      {content}
    </div>
  )
}

export default function AgentTrace({ events }) {
  const bottomRef = useRef()

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [events])

  return (
    <div style={styles.container}>
      {events.length === 0 && (
        <div style={styles.empty}>Agent trace will appear here when you run a task</div>
      )}
      {events.map(evt => (
        <EventEntry key={evt.id} evt={evt} />
      ))}
      <div ref={bottomRef} />
    </div>
  )
}

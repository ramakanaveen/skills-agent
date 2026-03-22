import React, { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { UI } from '../config.js'

const TOOL_ICONS = {
  read_file: '📂',
  write_file: '✍️',
  run_code: '⚙️',
  list_files: '📋',
}

const styles = {
  container: {
    flex: 1,
    overflowY: 'auto',
    padding: '16px',
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  empty: {
    margin: 'auto',
    textAlign: 'center',
    color: 'var(--text-dim)',
    fontSize: '13px',
    lineHeight: '2',
  },
  emptyTitle: {
    color: 'var(--accent)',
    fontSize: '15px',
    marginBottom: '8px',
  },
  userBubble: {
    alignSelf: 'flex-end',
    maxWidth: '80%',
    background: 'var(--accent)',
    color: '#0d1117',
    borderRadius: '12px 12px 2px 12px',
    padding: '10px 14px',
    fontSize: '13px',
    lineHeight: '1.5',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
  },
  agentTurn: {
    alignSelf: 'flex-start',
    maxWidth: '92%',
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  agentLabel: {
    fontSize: '10px',
    color: 'var(--text-dim)',
    marginBottom: '2px',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  agentBubble: {
    background: 'var(--bg2)',
    border: '1px solid var(--border)',
    borderRadius: '2px 12px 12px 12px',
    padding: '10px 14px',
    fontSize: '13px',
    color: 'var(--text)',
    lineHeight: '1.6',
    wordBreak: 'break-word',
  },
  thinkingDot: {
    display: 'inline-flex',
    gap: '3px',
    padding: '10px 14px',
    background: 'var(--bg2)',
    border: '1px solid var(--border)',
    borderRadius: '2px 12px 12px 12px',
  },
  dot: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    background: 'var(--text-dim)',
    animation: 'pulse 1.2s ease-in-out infinite',
  },
  traceList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  traceItem: {
    fontSize: '11px',
    padding: '5px 10px',
    background: 'var(--bg)',
    border: '1px solid var(--border)',
    borderRadius: '4px',
    color: 'var(--text-dim)',
    cursor: 'pointer',
    userSelect: 'none',
  },
  traceHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  traceBody: {
    marginTop: '5px',
    padding: '5px 8px',
    background: 'var(--bg2)',
    borderRadius: '3px',
    fontSize: '11px',
    color: 'var(--text)',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-all',
    maxHeight: '120px',
    overflowY: 'auto',
  },
  toolName: {
    color: 'var(--yellow)',
    fontWeight: 'bold',
  },
  resultLen: {
    marginLeft: 'auto',
    color: 'var(--text-dim)',
    fontSize: '10px',
  },
}

// Inject styles once
const styleSheet = document.createElement('style')
styleSheet.textContent = `
  @keyframes pulse {
    0%, 80%, 100% { opacity: 0.2; transform: scale(0.8); }
    40% { opacity: 1; transform: scale(1); }
  }

  .agent-md p { margin: 0 0 8px 0; }
  .agent-md p:last-child { margin-bottom: 0; }
  .agent-md h1, .agent-md h2, .agent-md h3 {
    color: var(--accent);
    font-family: inherit;
    margin: 10px 0 6px 0;
    font-size: 13px;
    font-weight: 700;
  }
  .agent-md h1 { font-size: 15px; }
  .agent-md h2 { font-size: 14px; }
  .agent-md ul, .agent-md ol {
    padding-left: 18px;
    margin: 6px 0;
  }
  .agent-md li { margin: 3px 0; }
  .agent-md strong { color: var(--text); font-weight: 700; }
  .agent-md em { color: var(--text-dim); font-style: italic; }
  .agent-md code {
    background: var(--bg3, #21262d);
    border: 1px solid var(--border);
    border-radius: 3px;
    padding: 1px 5px;
    font-family: 'Courier New', monospace;
    font-size: 11px;
    color: var(--orange, #e3b341);
  }
  .agent-md pre {
    background: var(--bg3, #21262d);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 10px 12px;
    overflow-x: auto;
    margin: 8px 0;
  }
  .agent-md pre code {
    background: none;
    border: none;
    padding: 0;
    color: var(--text);
    font-size: 12px;
  }
  .agent-md blockquote {
    border-left: 3px solid var(--accent);
    padding-left: 10px;
    color: var(--text-dim);
    margin: 6px 0;
  }
  .agent-md hr {
    border: none;
    border-top: 1px solid var(--border);
    margin: 10px 0;
  }
  .agent-md a { color: var(--accent); }
  .agent-md table { border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 12px; }
  .agent-md th, .agent-md td {
    border: 1px solid var(--border);
    padding: 5px 10px;
    text-align: left;
  }
  .agent-md th { background: var(--bg3, #21262d); font-weight: 700; color: var(--accent); }
`
document.head.appendChild(styleSheet)

function TraceEvent({ evt }) {
  const [expanded, setExpanded] = useState(false)

  if (evt.stage === 'warning') {
    return (
      <div style={{ ...styles.traceItem, color: 'var(--orange)', cursor: 'default' }}>
        ⚠️ {evt.text}
      </div>
    )
  }
  if (evt.stage === 'error') {
    return (
      <div style={{ ...styles.traceItem, color: 'var(--red)', cursor: 'default' }}>
        ❌ {evt.text}
      </div>
    )
  }

  if (evt.stage === 'tool_call') {
    const icon = TOOL_ICONS[evt.tool] || '🔧'
    const inputPreview = evt.input
      ? Object.entries(evt.input).map(([k, v]) =>
          `${k}: ${String(v).slice(0, 60)}`
        ).join(' · ')
      : ''
    return (
      <div style={styles.traceItem} onClick={() => setExpanded(e => !e)}>
        <div style={styles.traceHeader}>
          <span>{icon}</span>
          <span style={styles.toolName}>{evt.tool}</span>
          <span style={{ color: 'var(--text-dim)' }}>{inputPreview.slice(0, UI.traceInputPreviewChars)}</span>
          <span style={styles.resultLen}>{expanded ? '▲' : '▼'}</span>
        </div>
        {expanded && evt.input && (
          <div style={styles.traceBody}>
            {JSON.stringify(evt.input, null, 2)}
          </div>
        )}
      </div>
    )
  }

  if (evt.stage === 'tool_result') {
    const icon = TOOL_ICONS[evt.tool] || '📤'
    const truncated = evt.full_length > UI.traceResultBadgeThreshold
    return (
      <div style={{ ...styles.traceItem, borderColor: 'rgba(63,185,80,0.2)' }}
           onClick={() => setExpanded(e => !e)}>
        <div style={styles.traceHeader}>
          <span>{icon}</span>
          <span style={{ color: 'var(--green)' }}>{evt.tool} result</span>
          {truncated && (
            <span style={styles.resultLen}>{evt.full_length} chars</span>
          )}
          <span style={{ ...styles.resultLen, marginLeft: truncated ? '4px' : 'auto' }}>
            {expanded ? '▲' : '▼'}
          </span>
        </div>
        {expanded && (
          <div style={styles.traceBody}>{evt.result}</div>
        )}
      </div>
    )
  }

  return null
}

function ThinkingIndicator() {
  return (
    <div style={styles.thinkingDot}>
      {[0, 1, 2].map(i => (
        <div key={i} style={{ ...styles.dot, animationDelay: `${i * 0.2}s` }} />
      ))}
    </div>
  )
}

function AgentTurn({ turn, isLast, running }) {
  const hasText = turn.text && turn.text.trim().length > 0
  const hasEvents = turn.events && turn.events.length > 0
  const isThinking = isLast && running && !hasText && !hasEvents

  return (
    <div style={styles.agentTurn}>
      <div style={styles.agentLabel}>Agent</div>
      {isThinking && <ThinkingIndicator />}
      {hasEvents && (
        <div style={styles.traceList}>
          {turn.events.map(evt => <TraceEvent key={evt.id} evt={evt} />)}
        </div>
      )}
      {hasText && (
        <div style={styles.agentBubble}>
          <div className="agent-md">
            <ReactMarkdown>{turn.text}</ReactMarkdown>
          </div>
          {isLast && running && <span style={{ opacity: 0.5 }}>▌</span>}
        </div>
      )}
      {!hasText && isLast && running && hasEvents && (
        <ThinkingIndicator />
      )}
    </div>
  )
}

export default function ChatView({ turns, running }) {
  const bottomRef = useRef()

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [turns])

  return (
    <div style={styles.container}>
      {turns.length === 0 && (
        <div style={styles.empty}>
          <div style={styles.emptyTitle}>⚡ Skills Agent</div>
          <div>Type a task below to get started.</div>
          <div style={{ marginTop: '6px', fontSize: '12px' }}>
            Try: <em>"Write a project status report"</em><br />
            or: <em>"Help me build a resume from scratch"</em>
          </div>
        </div>
      )}
      {turns.map((turn, i) => (
        turn.role === 'user'
          ? <div key={turn.id} style={styles.userBubble}>{turn.text}</div>
          : <AgentTurn
              key={turn.id}
              turn={turn}
              isLast={i === turns.length - 1}
              running={running}
            />
      ))}
      <div ref={bottomRef} />
    </div>
  )
}

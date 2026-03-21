import React, { useState, useRef, useEffect } from 'react'

const styles = {
  container: {
    borderTop: '1px solid var(--border)',
    background: 'var(--bg2)',
    padding: '10px 12px',
    flexShrink: 0,
  },
  uploadRow: {
    display: 'flex',
    gap: '6px',
    flexWrap: 'wrap',
    marginBottom: '6px',
  },
  badge: {
    padding: '2px 8px',
    background: 'var(--bg3)',
    border: '1px solid var(--border)',
    borderRadius: '3px',
    color: 'var(--accent)',
    fontSize: '11px',
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
  },
  badgeRemove: {
    cursor: 'pointer',
    color: 'var(--text-dim)',
    fontWeight: 'bold',
    lineHeight: 1,
  },
  inputRow: {
    display: 'flex',
    gap: '8px',
    alignItems: 'flex-end',
  },
  uploadBtn: {
    padding: '7px 10px',
    background: 'var(--bg3)',
    border: '1px solid var(--border)',
    borderRadius: '4px',
    color: 'var(--text-dim)',
    fontSize: '14px',
    cursor: 'pointer',
    flexShrink: 0,
    lineHeight: 1,
  },
  textarea: {
    flex: 1,
    minHeight: '38px',
    maxHeight: '160px',
    background: 'var(--bg)',
    border: '1px solid var(--border)',
    borderRadius: '4px',
    color: 'var(--text)',
    fontFamily: 'var(--font)',
    fontSize: '13px',
    padding: '9px 12px',
    resize: 'none',
    outline: 'none',
    lineHeight: '1.4',
    overflow: 'auto',
  },
  sendBtn: {
    padding: '7px 16px',
    background: 'var(--accent)',
    border: 'none',
    borderRadius: '4px',
    color: '#0d1117',
    fontWeight: 'bold',
    fontSize: '13px',
    cursor: 'pointer',
    flexShrink: 0,
    lineHeight: 1,
  },
  sendBtnDisabled: {
    background: 'var(--border)',
    color: 'var(--text-dim)',
    cursor: 'not-allowed',
  },
  hint: {
    fontSize: '10px',
    color: 'var(--text-dim)',
    marginTop: '5px',
    textAlign: 'right',
  },
}

export default function ReplyBar({ onSend, running, uploadedFiles, setUploadedFiles, hasHistory }) {
  const [text, setText] = useState('')
  const fileRef = useRef()
  const textareaRef = useRef()

  // Auto-focus reply bar when agent finishes
  useEffect(() => {
    if (!running && hasHistory) {
      textareaRef.current?.focus()
    }
  }, [running])

  const handleUpload = async (e) => {
    const files = Array.from(e.target.files)
    for (const file of files) {
      const form = new FormData()
      form.append('file', file)
      try {
        const res = await fetch('/api/upload', { method: 'POST', body: form })
        const data = await res.json()
        setUploadedFiles(prev => [...prev, { name: data.filename, path: data.path }])
      } catch (err) {
        console.error('Upload failed', err)
      }
    }
    e.target.value = ''
  }

  const removeFile = (name) => {
    setUploadedFiles(prev => prev.filter(f => f.name !== name))
  }

  const handleSend = () => {
    if (!text.trim() || running) return
    onSend(text.trim())
    setText('')
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // Auto-resize textarea
  const handleChange = (e) => {
    setText(e.target.value)
    e.target.style.height = 'auto'
    e.target.style.height = Math.min(e.target.scrollHeight, 160) + 'px'
  }

  return (
    <div style={styles.container}>
      {uploadedFiles.length > 0 && (
        <div style={styles.uploadRow}>
          {uploadedFiles.map(f => (
            <span key={f.name} style={styles.badge}>
              📎 {f.name}
              <span style={styles.badgeRemove} onClick={() => removeFile(f.name)}>×</span>
            </span>
          ))}
        </div>
      )}
      <div style={styles.inputRow}>
        <button
          style={styles.uploadBtn}
          onClick={() => fileRef.current.click()}
          disabled={running}
          title="Upload file"
        >
          📎
        </button>
        <input
          ref={fileRef}
          type="file"
          multiple
          style={{ display: 'none' }}
          onChange={handleUpload}
        />
        <textarea
          ref={textareaRef}
          style={styles.textarea}
          value={text}
          onChange={handleChange}
          onKeyDown={handleKey}
          placeholder={running ? 'Agent is working…' : hasHistory ? 'Reply…' : 'Describe your task…'}
          disabled={running}
          rows={1}
        />
        <button
          style={{ ...styles.sendBtn, ...(running || !text.trim() ? styles.sendBtnDisabled : {}) }}
          onClick={handleSend}
          disabled={running || !text.trim()}
        >
          {running ? '⏳' : '▶'}
        </button>
      </div>
      <div style={styles.hint}>Enter to send · Shift+Enter for new line</div>
    </div>
  )
}

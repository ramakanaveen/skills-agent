import React, { useState, useRef } from 'react'

const styles = {
  container: {
    padding: '16px',
    borderBottom: '1px solid var(--border)',
    background: 'var(--bg2)',
  },
  textarea: {
    width: '100%',
    minHeight: '90px',
    background: 'var(--bg)',
    border: '1px solid var(--border)',
    borderRadius: '4px',
    color: 'var(--text)',
    fontFamily: 'var(--font)',
    fontSize: '13px',
    padding: '10px',
    resize: 'vertical',
    outline: 'none',
  },
  row: {
    display: 'flex',
    gap: '8px',
    marginTop: '10px',
    alignItems: 'center',
    flexWrap: 'wrap',
  },
  uploadBtn: {
    padding: '6px 12px',
    background: 'var(--bg3)',
    border: '1px solid var(--border)',
    borderRadius: '4px',
    color: 'var(--text-dim)',
    fontSize: '12px',
    cursor: 'pointer',
  },
  runBtn: {
    padding: '6px 20px',
    background: 'var(--accent)',
    border: 'none',
    borderRadius: '4px',
    color: '#0d1117',
    fontWeight: 'bold',
    fontSize: '13px',
    cursor: 'pointer',
    marginLeft: 'auto',
  },
  runBtnDisabled: {
    background: 'var(--border)',
    color: 'var(--text-dim)',
    cursor: 'not-allowed',
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
  },
}

export default function TaskInput({ onRun, running, uploadedFiles, setUploadedFiles }) {
  const [task, setTask] = useState('')
  const fileRef = useRef()

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

  const handleRun = () => {
    if (!task.trim() || running) return
    onRun(task.trim())
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      handleRun()
    }
  }

  return (
    <div style={styles.container}>
      <textarea
        style={styles.textarea}
        value={task}
        onChange={e => setTask(e.target.value)}
        onKeyDown={handleKey}
        placeholder="Describe your task… (Cmd+Enter to run)"
        disabled={running}
      />
      <div style={styles.row}>
        <button style={styles.uploadBtn} onClick={() => fileRef.current.click()} disabled={running}>
          📎 Upload files
        </button>
        <input
          ref={fileRef}
          type="file"
          multiple
          style={{ display: 'none' }}
          onChange={handleUpload}
        />
        {uploadedFiles.map(f => (
          <span key={f.name} style={styles.badge}>
            {f.name}
            <span style={styles.badgeRemove} onClick={() => removeFile(f.name)}>×</span>
          </span>
        ))}
        <button
          style={{ ...styles.runBtn, ...(running ? styles.runBtnDisabled : {}) }}
          onClick={handleRun}
          disabled={running}
        >
          {running ? '⏳ Running…' : '▶ Run'}
        </button>
      </div>
    </div>
  )
}

import React, { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { marked } from 'marked'
import { API, UI } from '../config.js'

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    flex: 1,
    overflow: 'hidden',
    minHeight: 0,
  },
  tabs: {
    display: 'flex',
    borderBottom: '1px solid var(--border)',
    background: 'var(--bg2)',
  },
  tab: {
    padding: '8px 16px',
    cursor: 'pointer',
    fontSize: '12px',
    fontWeight: '500',
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
    minHeight: 0,
  },
  fileList: {
    flex: 1,
    overflowY: 'auto',
    padding: '12px 16px',
    minHeight: 0,
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
}

const PREVIEWABLE = ['.md', '.txt', '.py', '.js', '.ts', '.jsx', '.tsx', '.json', '.yaml', '.yml', '.html', '.css', '.png', '.jpg', '.jpeg']

function FileCard({ filename, sessionId }) {
  const [expanded, setExpanded] = useState(false)
  const [preview, setPreview] = useState(null)
  const [loading, setLoading] = useState(false)

  const ext = '.' + filename.split('.').pop()
  const canPreview = PREVIEWABLE.includes(ext)
  const isImage = ['.png', '.jpg', '.jpeg'].includes(ext)
  const isMarkdown = ext === '.md'
  const downloadUrl = sessionId ? `/api/download/${sessionId}/${filename}` : `/api/download/${filename}`

  const loadPreview = async () => {
    if (isImage) { setExpanded(e => !e); return }
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
      {expanded && (
        isImage
          ? <img src={downloadUrl} alt={filename} style={{ maxWidth: '100%', maxHeight: '300px', objectFit: 'contain', display: 'block', padding: '8px' }} />
          : isMarkdown
            ? <div style={{ padding: '12px 16px', background: 'var(--bg)', borderTop: '1px solid var(--border)', fontSize: '12px', lineHeight: '1.6', color: 'var(--text)', maxHeight: '400px', overflowY: 'auto' }}>
                <div className="agent-md">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{preview}</ReactMarkdown>
                </div>
              </div>
            : preview !== null && <div style={styles.preview}>{preview}</div>
      )}
    </div>
  )
}

function PreviewPanel({ outputFiles, sessionId }) {
  const [content, setContent] = useState(null)
  const [activeFile, setActiveFile] = useState(null)
  const [loading, setLoading] = useState(false)

  const IMAGE_EXTS = ['.png', '.jpg', '.jpeg', '.gif', '.webp']
  const TEXT_EXTS = ['.md', '.txt', '.csv', '.json']

  const sortedByLatest = (files) => [...files].sort((a, b) => b.localeCompare(a))

  const pickBestFile = (files) => {
    const sorted = sortedByLatest(files)
    return sorted.find(f => f.endsWith('.md'))
      || sorted.find(f => IMAGE_EXTS.some(e => f.endsWith(e)))
      || sorted.find(f => TEXT_EXTS.some(e => f.endsWith(e)))
      || null
  }

  useEffect(() => {
    if (!outputFiles || outputFiles.length === 0) { setContent(null); setActiveFile(null); return }
    const best = pickBestFile(outputFiles)
    if (!best) return
    const ext = '.' + best.split('.').pop().toLowerCase()
    if (IMAGE_EXTS.includes(ext)) { setActiveFile(best); setContent('__image__'); return }
    setActiveFile(best)
    setLoading(true)
    const url = sessionId ? `/api/download/${sessionId}/${best}` : `/api/download/${best}`
    fetch(url).then(r => r.text()).then(text => {
      setContent(text); setLoading(false)
    }).catch(() => { setContent('(could not load preview)'); setLoading(false) })
  }, [outputFiles, sessionId])

  const previewableFiles = sortedByLatest(
    (outputFiles || []).filter(f =>
      IMAGE_EXTS.some(e => f.endsWith(e)) || TEXT_EXTS.some(e => f.endsWith(e))
    )
  )

  const loadFile = (filename) => {
    const ext = '.' + filename.split('.').pop().toLowerCase()
    setActiveFile(filename)
    if (IMAGE_EXTS.includes(ext)) { setContent('__image__'); return }
    setLoading(true)
    const url = sessionId ? `/api/download/${sessionId}/${filename}` : `/api/download/${filename}`
    fetch(url).then(r => r.text()).then(text => {
      setContent(text); setLoading(false)
    }).catch(() => { setContent('(could not load)'); setLoading(false) })
  }

  const imgComponents = {
    img: ({ src, alt }) => {
      const resolved = src && !src.startsWith('http') && !src.startsWith('/')
        ? (sessionId ? `/api/download/${sessionId}/${src}` : `/api/download/${src}`)
        : src
      return (
        <img src={resolved} alt={alt || ''} style={{
          maxWidth: '100%', borderRadius: '6px',
          margin: '10px 0', display: 'block',
          border: '1px solid var(--border)',
        }} />
      )
    }
  }

  if (!outputFiles || outputFiles.length === 0) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ color: 'var(--text-dim)', fontSize: '12px', textAlign: 'center' }}>
          <div style={{ fontSize: '24px', marginBottom: '8px' }}>📄</div>
          Run a task to see output here
        </div>
      </div>
    )
  }

  const isImage = activeFile && ['.png', '.jpg', '.jpeg', '.gif', '.webp'].some(e => activeFile.endsWith(e))
  const isMd = activeFile && activeFile.endsWith('.md')

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minHeight: 0 }}>
      {previewableFiles.length > 0 && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: '8px',
          padding: '8px 12px', borderBottom: '1px solid var(--border)',
          background: 'var(--bg2)', flexShrink: 0,
        }}>
          <span style={{ fontSize: '11px', color: 'var(--text-dim)', flexShrink: 0 }}>File:</span>
          <select
            value={activeFile || ''}
            onChange={e => loadFile(e.target.value)}
            style={{
              flex: 1, padding: '4px 8px', fontSize: '11px',
              background: 'var(--bg3)', color: 'var(--text)',
              border: '1px solid var(--border)', borderRadius: '4px',
              cursor: 'pointer', fontFamily: 'monospace',
            }}
          >
            {previewableFiles.map(f => <option key={f} value={f}>{f}</option>)}
          </select>
        </div>
      )}
      <div style={{ flex: 1, overflowY: 'auto', padding: '16px', minHeight: 0 }}>
        {loading && <div style={{ color: 'var(--text-dim)', fontSize: '12px' }}>Loading…</div>}
        {!loading && content === '__image__' && activeFile && (
          <img
            src={sessionId ? `/api/download/${sessionId}/${activeFile}` : `/api/download/${activeFile}`}
            alt={activeFile}
            style={{ maxWidth: '100%', borderRadius: '6px', display: 'block' }}
          />
        )}
        {!loading && content && content !== '__image__' && isMd && (
          <div className="agent-md" style={{ fontSize: '13px', lineHeight: '1.7' }}>
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={imgComponents}>{content}</ReactMarkdown>
          </div>
        )}
        {!loading && content && content !== '__image__' && !isMd && (
          <pre style={{ fontSize: '12px', color: 'var(--text)', whiteSpace: 'pre-wrap', fontFamily: 'monospace', lineHeight: '1.5' }}>{content}</pre>
        )}
      </div>
    </div>
  )
}

const exportBtnStyle = {
  padding: '4px 12px',
  background: 'var(--bg3)',
  border: '1px solid var(--border)',
  borderRadius: '6px',
  color: 'var(--text)',
  fontSize: '11px',
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  gap: '4px',
}

export default function OutputPanel({ outputFiles, sessionId, forcePreview }) {
  const [activeTab, setActiveTab] = useState(0)

  useEffect(() => {
    if (forcePreview) setActiveTab(0)
  }, [forcePreview])

  const handlePrintExport = async (files, sid) => {
    const mdFiles = files.filter(f => f.endsWith('.md'))
    let html = `<html><head><title>Skills Agent Report</title><style>
      body { font-family: -apple-system, sans-serif; max-width: 800px; margin: 40px auto; color: #1a1a1a; line-height: 1.6; }
      h1 { font-size: 24px; border-bottom: 2px solid #333; padding-bottom: 8px; margin-top: 32px; }
      h2 { font-size: 20px; margin-top: 28px; color: #333; }
      h3 { font-size: 16px; margin-top: 20px; }
      p { margin: 8px 0; }
      ul, ol { padding-left: 24px; margin: 8px 0; }
      li { margin: 4px 0; }
      strong { font-weight: 700; }
      em { font-style: italic; color: #555; }
      table { border-collapse: collapse; width: 100%; margin: 16px 0; }
      th, td { border: 1px solid #ddd; padding: 8px 12px; text-align: left; }
      th { background: #f5f5f5; font-weight: 600; }
      code { background: #f5f5f5; padding: 2px 6px; border-radius: 3px; font-size: 12px; font-family: monospace; }
      pre { background: #f5f5f5; padding: 16px; border-radius: 6px; overflow-x: auto; margin: 12px 0; }
      pre code { background: none; padding: 0; }
      img { max-width: 100%; margin: 16px 0; border-radius: 4px; page-break-inside: avoid; }
      hr { border: none; border-top: 1px solid #ddd; margin: 32px 0; }
      .section { margin-bottom: 24px; }
      @media print { body { margin: 20px; } h1, h2, h3 { page-break-after: avoid; } }
    </style></head><body>`
    for (const filename of mdFiles) {
      const url = sid ? `/api/download/${sid}/${filename}` : `/api/download/${filename}`
      try {
        const res = await fetch(url)
        const text = await res.text()
        const renderedMd = marked(text)
        const fixedHtml = renderedMd.replace(
          /src="(?!http)(?!\/)([^"]+)"/g,
          (match, fname) => `src="${sid ? `/api/download/${sid}/${fname}` : `/api/download/${fname}`}"`
        )
        html += `<div class="section">${fixedHtml}</div><hr/>`
      } catch (e) { console.error(e) }
    }
    html += '</body></html>'
    const w = window.open('', '_blank')
    w.document.write(html)
    w.document.close()
    w.focus()
    setTimeout(() => w.print(), 500)
  }

  const handleMarkdownExport = async (files, sid) => {
    const mdFiles = files.filter(f => f.endsWith('.md'))
    let combined = `# Skills Agent Report\n\nGenerated: ${new Date().toLocaleString()}\n\n---\n\n`
    for (const filename of mdFiles) {
      const url = sid ? `/api/download/${sid}/${filename}` : `/api/download/${filename}`
      try {
        const res = await fetch(url)
        const text = await res.text()
        combined += `## ${filename}\n\n${text}\n\n---\n\n`
      } catch (e) { console.error(e) }
    }
    const blob = new Blob([combined], { type: 'text/markdown' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `report_${Date.now()}.md`
    a.click()
    URL.revokeObjectURL(a.href)
  }

  const tabs = [
    { label: 'Preview' },
    { label: `Files${outputFiles.length ? ` (${outputFiles.length})` : ''}` },
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
            {t.label}
          </div>
        ))}
      </div>

      <div style={styles.panel}>
        {activeTab === 0 && (
          <PreviewPanel outputFiles={outputFiles} sessionId={sessionId} />
        )}

        {activeTab === 1 && (
          <div style={{ display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden' }}>
            {outputFiles.length > 0 && (
              <div style={{ display: 'flex', gap: '8px', padding: '10px 16px', borderBottom: '1px solid var(--border)', background: 'var(--bg2)', flexShrink: 0, alignItems: 'center' }}>
                <span style={{ fontSize: '11px', color: 'var(--text-dim)', marginRight: '4px' }}>Export:</span>
                <button style={exportBtnStyle} onClick={() => handlePrintExport(outputFiles, sessionId)}>📄 PDF</button>
                <button style={exportBtnStyle} onClick={() => handleMarkdownExport(outputFiles, sessionId)}>📝 Markdown</button>
              </div>
            )}
            <div style={styles.fileList}>
              {outputFiles.length === 0
                ? <div style={styles.empty}>No output files yet</div>
                : outputFiles.map(f => <FileCard key={f} filename={f} sessionId={sessionId} />)
              }
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

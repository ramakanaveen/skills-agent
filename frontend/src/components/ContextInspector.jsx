import React, { useState } from 'react'

const styles = {
  container: {
    flex: 1,
    overflowY: 'auto',
    padding: '12px 16px',
    background: 'var(--bg)',
  },
  section: {
    marginBottom: '12px',
    border: '1px solid var(--border)',
    borderRadius: '4px',
    overflow: 'hidden',
  },
  sectionHeader: {
    padding: '8px 12px',
    background: 'var(--bg2)',
    cursor: 'pointer',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    fontSize: '12px',
    fontWeight: 'bold',
    color: 'var(--accent)',
    userSelect: 'none',
  },
  sectionBody: {
    padding: '10px 12px',
    background: 'var(--bg)',
    fontSize: '12px',
    color: 'var(--text)',
    whiteSpace: 'pre-wrap',
    maxHeight: '300px',
    overflowY: 'auto',
    borderTop: '1px solid var(--border)',
  },
  skillRow: {
    padding: '6px 12px',
    borderTop: '1px solid var(--border)',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    fontSize: '12px',
    background: 'var(--bg)',
  },
  skillRowRead: {
    background: 'rgba(63, 185, 80, 0.08)',
  },
  skillName: {
    fontWeight: 'bold',
    color: 'var(--text)',
  },
  skillNameRead: {
    color: 'var(--green)',
  },
  skillPath: {
    fontSize: '11px',
    color: 'var(--text-dim)',
  },
  skillPathRead: {
    color: 'var(--green)',
  },
  readBadge: {
    fontSize: '10px',
    background: 'rgba(63, 185, 80, 0.2)',
    color: 'var(--green)',
    padding: '1px 6px',
    borderRadius: '3px',
    border: '1px solid var(--green)',
  },
  empty: {
    color: 'var(--text-dim)',
    fontSize: '12px',
    fontStyle: 'italic',
    padding: '8px 0',
  },
}

function Expandable({ title, content, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div style={styles.section}>
      <div style={styles.sectionHeader} onClick={() => setOpen(o => !o)}>
        <span>{title}</span>
        <span style={{ color: 'var(--text-dim)' }}>{open ? '▲' : '▼'}</span>
      </div>
      {open && <div style={styles.sectionBody}>{content}</div>}
    </div>
  )
}

export default function ContextInspector({ skills, readSkills, uploadedFiles }) {
  return (
    <div style={styles.container}>
      <Expandable
        title="SOUL.md — Agent Identity"
        content="You are a general-purpose agent. You help with any task by reading the right skill before acting. Your skills teach you how to create documents, write code, analyse files, build workflows, and more.\n\nBefore any non-trivial task, check the available skills and read the relevant SKILL.md using read_file. The skill is your source of truth.\n\nIf no skill matches a task, use the skill-creator skill to write one first, then use it."
      />
      <Expandable
        title="AGENTS.md — Behavioral Rules"
        content="1. Read the relevant SKILL.md before starting any task\n2. If a user uploaded a file (policy, spec, notes), read it too\n3. For multi-step tasks, chain multiple skills in sequence\n4. After writing code, always run it — do not just produce it\n5. If execution fails, read the error, fix the code, retry up to 3 times\n6. If no skill exists for a task, use skill-creator to write one first\n7. Keep the user informed at each step via your text responses\n8. End every task with a summary of what was produced"
      />
      <Expandable
        title="TOOLS.md — Available Tools"
        content="read_file(path) — Read any file by path relative to backend/\nwrite_file(filename, content) — Write content to outputs/ or skills/\nrun_code(filename, runtime) — Execute from outputs/, returns stdout/stderr/exit_code\nlist_files(directory) — List files in skills/, uploads/, or outputs/"
      />

      <div style={styles.section}>
        <div style={styles.sectionHeader}>
          <span>Available Skills ({skills.length})</span>
        </div>
        {skills.length === 0 && (
          <div style={{ padding: '10px 12px' }}>
            <div style={styles.empty}>No skills loaded</div>
          </div>
        )}
        {skills.map(s => {
          const wasRead = readSkills.has(s.name)
          const isPrivate = s.visibility === 'private'
          return (
            <div
              key={s.name}
              style={{ ...styles.skillRow, ...(wasRead ? styles.skillRowRead : {}) }}
            >
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ ...styles.skillName, ...(wasRead ? styles.skillNameRead : {}) }}>
                    {s.name}
                  </span>
                  <span style={{
                    fontSize: '9px',
                    padding: '1px 5px',
                    borderRadius: '3px',
                    border: `1px solid ${isPrivate ? 'var(--orange)' : 'var(--border)'}`,
                    color: isPrivate ? 'var(--orange)' : 'var(--text-dim)',
                    background: isPrivate ? 'rgba(227,179,65,0.08)' : 'transparent',
                    flexShrink: 0,
                  }}>
                    {isPrivate ? '🔒 private' : '🌐 public'}
                  </span>
                </div>
                <div style={{ ...styles.skillPath, ...(wasRead ? styles.skillPathRead : {}) }}>
                  {s.skill_md_path}
                </div>
              </div>
              {wasRead && <span style={styles.readBadge}>READ</span>}
            </div>
          )
        })}
      </div>

      {uploadedFiles.length > 0 && (
        <div style={styles.section}>
          <div style={styles.sectionHeader}>
            <span>Uploaded Files ({uploadedFiles.length})</span>
          </div>
          {uploadedFiles.map(f => (
            <div key={f.name} style={styles.skillRow}>
              <div>
                <div style={styles.skillName}>{f.name}</div>
                <div style={styles.skillPath}>uploads/{f.name}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

/**
 * Frontend configuration — centralised place for all magic numbers and
 * API endpoint strings. Override by setting VITE_* env vars in .env.local.
 *
 * Env var examples:
 *   VITE_API_BASE=https://myserver.example.com
 *   VITE_FILE_PREVIEW_CHARS=5000
 */

// Base URL for all backend API calls (empty = same origin, works for proxy)
export const API_BASE = import.meta.env.VITE_API_BASE ?? ''

// API endpoint paths
export const API = {
  run:        `${API_BASE}/api/run`,
  skills:     `${API_BASE}/api/skills`,
  skillStats: `${API_BASE}/api/skill-stats`,
  upload:     `${API_BASE}/api/upload`,
  sessions:   `${API_BASE}/api/sessions`,
  health:     `${API_BASE}/api/health`,
  session:    (id)           => `${API_BASE}/api/session/${id}`,
  outputs:    (id)           => `${API_BASE}/api/outputs/${id}`,
  download:   (sid, file)    => `${API_BASE}/api/download/${sid}/${file}`,
}

// UI — truncation / preview lengths
export const UI = {
  // Characters of tool result shown in the agent trace panel
  traceResultPreviewChars: Number(import.meta.env.VITE_TRACE_RESULT_PREVIEW_CHARS ?? 200),

  // Characters shown in the file preview panel (Output Files tab)
  filePreviewChars: Number(import.meta.env.VITE_FILE_PREVIEW_CHARS ?? 2000),

  // Characters of tool result truncated when reconstructing past sessions
  sessionToolResultChars: Number(import.meta.env.VITE_SESSION_TOOL_RESULT_CHARS ?? 500),

  // Characters shown per transcript entry in the Transcript tab
  transcriptEntryChars: Number(import.meta.env.VITE_TRANSCRIPT_ENTRY_CHARS ?? 300),

  // Threshold above which the trace shows "N chars" badge (full_length > this)
  traceResultBadgeThreshold: Number(import.meta.env.VITE_TRACE_RESULT_BADGE_THRESHOLD ?? 200),

  // Max characters used in tool_call input preview inline
  traceInputPreviewChars: Number(import.meta.env.VITE_TRACE_INPUT_PREVIEW_CHARS ?? 80),
}

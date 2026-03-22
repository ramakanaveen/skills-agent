import React from 'react'
import ReactDOM from 'react-dom/client'
import { applyTheme, getStoredTheme } from './themes.js'
import './index2.css'
import App from './App.jsx'

// Apply saved theme before first render to avoid flash
applyTheme(getStoredTheme())

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode><App /></React.StrictMode>
)

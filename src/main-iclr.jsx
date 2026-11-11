import React from 'react'
import { createRoot } from 'react-dom/client'
import App, { init } from './App.jsx'
import { navFor } from './pages.js'
import report from './data/report.iclr.json'
import './styles.css'

init(report, navFor('iclr'))
createRoot(document.getElementById('root')).render(<App />)

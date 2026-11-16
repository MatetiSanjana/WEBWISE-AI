import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
// Self-hosted fonts (bundled by Vite, no third-party requests): Crimson Pro for headings, Instrument Sans for the interface.
import '@fontsource-variable/crimson-pro/wght.css'
import '@fontsource-variable/crimson-pro/wght-italic.css'
import '@fontsource-variable/instrument-sans/wght.css'
import './styles/index.css'
import App from './App'
import { SettingsProvider } from './hooks/useSettings'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <SettingsProvider>
      <App />
    </SettingsProvider>
  </StrictMode>,
)

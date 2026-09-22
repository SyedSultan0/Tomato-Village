import { useState } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import NavBar from './components/NavBar.jsx'
import MobileTabs from './components/MobileTabs.jsx'
import FarmerView from './views/FarmerView.jsx'
import OfficerView from './views/OfficerView.jsx'
import MapView from './views/MapView.jsx'
import { T } from './i18n.js'

export default function App() {
  const [lang, setLang] = useState(
    () => localStorage.getItem('lang') || 'en'
  )

  function changeLang(code) {
    setLang(code)
    localStorage.setItem('lang', code)
  }

  const t = T[lang] || T.en

  return (
    <div className="app-bg min-h-screen flex flex-col">
      <NavBar lang={lang} onChangeLang={changeLang} t={t} />

      <main className="flex-1 pb-20 md:pb-8">
        <Routes>
          <Route path="/" element={<Navigate to="/farmer" replace />} />
          <Route path="/farmer"  element={<FarmerView t={t} lang={lang} />} />
          <Route path="/officer" element={<OfficerView t={t} lang={lang} />} />
          <Route path="/map"     element={<MapView t={t} lang={lang} />} />
        </Routes>
      </main>

      <footer className="hidden md:block text-center text-xs text-stone-400 py-4 border-t border-stone-200">
        🌾 {t.appName} · SIH 2026 · PS 26131
      </footer>

      <MobileTabs t={t} />
    </div>
  )
}
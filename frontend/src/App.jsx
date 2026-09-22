import { useState } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import NavBar from './components/NavBar.jsx'
import MobileTabs from './components/MobileTabs.jsx'
import HomeView from './views/HomeView.jsx'
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
    <div className="min-h-screen flex flex-col" style={{ background: 'var(--cream)' }}>
      <NavBar lang={lang} onChangeLang={changeLang} t={t} />

      <main className="flex-1 pb-20 md:pb-0">
        <Routes>
          <Route path="/"        element={<HomeView t={t} lang={lang} />} />
          <Route path="/farmer"  element={<FarmerView t={t} lang={lang} />} />
          <Route path="/officer" element={<OfficerView t={t} lang={lang} />} />
          <Route path="/map"     element={<MapView t={t} lang={lang} />} />
          <Route path="*"        element={<Navigate to="/" replace />} />
        </Routes>
      </main>

      <footer
        className="hidden md:block py-8 text-xs"
        style={{
          background: 'var(--green-deep)',
          color: 'rgba(247,242,231,0.6)',
        }}
      >
        <div className="wrap flex justify-between items-center gap-4">
          <span
            className="font-semibold"
            style={{ fontFamily: 'Fraunces, serif', color: 'var(--cream-dim)', fontSize: 16 }}
          >
            Pandora Crop Intelligence
          </span>
          <span>Prototype build — Smart India Hackathon 2026, PS 26131</span>
        </div>
      </footer>

      <MobileTabs t={t} />
    </div>
  )
}
import { Routes, Route, Navigate } from 'react-router-dom'
import NavBar from './components/NavBar.jsx'
import FarmerView from './views/FarmerView.jsx'
import OfficerView from './views/OfficerView.jsx'
import MapView from './views/MapView.jsx'

export default function App() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <NavBar />
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<Navigate to="/farmer" replace />} />
          <Route path="/farmer" element={<FarmerView />} />
          <Route path="/officer" element={<OfficerView />} />
          <Route path="/map" element={<MapView />} />
        </Routes>
      </main>
      <footer className="text-center text-xs text-slate-500 py-3 border-t border-slate-800">
        🍅 Tomato-Village · SIH 2026 · PS 26131
      </footer>
    </div>
  )
}
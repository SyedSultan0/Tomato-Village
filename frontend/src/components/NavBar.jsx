import { NavLink, useLocation } from 'react-router-dom'
import LanguageBar from './LanguageBar.jsx'
import FarmerProfile from './FarmerProfile.jsx'

export default function NavBar({ lang, onChangeLang, t }) {
  const location = useLocation()
  const isHome = location.pathname === '/'

  const tabs = [
    { to: '/',        label: 'Home',  end: true },
    { to: '/farmer',  label: t.navFarmer },
    { to: '/officer', label: t.navOfficer },
    { to: '/map',     label: t.navMap },
    
  ]

  return (
    <nav
      className="sticky top-0 z-50 border-b"
      style={{
        background: 'rgba(30, 59, 44, 0.88)',
        backdropFilter: 'blur(10px)',
        WebkitBackdropFilter: 'blur(10px)',
        borderColor: 'rgba(216, 179, 74, 0.18)',
      }}
    >
      <div className="max-w-[1180px] mx-auto px-5 md:px-8 py-4 flex items-center justify-between gap-6">

        {/* Left: brand + profile */}
        <div className="flex items-center gap-4 min-w-0">
          <NavLink
            to="/"
            className="flex items-center gap-2.5 shrink-0"
            style={{ color: 'var(--cream)', fontFamily: 'Fraunces, serif', fontSize: 18, fontWeight: 600 }}
          >
            <svg viewBox="0 0 24 24" fill="none" width="24" height="24">
              <path d="M4 20C4 11 11 4 20 4c0 9-7 16-16 16Z" stroke="#7FA65A" strokeWidth="1.6" strokeLinejoin="round"/>
              <path d="M4 20c4-4 8-8 12-12" stroke="#3F6B4A" strokeWidth="1.3" strokeLinecap="round"/>
              <circle cx="17" cy="7" r="1.6" fill="#D8B34A"/>
            </svg>
            <span className="hidden sm:inline">Pandora</span>
          </NavLink>

          {!isHome && (
            <div className="hidden lg:block">
              <FarmerProfile t={t} />
            </div>
          )}
        </div>

        {/* Center: nav tabs (desktop) */}
        <div className="hidden md:flex items-center gap-7">
          {tabs.map((tab) => (
              <NavLink
                key={tab.to}
                to={tab.to}
                end={tab.end}
                className="text-sm font-medium transition-colors"
                style={({ isActive }) => ({
                  color: isActive ? 'var(--gold)' : 'rgba(239, 231, 214, 0.9)',
                })}
              >
                {tab.label}
              </NavLink>
            ))}
        </div>

        {/* Right: language */}
        <div className="shrink-0">
          <LanguageBar lang={lang} onChange={onChangeLang} />
        </div>

      </div>
    </nav>
  )
}
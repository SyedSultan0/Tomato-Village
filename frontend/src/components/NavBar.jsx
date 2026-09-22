import { NavLink } from 'react-router-dom'
import FarmerProfile from './FarmerProfile.jsx'
import LanguageBar from './LanguageBar.jsx'

export default function NavBar({ lang, onChangeLang, t }) {
  const tabs = [
    { to: '/farmer',  label: t.navFarmer },
    { to: '/officer', label: t.navOfficer },
    { to: '/map',     label: t.navMap },
  ]

  return (
    <header className="sticky top-0 z-40 backdrop-blur-md bg-white/80 border-b border-stone-200">
      <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between gap-4">

        {/* Left: brand + profile */}
        <div className="flex items-center gap-4 min-w-0">
          <div className="flex items-center gap-2 shrink-0">
            <span className="text-2xl">🌾</span>
            <div className="hidden sm:block">
              <div className="font-bold text-stone-800 leading-tight">
                {t.appName}
              </div>
              <div className="text-[11px] text-stone-500">
                {t.appTagline}
              </div>
            </div>
          </div>

          <div className="hidden md:block">
            <FarmerProfile t={t} />
          </div>
        </div>

        {/* Center: nav tabs (desktop) */}
        <nav className="hidden md:flex gap-1">
          {tabs.map((tab) => (
            <NavLink
              key={tab.to}
              to={tab.to}
              className={({ isActive }) =>
                `px-4 py-2 rounded-full text-sm font-medium transition ${
                  isActive
                    ? 'bg-emerald-600 text-white shadow-sm'
                    : 'text-stone-600 hover:bg-stone-100'
                }`
              }
            >
              {tab.label}
            </NavLink>
          ))}
        </nav>

        {/* Right: language */}
        <div className="shrink-0">
          <LanguageBar lang={lang} onChange={onChangeLang} />
        </div>

      </div>
    </header>
  )
}
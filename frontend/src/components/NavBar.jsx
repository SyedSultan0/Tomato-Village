import { NavLink } from 'react-router-dom'

export default function NavBar() {
  const tabs = [
    { to: '/farmer', label: '🌱 Farmer', icon: 'farmer' },
    { to: '/officer', label: '👮 Officer', icon: 'officer' },
    { to: '/map', label: '🗺 Map', icon: 'map' },
  ]

  return (
    <header className="border-b border-slate-800 bg-slate-900">
      <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-2xl">🍅</span>
          <div>
            <div className="font-bold text-lg">Tomato-Village</div>
            <div className="text-xs text-slate-500">
              Crop health intelligence
            </div>
          </div>
        </div>
        <nav className="flex gap-1">
          {tabs.map((tab) => (
            <NavLink
              key={tab.to}
              to={tab.to}
              className={({ isActive }) =>
                `px-4 py-2 rounded-md text-sm font-medium transition ${
                  isActive
                    ? 'bg-emerald-600 text-white'
                    : 'text-slate-300 hover:bg-slate-800'
                }`
              }
            >
              {tab.label}
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  )
}
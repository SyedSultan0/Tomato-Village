import { NavLink } from 'react-router-dom'

export default function MobileTabs({ t }) {
  const tabs = [
    { to: '/farmer',  label: t.navFarmer,  icon: '🌱' },
    { to: '/officer', label: t.navOfficer, icon: '👮' },
    { to: '/map',     label: t.navMap,     icon: '🗺️' },
  ]

  return (
    <nav
      className="md:hidden fixed bottom-0 left-0 right-0 z-40 border-t"
      style={{
        background: 'var(--green-deep)',
        borderColor: 'rgba(216, 179, 74, 0.2)',
      }}
    >
      <div className="grid grid-cols-3">
        {tabs.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            className="flex flex-col items-center justify-center py-2.5 text-[11px] transition-colors"
            style={({ isActive }) => ({
              color: isActive ? 'var(--gold)' : 'rgba(239, 231, 214, 0.75)',
              fontWeight: isActive ? 600 : 500,
            })}
          >
            <span className="text-lg mb-0.5">{tab.icon}</span>
            {tab.label}
          </NavLink>
        ))}
      </div>
    </nav>
  )
}
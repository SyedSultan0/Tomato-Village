export default function FarmerProfile({ t }) {
  const farmer = {
    name: 'Demo Farmer',
    village: 'Nashik',
    crop: 'Tomato',
  }

  return (
    <div
      className="flex items-center gap-2 rounded-full pl-1 pr-3 py-1"
      style={{
        border: '1px solid rgba(216, 179, 74, 0.2)',
        background: 'rgba(20, 42, 30, 0.4)',
      }}
    >
      <div
        className="w-7 h-7 rounded-full flex items-center justify-center text-sm"
        style={{ background: 'rgba(127, 166, 90, 0.25)' }}
      >
        👨‍🌾
      </div>
      <div className="leading-tight">
        <div className="text-xs font-semibold" style={{ color: 'var(--cream)' }}>
          {farmer.name}
        </div>
        <div className="text-[10px]" style={{ color: 'rgba(247, 242, 231, 0.6)' }}>
          📍 {farmer.village} · {farmer.crop}
        </div>
      </div>
    </div>
  )
}
// Simple farmer profile chip. In production this would be
// populated from an API and editable. For the demo it's static.

export default function FarmerProfile({ t }) {
  // TODO: read from backend once we have a GET /farmers/{id}
  const farmer = {
    name: 'Demo Farmer',
    village: 'Nashik',
    farm: 'Test Tomato Farm',
    crop: 'Tomato',
  }

  return (
    <div className="flex items-center gap-2 rounded-full border border-stone-200 bg-white pl-1 pr-3 py-1 shadow-sm">
      <div className="w-7 h-7 rounded-full bg-emerald-100 flex items-center justify-center text-sm">
        👨‍🌾
      </div>
      <div className="leading-tight">
        <div className="text-xs font-semibold text-stone-800">
          {farmer.name}
        </div>
        <div className="text-[10px] text-stone-500">
          📍 {farmer.village} · {farmer.crop}
        </div>
      </div>
    </div>
  )
}
export default function LoadingSpinner({ label = 'Loading…' }) {
  return (
    <div className="flex items-center justify-center gap-3 py-8 text-stone-500">
      <div className="w-5 h-5 border-2 border-stone-300 border-t-emerald-600 rounded-full animate-spin" />
      <span className="text-sm">{label}</span>
    </div>
  )
}
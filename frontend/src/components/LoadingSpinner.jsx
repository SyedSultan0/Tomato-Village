export default function LoadingSpinner({ label = 'Loading…' }) {
  return (
    <div className="flex items-center justify-center gap-3 py-8 text-slate-400">
      <div className="w-5 h-5 border-2 border-slate-500 border-t-emerald-500 rounded-full animate-spin" />
      <span className="text-sm">{label}</span>
    </div>
  )
}
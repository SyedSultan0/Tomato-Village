import LoadingSpinner from '../components/LoadingSpinner.jsx'
import ErrorBox from '../components/ErrorBox.jsx'

export default function FarmerView() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-2">🌱 Farmer</h1>
      <p className="text-slate-400 mb-6">
        Upload a leaf photo to get a diagnosis, risk assessment,
        and sourced advisory.
      </p>

      <div className="rounded-lg border border-slate-800 bg-slate-900 p-6">
        <p className="text-slate-500">
          🚧 Farmer view is being built — coming in the next session.
        </p>
      </div>
    </div>
  )
}
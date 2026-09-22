import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from 'react-leaflet'
import { getHotspots } from '../api.js'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import ErrorBox from '../components/ErrorBox.jsx'

/* ------------------------------------------------------------------
 *  MapView
 *
 *  Leaflet map of Maharashtra with hotspot pins.
 *  Pins come from GET /hotspots.
 *
 *  Pin color = max risk level in the cluster.
 *  Pin radius = proportional to report count.
 *  Click = popup with cluster details.
 * ------------------------------------------------------------------ */

// Maharashtra center (approx)
const MH_CENTER = [19.75, 75.71]
const MH_ZOOM = 6

const CONDITION_OPTIONS = [
  { value: '', label: 'All conditions' },
  { value: 'Late Blight', label: 'Late Blight' },
  { value: 'Early Blight', label: 'Early Blight' },
  { value: 'Leaf Miner', label: 'Leaf Miner' },
  { value: 'Spotted Wilt Virus', label: 'Spotted Wilt Virus' },
  { value: 'Magnesium Deficiency', label: 'Magnesium Deficiency' },
  { value: 'Nitrogen Deficiency', label: 'Nitrogen Deficiency' },
  { value: 'Potassium Deficiency', label: 'Potassium Deficiency' },
  { value: 'Healthy', label: 'Healthy' },
]

export default function MapView() {

  const [hotspots, setHotspots] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [condition, setCondition] = useState('')
  const [days, setDays] = useState(14)
  const [minReports, setMinReports] = useState(3)
  const [radiusKm, setRadiusKm] = useState(5)

  const [selected, setSelected] = useState(null)

  useEffect(() => {
    let cancelled = false

    async function load() {
      setLoading(true)
      setError(null)
      try {
        const params = { days, min_reports: minReports, radius_km: radiusKm }
        if (condition) params.condition = condition

        const { data } = await getHotspots(params)
        if (!cancelled) setHotspots(data.hotspots || [])
      } catch (err) {
        if (!cancelled) {
          setError(err.response?.data?.detail || err.message || 'Failed to load hotspots.')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => { cancelled = true }
  }, [condition, days, minReports, radiusKm])

  return (
    <div className="max-w-6xl mx-auto px-4 py-6 space-y-4">

      <header>
        <h1 className="text-2xl font-bold mb-1">🗺 Hotspot Map</h1>
        <p className="text-slate-400 text-sm">
          Regional outbreak signals across Maharashtra. Each pin is a
          cluster of same-condition reports.
        </p>
      </header>

      {/* Filters */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <label className="block">
          <span className="block text-xs text-slate-400 mb-1">Condition</span>
          <select
            value={condition}
            onChange={(e) => setCondition(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-2 text-sm"
          >
            {CONDITION_OPTIONS.map((c) => (
              <option key={c.value} value={c.value}>{c.label}</option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="block text-xs text-slate-400 mb-1">Time window (days)</span>
          <input
            type="number" min="1" max="90"
            value={days}
            onChange={(e) => setDays(Number(e.target.value) || 14)}
            className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-2 text-sm"
          />
        </label>

        <label className="block">
          <span className="block text-xs text-slate-400 mb-1">Min reports</span>
          <input
            type="number" min="2" max="20"
            value={minReports}
            onChange={(e) => setMinReports(Number(e.target.value) || 3)}
            className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-2 text-sm"
          />
        </label>

        <label className="block">
          <span className="block text-xs text-slate-400 mb-1">Radius (km)</span>
          <input
            type="number" min="1" max="100"
            value={radiusKm}
            onChange={(e) => setRadiusKm(Number(e.target.value) || 5)}
            className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-2 text-sm"
          />
        </label>
      </div>

      <ErrorBox message={error} />

      {/* Map + side panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        <div className="lg:col-span-2 rounded-lg border border-slate-800 overflow-hidden">
          <div className="h-[500px]">
            <MapContainer
              center={MH_CENTER}
              zoom={MH_ZOOM}
              style={{ height: '100%', width: '100%' }}
            >
              <TileLayer
                attribution='&copy; OpenStreetMap'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />

              {hotspots.map((h, idx) => (
                <CircleMarker
                  key={idx}
                  center={[h.center.latitude, h.center.longitude]}
                  radius={pinRadius(h.report_count)}
                  pathOptions={pinStyle(h.max_risk_level)}
                  eventHandlers={{
                    click: () => setSelected(h),
                  }}
                >
                  <Popup>
                    <div className="text-xs">
                      <div className="font-bold mb-1">
                        {h.condition}
                      </div>
                      <div>{h.report_count} cases · {h.radius_km} km</div>
                      <div className="text-slate-500">
                        {h.districts?.join(', ') || '—'}
                      </div>
                    </div>
                  </Popup>
                </CircleMarker>
              ))}
            </MapContainer>
          </div>
        </div>

        <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
          {loading ? (
            <LoadingSpinner label="Loading hotspots…" />
          ) : selected ? (
            <HotspotDetail hotspot={selected} onClear={() => setSelected(null)} />
          ) : (
            <div className="text-sm text-slate-400 space-y-3">
              <div className="font-semibold text-slate-200">
                {hotspots.length} hotspot{hotspots.length === 1 ? '' : 's'}
              </div>
              <p>
                Click a pin on the map to see cluster details.
              </p>

              <div className="pt-3 border-t border-slate-800">
                <div className="text-xs uppercase tracking-wide text-slate-500 mb-2">
                  Legend
                </div>
                <ul className="space-y-1 text-xs">
                  <li className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full" style={{ background: '#22c55e' }} />
                    LOW
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full" style={{ background: '#eab308' }} />
                    MODERATE
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full" style={{ background: '#f97316' }} />
                    HIGH
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full" style={{ background: '#ef4444' }} />
                    CRITICAL
                  </li>
                </ul>
              </div>
            </div>
          )}
        </div>

      </div>

    </div>
  )
}

/* ------------------------------------------------------------------
 *  Detail panel
 * ------------------------------------------------------------------ */

function HotspotDetail({ hotspot, onClear }) {
  const h = hotspot

  return (
    <div className="text-sm space-y-3">
      <div className="flex items-start justify-between">
        <div>
          <div className="font-bold text-slate-100 text-base">{h.condition}</div>
          <div className="text-xs text-slate-500">
            {h.districts?.join(', ') || '—'}
          </div>
        </div>
        <button
          onClick={onClear}
          className="text-slate-500 hover:text-slate-300 text-lg"
          title="Clear"
        >
          ×
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <Stat label="Reports" value={h.report_count} />
        <Stat label="Radius" value={`${h.radius_km} km`} />
        <Stat label="Farms" value={h.farm_ids?.length || 0} />
        <Stat label="Max risk" value={h.max_risk_level || '—'} />
      </div>

      <div className="pt-2 border-t border-slate-800">
        <div className="text-xs uppercase tracking-wide text-slate-500 mb-2">
          Time range
        </div>
        <div className="text-xs text-slate-300">
          {formatDate(h.earliest_report)} → {formatDate(h.latest_report)}
        </div>
      </div>

      {h.farms?.length > 0 && (
        <div className="pt-2 border-t border-slate-800">
          <div className="text-xs uppercase tracking-wide text-slate-500 mb-2">
            Farms in this cluster
          </div>
          <ul className="space-y-2">
            {h.farms.map((farm) => (
              <li
                key={farm.farm_id}
                className="rounded-md bg-slate-950 border border-slate-800 p-2"
              >
                <div className="text-xs font-semibold text-slate-100">
                  {farm.farm_name}
                </div>
                <div className="text-[11px] text-slate-400 mt-0.5">
                  {farm.crop_name || '—'}
                  {farm.farmer_name ? ` · ${farm.farmer_name}` : ''}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="pt-2 border-t border-slate-800">
        <div className="text-xs uppercase tracking-wide text-slate-500 mb-2">
          Report IDs
        </div>
        <div className="text-xs text-slate-400">
          {h.report_ids?.join(', ') || '—'}
        </div>
      </div>
    </div>
  )
}

function Stat({ label, value }) {
  return (
    <div className="rounded-md bg-slate-950 border border-slate-800 px-3 py-2">
      <div className="text-[10px] uppercase tracking-wide text-slate-500">
        {label}
      </div>
      <div className="text-sm font-semibold text-slate-100">
        {value}
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------
 *  Helpers
 * ------------------------------------------------------------------ */

function pinRadius(count) {
  // 8–20 based on report count
  const base = 8
  const scaled = Math.min(12, count * 2)
  return base + scaled
}

function pinStyle(level) {
  const color = colorForRisk(level)
  return {
    color: color,
    fillColor: color,
    fillOpacity: 0.5,
    weight: 2,
  }
}

function colorForRisk(level) {
  switch ((level || '').toUpperCase()) {
    case 'LOW':      return '#22c55e'
    case 'MODERATE': return '#eab308'
    case 'HIGH':     return '#f97316'
    case 'CRITICAL': return '#ef4444'
    default:         return '#64748b'
  }
}

function formatDate(value) {
  if (!value) return '—'
  try {
    const d = new Date(value)
    return d.toLocaleDateString()
  } catch {
    return '—'
  }
}
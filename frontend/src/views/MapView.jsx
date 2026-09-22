import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet'
import { getHotspots } from '../api.js'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import ErrorBox from '../components/ErrorBox.jsx'

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

export default function MapView({ t, lang }) {

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
    <div className="wrap py-8 md:py-12 space-y-6">

      <header>
        <h1
          className="font-bold mb-2"
          style={{ fontFamily: 'Fraunces, serif', fontSize: 32, color: 'var(--soil)' }}
        >
          🗺 {t?.mapHeading || 'Hotspot Map'}
        </h1>
        <p style={{ color: 'rgba(74,53,38,0.7)', fontSize: 15 }}>
          {t?.mapSub || 'Regional outbreak signals across Maharashtra. Each pin is a cluster of same-condition reports.'}
        </p>
      </header>

      {/* Filters */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <label className="block">
          <span className="label">{t?.condition || 'Condition'}</span>
          <select
            value={condition}
            onChange={(e) => setCondition(e.target.value)}
            className="input"
          >
            {CONDITION_OPTIONS.map((c) => (
              <option key={c.value} value={c.value}>{c.label}</option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="label">{t?.timeWindow || 'Time window (days)'}</span>
          <input
            type="number" min="1" max="90"
            value={days}
            onChange={(e) => setDays(Number(e.target.value) || 14)}
            className="input"
          />
        </label>

        <label className="block">
          <span className="label">{t?.minReports || 'Min reports'}</span>
          <input
            type="number" min="2" max="20"
            value={minReports}
            onChange={(e) => setMinReports(Number(e.target.value) || 3)}
            className="input"
          />
        </label>

        <label className="block">
          <span className="label">{t?.radiusKm || 'Radius (km)'}</span>
          <input
            type="number" min="1" max="100"
            value={radiusKm}
            onChange={(e) => setRadiusKm(Number(e.target.value) || 5)}
            className="input"
          />
        </label>
      </div>

      <ErrorBox message={error} />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        <div
          className="lg:col-span-2 overflow-hidden"
          style={{
            borderRadius: 20,
            border: '1px solid var(--cream-dim)',
          }}
        >
          <div style={{ height: 500 }}>
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
                  eventHandlers={{ click: () => setSelected(h) }}
                >
                  <Popup>
                    <div className="text-xs">
                      <div className="font-bold mb-1">{h.condition}</div>
                      <div>{h.report_count} cases · {h.radius_km} km</div>
                      <div style={{ color: '#6b6b6b' }}>
                        {h.districts?.join(', ') || '—'}
                      </div>
                    </div>
                  </Popup>
                </CircleMarker>
              ))}
            </MapContainer>
          </div>
        </div>

        <div className="card p-4">
          {loading ? (
            <LoadingSpinner label={t?.loading || 'Loading hotspots…'} />
          ) : selected ? (
            <HotspotDetail hotspot={selected} onClear={() => setSelected(null)} />
          ) : (
            <div className="text-sm space-y-3" style={{ color: 'rgba(74,53,38,0.75)' }}>
              <div className="font-semibold" style={{ color: 'var(--soil)', fontSize: 15 }}>
                {hotspots.length} hotspot{hotspots.length === 1 ? '' : 's'}
              </div>
              <p>
                {t?.clickPin || 'Click a pin on the map to see cluster details.'}
              </p>

              <div className="pt-3" style={{ borderTop: '1px solid var(--cream-dim)' }}>
                <div
                  className="text-xs uppercase tracking-wider mb-2 font-semibold"
                  style={{ color: 'rgba(74,53,38,0.55)' }}
                >
                  {t?.legend || 'Legend'}
                </div>
                <ul className="space-y-1 text-xs">
                  <li className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full" style={{ background: '#3F6B4A' }} />
                    LOW
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full" style={{ background: '#D8B34A' }} />
                    MODERATE
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full" style={{ background: '#C97A2B' }} />
                    HIGH
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full" style={{ background: '#C1442D' }} />
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
          <div
            className="font-bold text-base"
            style={{ fontFamily: 'Fraunces, serif', color: 'var(--soil)' }}
          >
            {h.condition}
          </div>
          <div className="text-xs" style={{ color: 'rgba(74,53,38,0.55)' }}>
            {h.districts?.join(', ') || '—'}
          </div>
        </div>
        <button
          onClick={onClear}
          className="text-lg leading-none transition-opacity hover:opacity-60"
          style={{ color: 'var(--soil)' }}
          title="Clear"
        >
          ×
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <Stat label="Reports"  value={h.report_count} />
        <Stat label="Radius"   value={`${h.radius_km} km`} />
        <Stat label="Farms"    value={h.farm_ids?.length || 0} />
        <Stat label="Max risk" value={h.max_risk_level || '—'} />
      </div>

      <div className="pt-2" style={{ borderTop: '1px solid var(--cream-dim)' }}>
        <div
          className="text-xs uppercase tracking-wider mb-2 font-semibold"
          style={{ color: 'rgba(74,53,38,0.55)' }}
        >
          Time range
        </div>
        <div className="text-xs" style={{ color: 'var(--soil)' }}>
          {formatDate(h.earliest_report)} → {formatDate(h.latest_report)}
        </div>
      </div>

      {h.farms?.length > 0 && (
        <div className="pt-2" style={{ borderTop: '1px solid var(--cream-dim)' }}>
          <div
            className="text-xs uppercase tracking-wider mb-2 font-semibold"
            style={{ color: 'rgba(74,53,38,0.55)' }}
          >
            Farms in this cluster
          </div>
          <ul className="space-y-2">
            {h.farms.map((farm) => (
              <li
                key={farm.farm_id}
                className="p-2 rounded-xl"
                style={{
                  background: 'var(--cream)',
                  border: '1px solid var(--cream-dim)',
                }}
              >
                <div className="text-xs font-semibold" style={{ color: 'var(--soil)' }}>
                  {farm.farm_name}
                </div>
                <div className="text-[11px] mt-0.5" style={{ color: 'rgba(74,53,38,0.65)' }}>
                  {farm.crop_name || '—'}
                  {farm.farmer_name ? ` · ${farm.farmer_name}` : ''}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="pt-2" style={{ borderTop: '1px solid var(--cream-dim)' }}>
        <div
          className="text-xs uppercase tracking-wider mb-2 font-semibold"
          style={{ color: 'rgba(74,53,38,0.55)' }}
        >
          Report IDs
        </div>
        <div className="text-xs" style={{ color: 'rgba(74,53,38,0.65)' }}>
          {h.report_ids?.join(', ') || '—'}
        </div>
      </div>

    </div>
  )
}

function Stat({ label, value }) {
  return (
    <div
      className="rounded-xl px-3 py-2"
      style={{
        background: 'var(--cream)',
        border: '1px solid var(--cream-dim)',
      }}
    >
      <div
        className="text-[10px] uppercase tracking-wider font-semibold"
        style={{ color: 'rgba(74,53,38,0.55)' }}
      >
        {label}
      </div>
      <div className="text-sm font-semibold" style={{ color: 'var(--soil)' }}>
        {value}
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------
 *  Helpers
 * ------------------------------------------------------------------ */

function pinRadius(count) {
  const base = 8
  const scaled = Math.min(12, count * 2)
  return base + scaled
}

function pinStyle(level) {
  const color = colorForRisk(level)
  return {
    color: color,
    fillColor: color,
    fillOpacity: 0.55,
    weight: 2,
  }
}

function colorForRisk(level) {
  switch ((level || '').toUpperCase()) {
    case 'LOW':      return '#3F6B4A'
    case 'MODERATE': return '#D8B34A'
    case 'HIGH':     return '#C97A2B'
    case 'CRITICAL': return '#C1442D'
    default:         return '#8F8A7D'
  }
}

function formatDate(value) {
  if (!value) return '—'
  try {
    return new Date(value).toLocaleDateString()
  } catch {
    return '—'
  }
}
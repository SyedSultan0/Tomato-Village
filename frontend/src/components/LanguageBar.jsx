import { LANGUAGES } from '../i18n.js'

export default function LanguageBar({ lang, onChange }) {
  return (
    <div className="flex items-center gap-1 rounded-full border border-stone-200 bg-white px-1 py-1 shadow-sm">
      {LANGUAGES.map((l) => (
        <button
          key={l.code}
          onClick={() => onChange(l.code)}
          title={l.label}
          className={
            'px-2.5 py-1 text-xs rounded-full transition ' +
            (lang === l.code
              ? 'bg-stone-800 text-white font-medium'
              : 'text-stone-600 hover:bg-stone-100')
          }
        >
          {l.native}
        </button>
      ))}
    </div>
  )
}
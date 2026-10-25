import { scaleLabel } from '../labels'

interface Props {
  name: string
  value: number | null
  onChange: (v: number) => void
  disabled?: boolean
}

export default function ScoreSelector({ name, value, onChange, disabled }: Props) {
  return (
    <div>
      <div role="group" aria-label={`Nota de ${name}`} className="flex flex-wrap gap-1">
        {Array.from({ length: 11 }, (_, n) => (
          <button
            key={n}
            type="button"
            disabled={disabled}
            aria-pressed={value === n}
            onClick={() => onChange(n)}
            className={`h-9 w-9 rounded border text-sm font-medium transition ${
              value === n
                ? 'border-indigo-600 bg-indigo-600 text-white'
                : 'border-slate-300 bg-white hover:bg-indigo-50'
            } disabled:cursor-not-allowed disabled:opacity-70`}
          >
            {n}
          </button>
        ))}
      </div>
      <p className="mt-1 h-5 text-sm text-slate-500">{value === null ? 'Sem nota' : scaleLabel(value)}</p>
    </div>
  )
}

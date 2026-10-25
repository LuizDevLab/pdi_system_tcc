import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listMine, type EvaluationMine } from '../api'
import { STATUS_LABEL, TYPE_LABEL } from '../labels'

const STATUS_STYLE: Record<string, string> = {
  pendente: 'bg-slate-100 text-slate-700',
  rascunho: 'bg-amber-100 text-amber-800',
  completo: 'bg-green-100 text-green-800',
}

function LinkCard({ link }: { link: EvaluationMine }) {
  const title = link.type === 'auto' ? TYPE_LABEL.auto : link.evaluated_name
  const subtitle = link.type === 'auto' ? 'Avalie suas próprias competências' : TYPE_LABEL[link.type]
  const action = link.status === 'completo' ? 'Ver' : link.status === 'rascunho' ? 'Continuar' : 'Iniciar'
  return (
    <li className="flex items-center justify-between gap-3 rounded-lg bg-white p-4 shadow-sm">
      <div className="min-w-0">
        <p className="truncate font-medium">{title}</p>
        <p className="text-sm text-slate-500">{subtitle}</p>
      </div>
      <div className="flex shrink-0 items-center gap-3">
        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLE[link.status] ?? ''}`}>
          {STATUS_LABEL[link.status] ?? link.status}
        </span>
        <Link
          to={`/avaliacao/${link.id}`}
          className="rounded border border-indigo-600 px-3 py-1 text-sm text-indigo-700 hover:bg-indigo-50"
        >
          {action}
        </Link>
      </div>
    </li>
  )
}

export default function MyEvaluations() {
  const [links, setLinks] = useState<EvaluationMine[] | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    listMine()
      .then(setLinks)
      .catch((e: Error) => setError(e.message))
  }, [])

  const auto = links?.filter((l) => l.type === 'auto') ?? []
  const others = links?.filter((l) => l.type !== 'auto') ?? []

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Minhas avaliações</h1>
      {error && (
        <p role="alert" className="rounded bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}
      {links === null && !error && <p className="text-slate-500">Carregando…</p>}
      {links?.length === 0 && <p className="text-slate-500">Você não tem avaliações para responder.</p>}
      {auto.length > 0 && (
        <section className="space-y-2">
          <h2 className="font-medium text-slate-600">Autoavaliação</h2>
          <ul className="space-y-2">
            {auto.map((l) => (
              <LinkCard key={l.id} link={l} />
            ))}
          </ul>
        </section>
      )}
      {others.length > 0 && (
        <section className="space-y-2">
          <h2 className="font-medium text-slate-600">Avaliações que eu faço</h2>
          <ul className="space-y-2">
            {others.map((l) => (
              <LinkCard key={l.id} link={l} />
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}

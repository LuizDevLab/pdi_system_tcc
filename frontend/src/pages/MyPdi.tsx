import { useEffect, useState } from 'react'
import { Legend, PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart, ResponsiveContainer } from 'recharts'
import { getPdi, type Pdi } from '../api'
import { useAuth } from '../auth'
import { DEV_TYPES, TIMEFRAMES } from '../labels'

const fmt = (n: number) => n.toFixed(2).replace('.', ',')

export default function MyPdi() {
  const { user } = useAuth()
  const [pdi, setPdi] = useState<Pdi | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!user) return
    getPdi(user.id)
      .then(setPdi)
      .catch((e: Error) => setError(e.message))
  }, [user])

  if (error) {
    return (
      <p role="alert" className="rounded bg-red-50 px-3 py-2 text-sm text-red-700">
        {error}
      </p>
    )
  }
  if (!pdi) return <p className="text-slate-500">Carregando…</p>

  const radarData = pdi.competencies.map((c) => ({
    name: c.name,
    Consolidado: Number(c.consolidated.toFixed(2)),
    [pdi.cargo ?? 'Cargo']: c.expected,
  }))

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Meu PDI</h1>
        <p className="text-sm text-slate-500">
          {pdi.cargo} · gerado em {new Date(pdi.generated_at).toLocaleDateString('pt-BR')}
        </p>
      </div>

      {pdi.reference_provisional && (
        <p role="note" className="rounded border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          Atenção: o perfil de referência deste cargo é provisório. Os resultados podem mudar quando ele for
          definido.
        </p>
      )}

      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-lg bg-white p-4 shadow-sm">
          <p className="text-sm text-slate-500">Similaridade de cosseno</p>
          <p className="text-2xl font-semibold">{fmt(pdi.cosine)}</p>
        </div>
        <div className="rounded-lg bg-white p-4 shadow-sm">
          <p className="text-sm text-slate-500">Índice de Jaccard</p>
          <p className="text-2xl font-semibold">{fmt(pdi.jaccard)}</p>
        </div>
      </div>

      <section className="rounded-lg bg-white p-4 shadow-sm">
        <h2 className="mb-2 font-medium">Seu perfil vs. o perfil do cargo</h2>
        <div className="h-[460px]">
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart data={radarData} outerRadius="65%">
              <PolarGrid />
              <PolarAngleAxis dataKey="name" tick={{ fontSize: 10 }} />
              <PolarRadiusAxis domain={[0, 10]} tickCount={6} tick={{ fontSize: 10 }} />
              <Radar dataKey="Consolidado" stroke="#4f46e5" fill="#4f46e5" fillOpacity={0.35} />
              <Radar
                dataKey={pdi.cargo ?? 'Cargo'}
                stroke="#64748b"
                strokeDasharray="4 3"
                fill="#64748b"
                fillOpacity={0.1}
              />
              <Legend />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="font-medium">Competências a desenvolver</h2>
        {pdi.items.length === 0 && (
          <p className="text-slate-500">Nenhuma lacuna relevante: seu perfil atende ao esperado para o cargo.</p>
        )}
        <ol className="space-y-3">
          {pdi.items.map((it) => (
            <li key={it.code} className="rounded-lg bg-white p-4 shadow-sm">
              <div className="flex items-baseline justify-between gap-3">
                <p className="font-medium">
                  {it.rank}. {it.name}
                </p>
                <span className="shrink-0 text-sm text-slate-500">Lacuna: {fmt(it.gap)}</span>
              </div>
              {it.action ? (
                <div className="mt-2 text-sm">
                  <p>
                    <span className="font-medium">{it.action.title}</span>{' '}
                    <span className="text-slate-500">({DEV_TYPES[it.action.type] ?? it.action.type})</span>
                  </p>
                  <p className="text-slate-600">{it.action.description}</p>
                </div>
              ) : (
                <p className="mt-2 text-sm text-slate-500">Sem ação sugerida no catálogo.</p>
              )}
              {it.timeframe && (
                <p className="mt-2 text-sm text-slate-600">Prazo: {TIMEFRAMES[it.timeframe] ?? it.timeframe}</p>
              )}
            </li>
          ))}
        </ol>
      </section>
    </div>
  )
}

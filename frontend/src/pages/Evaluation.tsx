import { useEffect, useState, type ReactNode } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  getEvaluation,
  saveDraft,
  submitEvaluation,
  type DevelopmentInput,
  type EvaluationDetail,
  type ScoreItem,
} from '../api'
import ScoreSelector from '../components/ScoreSelector'
import { DEV_TYPES, SCALE, STAY_IN_ROLE, STATUS_LABEL, TIMEFRAMES, TYPE_LABEL } from '../labels'

const MAX_NEEDS = 5
const inputCls = 'mt-1 w-full rounded border border-slate-300 px-3 py-2 disabled:bg-slate-100'

function Alert({ kind, children }: { kind: 'error' | 'ok'; children: ReactNode }) {
  const cls = kind === 'error' ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-800'
  return (
    <div role={kind === 'error' ? 'alert' : 'status'} className={`rounded px-3 py-2 text-sm ${cls}`}>
      {children}
    </div>
  )
}

export default function Evaluation() {
  const { linkId } = useParams()
  const id = Number(linkId)
  const [detail, setDetail] = useState<EvaluationDetail | null>(null)
  const [scores, setScores] = useState<Record<string, number | null>>({})
  const [dev, setDev] = useState<DevelopmentInput>({})
  const [loadError, setLoadError] = useState('')
  const [errors, setErrors] = useState<string[]>([])
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!Number.isInteger(id)) {
      setLoadError('Avaliação inválida.')
      return
    }
    getEvaluation(id)
      .then((d) => {
        setDetail(d)
        setScores(Object.fromEntries(d.competencies.map((c) => [c.code, c.score])))
        setDev(d.development_input ?? {})
      })
      .catch((e: Error) => setLoadError(e.message))
  }, [id])

  if (loadError)
    return (
      <div className="space-y-4">
        <Alert kind="error">{loadError}</Alert>
        <Link to="/minhas-avaliacoes" className="text-indigo-700 underline">
          Voltar
        </Link>
      </div>
    )
  if (!detail) return <p className="text-slate-500">Carregando…</p>

  const readOnly = detail.status === 'completo'
  const isAuto = detail.type === 'auto'
  const needs = dev.needs ?? []
  const nameOf = (code: string) => detail.competencies.find((c) => c.code === code)?.name ?? code

  const patch = (p: Partial<DevelopmentInput>) => {
    setDev((d) => ({ ...d, ...p }))
    setNotice('')
  }

  const toggle = (list: string[], value: string) =>
    list.includes(value) ? list.filter((v) => v !== value) : [...list, value]

  const toggleNeed = (code: string) => {
    const next = toggle(needs, code)
    patch({
      needs: next,
      priority_competency: next.includes(dev.priority_competency ?? '') ? dev.priority_competency : undefined,
    })
  }

  const scoreItems = (): ScoreItem[] =>
    detail.competencies.flatMap((c) => {
      const s = scores[c.code]
      return s === null || s === undefined ? [] : [{ competency_code: c.code, score: s }]
    })

  // Só envia campos preenchidos; a prioridade só vale se estiver entre as necessidades.
  const devPayload = (): DevelopmentInput => {
    const out: DevelopmentInput = { needs }
    if (dev.priority_competency && needs.includes(dev.priority_competency))
      out.priority_competency = dev.priority_competency
    if (dev.priority_reason?.trim()) out.priority_reason = dev.priority_reason
    if (isAuto) {
      if (dev.main_goal?.trim()) out.main_goal = dev.main_goal
      if (dev.stay_in_role) out.stay_in_role = dev.stay_in_role
      if (dev.future_role?.trim()) out.future_role = dev.future_role
      if (dev.dev_types?.length) out.dev_types = dev.dev_types
      if (dev.timeframe) out.timeframe = dev.timeframe
    }
    return out
  }

  const validate = (): string[] => {
    const problems: string[] = []
    const missing = detail.competencies.length - scoreItems().length
    if (missing > 0) problems.push(`Faltam ${missing} nota(s): todas as 20 competências precisam de nota (0 é válido).`)
    if (needs.length < 1) problems.push('Escolha ao menos uma necessidade de desenvolvimento.')
    if (!dev.priority_competency || !needs.includes(dev.priority_competency))
      problems.push('Escolha a competência prioritária entre as necessidades.')
    if (!dev.priority_reason?.trim()) problems.push('Explique o motivo da prioridade.')
    if (isAuto) {
      if (!dev.main_goal?.trim()) problems.push('Informe seu principal objetivo.')
      if (!dev.stay_in_role) problems.push('Informe se pretende permanecer no cargo.')
      if (!dev.dev_types?.length) problems.push('Escolha ao menos um tipo de desenvolvimento.')
      if (!dev.timeframe) problems.push('Escolha o prazo desejado.')
    }
    return problems
  }

  const run = async (action: () => Promise<EvaluationDetail>, okMessage: string) => {
    setBusy(true)
    setErrors([])
    setNotice('')
    try {
      const d = await action()
      setDetail(d)
      setNotice(okMessage)
      window.scrollTo({ top: 0, behavior: 'smooth' })
    } catch (e) {
      setErrors([e instanceof Error ? e.message : 'Erro ao enviar.'])
    } finally {
      setBusy(false)
    }
  }

  const onSave = () => run(() => saveDraft(id, scoreItems(), devPayload()), 'Rascunho salvo.')

  const onSubmit = () => {
    const problems = validate()
    if (problems.length) {
      setErrors(problems)
      setNotice('')
      window.scrollTo({ top: 0, behavior: 'smooth' })
      return
    }
    if (!window.confirm('Depois de enviada, a avaliação não poderá ser editada. Enviar agora?')) return
    run(() => submitEvaluation(id, scoreItems(), devPayload()), 'Avaliação enviada com sucesso.')
  }

  const title = isAuto ? 'Autoavaliação' : `Avaliação de ${detail.evaluated_name}`

  return (
    <div className="space-y-6">
      <div>
        <Link to="/minhas-avaliacoes" className="text-sm text-indigo-700 underline">
          ← Minhas avaliações
        </Link>
        <h1 className="mt-2 text-xl font-semibold">{title}</h1>
        <p className="text-sm text-slate-500">
          {TYPE_LABEL[detail.type]} · {STATUS_LABEL[detail.status]}
        </p>
      </div>

      {notice && <Alert kind="ok">{notice}</Alert>}
      {errors.length > 0 && (
        <Alert kind="error">
          <ul className="list-disc space-y-1 pl-5">
            {errors.map((m) => (
              <li key={m}>{m}</li>
            ))}
          </ul>
        </Alert>
      )}
      {readOnly && <Alert kind="ok">Esta avaliação já foi enviada e não pode mais ser editada.</Alert>}

      <section className="rounded-lg bg-white p-4 text-sm shadow-sm">
        <p className="mb-2 font-medium">Escala de 0 a 10</p>
        <ul className="grid grid-cols-2 gap-x-4 gap-y-1 sm:grid-cols-3">
          {SCALE.map((s) => (
            <li key={s.range}>
              <strong>{s.range}</strong> {s.label}
            </li>
          ))}
        </ul>
      </section>

      <section className="space-y-3">
        <h2 className="font-medium text-slate-600">Competências</h2>
        {detail.competencies.map((c) => (
          <div key={c.code} className="rounded-lg bg-white p-4 shadow-sm">
            <p className="font-medium">{c.name}</p>
            <p className="mb-3 text-sm text-slate-500">{c.description}</p>
            <ScoreSelector
              name={c.name}
              value={scores[c.code] ?? null}
              disabled={readOnly}
              onChange={(v) => {
                setScores((s) => ({ ...s, [c.code]: v }))
                setNotice('')
              }}
            />
          </div>
        ))}
      </section>

      <section className="space-y-4 rounded-lg bg-white p-4 shadow-sm">
        <h2 className="font-medium text-slate-600">{isAuto ? 'Necessidades e objetivos' : 'Necessidades do avaliado'}</h2>

        {isAuto && (
          <label className="block text-sm">
            Qual é o seu principal objetivo profissional?
            <textarea
              rows={3}
              disabled={readOnly}
              value={dev.main_goal ?? ''}
              onChange={(e) => patch({ main_goal: e.target.value })}
              className={inputCls}
            />
          </label>
        )}

        <fieldset className="text-sm" disabled={readOnly}>
          <legend>
            {isAuto ? 'Em quais competências você precisa se desenvolver?' : 'Em quais competências o avaliado precisa se desenvolver?'}{' '}
            <span className="text-slate-500">
              (até {MAX_NEEDS}; selecionadas: {needs.length})
            </span>
          </legend>
          <div className="mt-2 grid gap-1 sm:grid-cols-2">
            {detail.competencies.map((c) => (
              <label key={c.code} className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={needs.includes(c.code)}
                  disabled={!needs.includes(c.code) && needs.length >= MAX_NEEDS}
                  onChange={() => toggleNeed(c.code)}
                />
                {c.name}
              </label>
            ))}
          </div>
        </fieldset>

        <label className="block text-sm">
          Competência prioritária
          <select
            disabled={readOnly || needs.length === 0}
            value={dev.priority_competency ?? ''}
            onChange={(e) => patch({ priority_competency: e.target.value || undefined })}
            className={inputCls}
          >
            <option value="">{needs.length === 0 ? 'Escolha as necessidades primeiro' : 'Selecione…'}</option>
            {needs.map((code) => (
              <option key={code} value={code}>
                {nameOf(code)}
              </option>
            ))}
          </select>
        </label>

        <label className="block text-sm">
          Por que esta é a prioridade?
          <textarea
            rows={3}
            disabled={readOnly}
            value={dev.priority_reason ?? ''}
            onChange={(e) => patch({ priority_reason: e.target.value })}
            className={inputCls}
          />
        </label>

        {isAuto && (
          <>
            <fieldset className="text-sm" disabled={readOnly}>
              <legend>Pretende permanecer no cargo atual?</legend>
              <div className="mt-1 flex flex-wrap gap-4">
                {Object.entries(STAY_IN_ROLE).map(([value, label]) => (
                  <label key={value} className="flex items-center gap-2">
                    <input
                      type="radio"
                      name="stay_in_role"
                      checked={dev.stay_in_role === value}
                      onChange={() => patch({ stay_in_role: value })}
                    />
                    {label}
                  </label>
                ))}
              </div>
            </fieldset>

            <label className="block text-sm">
              Cargo futuro desejado <span className="text-slate-500">(opcional)</span>
              <input
                type="text"
                disabled={readOnly}
                value={dev.future_role ?? ''}
                onChange={(e) => patch({ future_role: e.target.value })}
                className={inputCls}
              />
            </label>

            <fieldset className="text-sm" disabled={readOnly}>
              <legend>Que tipos de desenvolvimento você prefere?</legend>
              <div className="mt-2 grid gap-1 sm:grid-cols-2">
                {Object.entries(DEV_TYPES).map(([value, label]) => (
                  <label key={value} className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={dev.dev_types?.includes(value) ?? false}
                      onChange={() => patch({ dev_types: toggle(dev.dev_types ?? [], value) })}
                    />
                    {label}
                  </label>
                ))}
              </div>
            </fieldset>

            <label className="block text-sm">
              Em quanto tempo quer desenvolver a competência prioritária?
              <select
                disabled={readOnly}
                value={dev.timeframe ?? ''}
                onChange={(e) => patch({ timeframe: e.target.value || undefined })}
                className={inputCls}
              >
                <option value="">Selecione…</option>
                {Object.entries(TIMEFRAMES).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
          </>
        )}
      </section>

      {!readOnly && (
        <div className="flex flex-wrap gap-3 pb-8">
          <button
            onClick={onSave}
            disabled={busy}
            className="rounded border border-indigo-600 px-4 py-2 font-medium text-indigo-700 hover:bg-indigo-50 disabled:opacity-60"
          >
            Salvar rascunho
          </button>
          <button
            onClick={onSubmit}
            disabled={busy}
            className="rounded bg-indigo-600 px-4 py-2 font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
          >
            Enviar avaliação
          </button>
        </div>
      )}
    </div>
  )
}

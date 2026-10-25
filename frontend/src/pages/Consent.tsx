import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import { CONSENT_TEXT, CONSENT_TITLE } from '../consentText'

export default function Consent() {
  const { user, loading, acceptConsent, logout } = useAuth()
  const navigate = useNavigate()
  const [checked, setChecked] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  if (loading) return <p className="p-8 text-center text-slate-500">Carregando…</p>
  if (!user) return <Navigate to="/login" replace />
  if (user.consented_at) return <Navigate to="/minhas-avaliacoes" replace />

  const accept = async () => {
    setError('')
    setBusy(true)
    try {
      await acceptConsent()
      navigate('/minhas-avaliacoes', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao registrar o consentimento.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-8">
      <div className="w-full max-w-xl space-y-4 rounded-lg bg-white p-6 shadow">
        <h1 className="text-xl font-semibold">{CONSENT_TITLE}</h1>
        <div className="space-y-3 text-sm text-slate-700">
          {CONSENT_TEXT.map((p, i) => (
            <p key={i}>{p}</p>
          ))}
        </div>
        <label className="flex items-start gap-2 text-sm">
          <input type="checkbox" checked={checked} onChange={(e) => setChecked(e.target.checked)} className="mt-1" />
          Li e concordo com o termo acima.
        </label>
        {error && (
          <p role="alert" className="rounded bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}
        <div className="flex gap-3">
          <button
            onClick={accept}
            disabled={!checked || busy}
            className="rounded bg-indigo-600 px-4 py-2 font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {busy ? 'Salvando…' : 'Aceitar e continuar'}
          </button>
          <button
            onClick={() => {
              logout()
              navigate('/login')
            }}
            className="rounded border border-slate-300 px-4 py-2 hover:bg-slate-100"
          >
            Sair
          </button>
        </div>
      </div>
    </div>
  )
}

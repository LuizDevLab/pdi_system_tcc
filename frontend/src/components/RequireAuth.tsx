import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../auth'
import Layout from './Layout'

// Exige login e consentimento aceito.
export default function RequireAuth() {
  const { user, loading } = useAuth()
  if (loading) return <p className="p-8 text-center text-slate-500">Carregando…</p>
  if (!user) return <Navigate to="/login" replace />
  if (!user.consented_at) return <Navigate to="/consentimento" replace />
  return (
    <Layout>
      <Outlet />
    </Layout>
  )
}

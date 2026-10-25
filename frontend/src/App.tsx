import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { getToken } from './api'
import { AuthProvider } from './auth'
import RequireAuth from './components/RequireAuth'
import Consent from './pages/Consent'
import Evaluation from './pages/Evaluation'
import Login from './pages/Login'
import MyEvaluations from './pages/MyEvaluations'
import MyPdi from './pages/MyPdi'

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<Navigate to={getToken() ? '/minhas-avaliacoes' : '/login'} replace />} />
          <Route path="/login" element={<Login />} />
          <Route path="/consentimento" element={<Consent />} />
          <Route element={<RequireAuth />}>
            <Route path="/minhas-avaliacoes" element={<MyEvaluations />} />
            <Route path="/avaliacao/:linkId" element={<Evaluation />} />
            <Route path="/meu-pdi" element={<MyPdi />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

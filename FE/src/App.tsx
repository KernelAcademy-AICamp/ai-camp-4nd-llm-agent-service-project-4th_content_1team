import { Route, Routes } from 'react-router-dom'
import LoginPage from './pages/login/page'
import UploadPage from './pages/upload/page'
import DashboardPage from './pages/dashboard/page'
import RootLayout from './pages/layout'
import OnboardingPage from './pages/onboarding/page'
import ScriptPage from './pages/script/page'
import ThumbnailPage from './pages/thumbnail/page'
import AnalysisPage from './pages/analysis/page'
import { ProtectedRoute } from './components/ProtectedRoute'

function App() {
  return (
    <RootLayout>
      <Routes>
        <Route>
          {/* Public Routes */}
          <Route index element={<LoginPage />} />

          {/* Protected Routes */}
          <Route path="onboarding" element={<ProtectedRoute><OnboardingPage /></ProtectedRoute>} />
          <Route path="dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
          <Route path="analysis" element={<ProtectedRoute><AnalysisPage /></ProtectedRoute>} />
          <Route path="script" element={<ProtectedRoute><ScriptPage /></ProtectedRoute>} />
          <Route path="thumbnail" element={<ProtectedRoute><ThumbnailPage /></ProtectedRoute>} />
          <Route path="upload" element={<ProtectedRoute><UploadPage /></ProtectedRoute>} />
          <Route path="dashboard/upload" element={<ProtectedRoute><UploadPage /></ProtectedRoute>} />
        </Route>
      </Routes>
    </RootLayout>
  )
}

export default App

import { Route, Routes } from 'react-router-dom'
import LoginPage from './pages/login/page'
import UploadPage from './pages/upload/page'
import DashboardPage from './pages/dashboard/page'
import RootLayout from './pages/layout'
import OnboardingPage from './pages/onboarding/page'
import ScriptPage from './pages/script/page'
import ThumbnailPage from './pages/thumbnail/page'
import AnalysisPage from './pages/analysis/page'
function App() {
  return (
    <RootLayout>
      <Routes>
        <Route>
          <Route index element={<LoginPage />} />
          <Route path="onboarding" element={<OnboardingPage />} />
          <Route path="analysis" element={<AnalysisPage />} />
          <Route path="script" element={<ScriptPage />} />
          <Route path="thumbnail" element={<ThumbnailPage />} />
          <Route path="upload" element={<UploadPage />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="dashboard/upload" element={<UploadPage />} />
        </Route>
      </Routes>
    </RootLayout>
  )
}

export default App

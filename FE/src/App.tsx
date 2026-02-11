import { Route, Routes } from 'react-router-dom'
import LoginPage from './pages/login/page'
import UploadPage from './pages/upload/page'
import DashboardPage from './pages/dashboard/page'
import RootLayout from './pages/layout'
import OnboardingPage from './pages/onboarding/page'
import ScriptPage from './pages/script/page'
import ScriptListPage from './pages/script-list/page'
import ExplorePage from './pages/explore/page'
import ThumbnailPage from './pages/thumbnail/page'
import AnalysisPage from './pages/analysis/page'
import { ProtectedRoute } from './components/ProtectedRoute'
import { HeaderOnlyLayout } from './layouts/header-only-layout'
import { FullLayout } from './layouts/full-layout'

function App() {
  return (
    <RootLayout>
      {/* 1920px 기준 메인 컨테이너 */}
      <div className="min-h-screen w-full flex justify-center bg-background">
        <div className="w-full max-w-[1920px]">
          <Routes>
            {/* Public Routes - 레이아웃 없음 */}
            <Route index element={<LoginPage />} />
            
            {/* HeaderOnlyLayout - 온보딩 */}
            <Route
              path="onboarding"
              element={
                <ProtectedRoute>
                  <HeaderOnlyLayout>
                    <OnboardingPage />
                  </HeaderOnlyLayout>
                </ProtectedRoute>
              }
            />
            
            {/* FullLayout - 나머지 페이지들 */}
            <Route
              path="dashboard"
              element={
                <ProtectedRoute>
                  <FullLayout>
                    <DashboardPage />
                  </FullLayout>
                </ProtectedRoute>
              }
            />
            
            <Route
              path="explore"
              element={
                <ProtectedRoute>
                  <FullLayout>
                    <ExplorePage />
                  </FullLayout>
                </ProtectedRoute>
              }
            />
            
            <Route
              path="analysis"
              element={
                <ProtectedRoute>
                  <FullLayout>
                    <AnalysisPage />
                  </FullLayout>
                </ProtectedRoute>
              }
            />
            
            <Route
              path="script"
              element={
                <ProtectedRoute>
                  <FullLayout>
                    <ScriptListPage />
                  </FullLayout>
                </ProtectedRoute>
              }
            />
            
            <Route
              path="script/edit"
              element={
                <ProtectedRoute>
                  <FullLayout>
                    <ScriptPage />
                  </FullLayout>
                </ProtectedRoute>
              }
            />
            
            <Route
              path="thumbnail"
              element={
                <ProtectedRoute>
                  <FullLayout>
                    <ThumbnailPage />
                  </FullLayout>
                </ProtectedRoute>
              }
            />
            
            <Route
              path="upload"
              element={
                <ProtectedRoute>
                  <FullLayout>
                    <UploadPage />
                  </FullLayout>
                </ProtectedRoute>
              }
            />
            
            <Route
              path="dashboard/upload"
              element={
                <ProtectedRoute>
                  <FullLayout>
                    <UploadPage />
                  </FullLayout>
                </ProtectedRoute>
              }
            />
          </Routes>
        </div>
      </div>
    </RootLayout>
  )
}

export default App

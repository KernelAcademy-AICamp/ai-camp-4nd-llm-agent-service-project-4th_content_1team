import { Route, Routes } from 'react-router-dom'
import LoginPage from './pages/login/page'
import UploadPage from './pages/upload/page'
import DashboardPage from './pages/dashboard/page'
import RootLayout from './pages/layout'
import OnboardingPage from './pages/onboarding/page'
import ChannelResultPage from './pages/channel-result/page'
import ExplorePage from './pages/explore/page'
import ScriptListPage from './pages/script-list/page'
import ScriptPage from './pages/script/page'
import ThumbnailPage from './pages/thumbnail/page'
import AnalysisPage from './pages/analysis/page'
import { ProtectedRoute } from './components/ProtectedRoute'
import { HeaderOnlyLayout } from './layouts/header-only-layout'
import { FullLayout } from './layouts/full-layout'

function App() {
  return (
    <RootLayout>
      <div className="min-h-screen w-full flex justify-center bg-background">
        <div className="w-full max-w-[1920px]">
          <Routes>
            <Route index element={<LoginPage />} />

            <Route
              path="onboarding/*"
              element={
                <ProtectedRoute>
                  <HeaderOnlyLayout>
                    <OnboardingPage />
                  </HeaderOnlyLayout>
                </ProtectedRoute>
              }
            />

            <Route
              path="channel-result"
              element={
                <ProtectedRoute>
                  <FullLayout>
                    <ChannelResultPage />
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

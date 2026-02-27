"use client"

import React from "react"

import { useState, useEffect, useRef } from "react"
import { useNavigate } from "react-router-dom"
import { Button } from "../../components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/card"
import { Input } from "../../components/ui/input"
import { Label } from "../../components/ui/label"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui/tabs"
import { Play, Sparkles, TrendingUp, Calendar, ImageIcon } from "lucide-react"
import { initiateGoogleLogin, getGoogleAuthCode } from "../../lib/googleAuth"
import { googleLogin, getMyPersona } from "../../lib/api/index"

export default function LoginPage() {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState("login")
  const navigate = useNavigate()

  // 로그인 폼 상태
  const [loginEmail, setLoginEmail] = useState("")
  const [loginPassword, setLoginPassword] = useState("")

  // 회원가입 폼 상태
  const [signupEmail, setSignupEmail] = useState("")
  const [signupPassword, setSignupPassword] = useState("")
  const [signupName, setSignupName] = useState("")

  // StrictMode 중복 호출 방지
  const hasCalledRef = useRef(false)

  // Google OAuth 콜백 처리
  useEffect(() => {
    const handleGoogleCallback = async () => {
      const code = getGoogleAuthCode()
      if (code && !hasCalledRef.current) {
        hasCalledRef.current = true
        setIsLoading(true)
        setError(null)

        try {
          const redirectUri = import.meta.env.VITE_GOOGLE_REDIRECT_URI || window.location.origin
          const response = await googleLogin(code, redirectUri)

          // 로그인 성공 - 토큰 저장 (선택사항, 쿠키 사용 시 불필요)
          if (response.tokens) {
            localStorage.setItem('accessToken', response.tokens.accessToken)
            localStorage.setItem('refreshToken', response.tokens.refreshToken)
          }

          // 페르소나 존재 확인 후 라우팅
          try {
            await getMyPersona()
            // 페르소나가 있으면 주제 탐색으로 이동
            navigate('/explore')
          } catch {
            // 페르소나가 없으면 온보딩으로 이동
            navigate('/onboarding')
          }
        } catch (err: any) {
          console.error('Google login failed:', err)
          setError(err.response?.data?.detail || '로그인에 실패했습니다. 다시 시도해주세요.')
          // URL에서 code 파라미터 제거
          window.history.replaceState({}, document.title, window.location.pathname)
        } finally {
          setIsLoading(false)
        }
      }
    }

    handleGoogleCallback()
  }, [navigate])

  const handleGoogleLogin = () => {
    initiateGoogleLogin()
  }

  const handleEmailLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!loginEmail || !loginPassword) {
      setError("이메일과 비밀번호를 입력해주세요.")
      return
    }

    setIsLoading(true)
    try {
      // TODO: 이메일 로그인 API 연동
      // const response = await emailLogin(loginEmail, loginPassword)
      setError("이메일 로그인은 아직 구현되지 않았습니다. Google 계정을 사용해주세요.")
    } catch (err: any) {
      setError(err.response?.data?.detail || "로그인에 실패했습니다.")
    } finally {
      setIsLoading(false)
    }
  }

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!signupEmail || !signupPassword) {
      setError("이메일과 비밀번호를 입력해주세요.")
      return
    }

    if (signupPassword.length < 8) {
      setError("비밀번호는 8자 이상이어야 합니다.")
      return
    }

    setIsLoading(true)
    try {
      // TODO: 회원가입 API 연동
      // const response = await signup(signupEmail, signupPassword, signupName)
      setError("회원가입은 아직 구현되지 않았습니다. Google 계정을 사용해주세요.")
    } catch (err: any) {
      setError(err.response?.data?.detail || "회원가입에 실패했습니다.")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-background flex">
      {/* Left Side - Branding */}
      <div className="hidden lg:flex lg:w-1/2 flex-col justify-between p-12 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/20 via-transparent to-accent/10" />

        <div className="relative z-10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center">
              <Play className="w-5 h-5 text-primary-foreground fill-current" />
            </div>
            <span className="text-2xl font-bold text-foreground">CreatorHub</span>
          </div>
        </div>

        <div className="relative z-10 space-y-8">
          <h1 className="text-5xl font-bold text-foreground leading-tight text-balance">
            AI로 완성하는<br />
            <span className="text-primary">유튜브 콘텐츠</span>
          </h1>
          <p className="text-lg text-muted-foreground max-w-md">
            트렌드 분석부터 스크립트 작성, 썸네일 생성까지.
            당신의 채널 성장을 위한 올인원 솔루션.
          </p>

          <div className="grid grid-cols-2 gap-4 max-w-md">
            <FeatureCard
              icon={<TrendingUp className="w-5 h-5" />}
              title="트렌드 분석"
              description="실시간 인기 주제 추천"
            />
            <FeatureCard
              icon={<Calendar className="w-5 h-5" />}
              title="콘텐츠 캘린더"
              description="체계적인 업로드 계획"
            />
            <FeatureCard
              icon={<Sparkles className="w-5 h-5" />}
              title="AI 스크립트"
              description="자동 스크립트 생성"
            />
            <FeatureCard
              icon={<ImageIcon className="w-5 h-5" />}
              title="썸네일 생성"
              description="클릭률 높은 썸네일"
            />
          </div>
        </div>

        <div className="relative z-10 text-sm text-muted-foreground">
          10,000+ 크리에이터가 사용 중
        </div>
      </div>

      {/* Right Side - Login Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8">
        <Card className="w-full max-w-md border-border/50 bg-card/50 backdrop-blur">
          <CardHeader className="text-center">
            <div className="lg:hidden flex items-center justify-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center">
                <Play className="w-5 h-5 text-primary-foreground fill-current" />
              </div>
              <span className="text-2xl font-bold text-foreground">CreatorHub</span>
            </div>
            <CardTitle className="text-2xl">시작하기</CardTitle>
            <CardDescription>계정으로 로그인하거나 새로 가입하세요</CardDescription>
          </CardHeader>
          <CardContent>
            {error && (
              <div className="mb-4 p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-sm">
                {error}
              </div>
            )}

            {isLoading ? (
              <div className="flex flex-col items-center justify-center py-12 gap-3">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                <p className="text-sm text-muted-foreground">처리 중...</p>
              </div>
            ) : (
              <div className="space-y-4">
                {/* 탭 - 로그인 / 회원가입 */}
                <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                  <TabsList className="grid w-full grid-cols-2">
                    <TabsTrigger value="login">로그인</TabsTrigger>
                    <TabsTrigger value="signup">회원가입</TabsTrigger>
                  </TabsList>

                  {/* 로그인 탭 */}
                  <TabsContent value="login" className="space-y-4 mt-4">
                    {/* Google 로그인 버튼 */}
                    <Button
                      variant="outline"
                      className="w-full gap-2 h-12 bg-transparent"
                      onClick={handleGoogleLogin}
                      disabled={isLoading}
                    >
                      <svg className="w-5 h-5" viewBox="0 0 24 24">
                        <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                        <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                        <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                        <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                      </svg>
                      Google 계정으로 계속하기
                    </Button>

                    {/* 구분선 */}
                    <div className="relative">
                      <div className="absolute inset-0 flex items-center">
                        <span className="w-full border-t border-border/50" />
                      </div>
                      <div className="relative flex justify-center text-xs uppercase">
                        <span className="bg-card px-2 text-muted-foreground">또는</span>
                      </div>
                    </div>

                    {/* 이메일 로그인 폼 */}
                    <form onSubmit={handleEmailLogin} className="space-y-4">
                      <div className="space-y-2">
                        <Label htmlFor="login-email">이메일</Label>
                        <Input
                          id="login-email"
                          type="email"
                          placeholder="name@example.com"
                          value={loginEmail}
                          onChange={(e) => setLoginEmail(e.target.value)}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="login-password">비밀번호</Label>
                        <Input
                          id="login-password"
                          type="password"
                          placeholder="비밀번호 입력"
                          value={loginPassword}
                          onChange={(e) => setLoginPassword(e.target.value)}
                        />
                      </div>
                      <Button type="submit" className="w-full" disabled={isLoading}>
                        로그인
                      </Button>
                    </form>
                  </TabsContent>

                  {/* 회원가입 탭 */}
                  <TabsContent value="signup" className="space-y-4 mt-4">
                    {/* Google 회원가입 버튼 */}
                    <Button
                      variant="outline"
                      className="w-full gap-2 h-12 bg-transparent"
                      onClick={handleGoogleLogin}
                      disabled={isLoading}
                    >
                      <svg className="w-5 h-5" viewBox="0 0 24 24">
                        <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                        <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                        <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                        <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                      </svg>
                      Google 계정으로 계속하기
                    </Button>

                    {/* 구분선 */}
                    <div className="relative">
                      <div className="absolute inset-0 flex items-center">
                        <span className="w-full border-t border-border/50" />
                      </div>
                      <div className="relative flex justify-center text-xs uppercase">
                        <span className="bg-card px-2 text-muted-foreground">또는</span>
                      </div>
                    </div>

                    {/* 이메일 회원가입 폼 */}
                    <form onSubmit={handleSignup} className="space-y-4">
                      <div className="space-y-2">
                        <Label htmlFor="signup-name">이름</Label>
                        <Input
                          id="signup-name"
                          type="text"
                          placeholder="홍길동"
                          value={signupName}
                          onChange={(e) => setSignupName(e.target.value)}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="signup-email">이메일</Label>
                        <Input
                          id="signup-email"
                          type="email"
                          placeholder="name@example.com"
                          value={signupEmail}
                          onChange={(e) => setSignupEmail(e.target.value)}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="signup-password">비밀번호</Label>
                        <Input
                          id="signup-password"
                          type="password"
                          placeholder="비밀번호 입력"
                          value={signupPassword}
                          onChange={(e) => setSignupPassword(e.target.value)}
                        />
                      </div>
                      <Button type="submit" className="w-full" disabled={isLoading}>
                        회원가입
                      </Button>
                    </form>
                  </TabsContent>
                </Tabs>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function FeatureCard({ icon, title, description }: { icon: React.ReactNode; title: string; description: string }) {
  return (
    <div className="p-4 rounded-xl bg-card/50 border border-border/50 space-y-2">
      <div className="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center text-primary">
        {icon}
      </div>
      <h3 className="font-semibold text-foreground">{title}</h3>
      <p className="text-sm text-muted-foreground">{description}</p>
    </div>
  )
}

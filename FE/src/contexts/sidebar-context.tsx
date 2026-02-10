import { createContext, useContext, useState, ReactNode } from "react"

interface SidebarContextType {
  isAppSidebarOpen: boolean
  isDetailSidebarOpen: boolean
  toggleAppSidebar: () => void
  openDetailSidebar: () => void
  closeDetailSidebar: () => void
}

const SidebarContext = createContext<SidebarContextType | undefined>(undefined)

export function SidebarProvider({ children }: { children: ReactNode }) {
  const [isAppSidebarOpen, setIsAppSidebarOpen] = useState(true)
  const [isDetailSidebarOpen, setIsDetailSidebarOpen] = useState(false)

  const toggleAppSidebar = () => {
    setIsAppSidebarOpen((prev) => {
      const newState = !prev
      // AppSidebar 펼칠 때 DetailSidebar 닫기
      if (newState) {
        setIsDetailSidebarOpen(false)
      }
      return newState
    })
  }

  const openDetailSidebar = () => {
    // DetailSidebar 열 때 AppSidebar 자동 접기
    setIsDetailSidebarOpen(true)
    setIsAppSidebarOpen(false)
  }

  const closeDetailSidebar = () => {
    setIsDetailSidebarOpen(false)
  }

  return (
    <SidebarContext.Provider
      value={{
        isAppSidebarOpen,
        isDetailSidebarOpen,
        toggleAppSidebar,
        openDetailSidebar,
        closeDetailSidebar,
      }}
    >
      {children}
    </SidebarContext.Provider>
  )
}

export function useSidebar() {
  const context = useContext(SidebarContext)
  if (context === undefined) {
    throw new Error("useSidebar must be used within a SidebarProvider")
  }
  return context
}

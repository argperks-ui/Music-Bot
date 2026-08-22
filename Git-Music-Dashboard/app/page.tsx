"use client"

import { useState } from "react"
import { LoginView } from "@/components/music/login-view"
import { TopNav, type View } from "@/components/music/top-nav"
import { DashboardView } from "@/components/music/dashboard-view"
import { LibraryView } from "@/components/music/library-view"
import { servers } from "@/lib/music-data"

export default function Page() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [view, setView] = useState<View>("dashboard")
  const [selectedServer, setSelectedServer] = useState(servers[0].id)

  if (!isAuthenticated) {
    return <LoginView onLogin={() => setIsAuthenticated(true)} />
  }

  return (
    <main className="min-h-svh bg-background">
      <TopNav
        view={view}
        onViewChange={setView}
        selectedServer={selectedServer}
        onServerChange={setSelectedServer}
        onLogout={() => setIsAuthenticated(false)}
      />
      {view === "dashboard" ? <DashboardView /> : <LibraryView />}
    </main>
  )
}

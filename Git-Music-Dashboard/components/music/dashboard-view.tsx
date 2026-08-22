"use client"

import { useEffect, useState } from "react"
import { NowPlayingCard } from "@/components/music/now-playing-card"
import { QueuePanel } from "@/components/music/queue-panel"
import { StatsGrid } from "@/components/music/stats-grid"

export interface Track {
  title: string
  url: string
  webpage_url?: string
  thumbnail?: string
  duration_string: string
  requester: string
}

export interface PlayerState {
  now_playing: Track | null
  queue: Track[]
  volume: number
  loop: string
}

interface DashboardViewProps {
  guildId?: string
}

export function DashboardView({ guildId = "123456789012345678" }: DashboardViewProps) {
  const [playerState, setPlayerState] = useState<PlayerState>({
    now_playing: null,
    queue: [],
    volume: 50,
    loop: "off",
  })
  const [isPlaying, setIsPlaying] = useState(false)

  // 1. Poll FastAPI Backend for Live Voice Channel State
  const fetchState = async () => {
    try {
      const res = await fetch(`/api/player/${guildId}`)
      if (res.ok) {
        const data = await res.json()
        setPlayerState({
          now_playing: data.now_playing || null,
          queue: data.queue || [],
          volume: data.volume ?? 50,
          loop: data.loop || "off",
        })
        setIsPlaying(!!data.now_playing)
      }
    } catch (err) {
      console.error("Failed to sync Git Music state:", err)
    }
  }

  useEffect(() => {
    fetchState()
    const interval = setInterval(fetchState, 3000)
    return () => clearInterval(interval)
  }, [guildId])

  // 2. Dispatch Control Actions (Pause, Resume, Skip, Volume)
  const handleControl = async (action: "pause" | "resume" | "skip" | "volume", value?: number) => {
    try {
      await fetch(`/api/player/${guildId}/control`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, value }),
      })
      fetchState()
    } catch (err) {
      console.error("Failed to execute control action:", err)
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-4 py-6 sm:px-6 sm:py-8">
      <div>
        <h1 className="text-balance text-2xl font-semibold tracking-tight text-foreground">
          Dashboard
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Control playback and monitor Git Music in real time.
        </p>
      </div>

      {/* Real-time Bot Stats */}
      <StatsGrid 
        queueCount={playerState.queue.length}
        volume={playerState.volume}
        isVoiceConnected={isPlaying}
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1.3fr_1fr]">
        {/* Active Track Card with Controls */}
        <NowPlayingCard 
          track={playerState.now_playing} 
          isPlaying={isPlaying}
          volume={playerState.volume}
          onControl={handleControl}
        />

        {/* Live Track Queue Panel */}
        <div className="lg:min-h-[420px]">
          <QueuePanel 
            queue={playerState.queue}
            onSkip={() => handleControl("skip")}
          />
        </div>
      </div>
    </div>
  )
}
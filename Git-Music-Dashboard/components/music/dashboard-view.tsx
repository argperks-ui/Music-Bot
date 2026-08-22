import { NowPlayingCard } from "@/components/music/now-playing-card"
import { QueuePanel } from "@/components/music/queue-panel"
import { StatsGrid } from "@/components/music/stats-grid"

export function DashboardView() {
  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-4 py-6 sm:px-6 sm:py-8">
      <div>
        <h1 className="text-balance text-2xl font-semibold tracking-tight text-foreground">
          Dashboard
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Control playback and monitor Viper Audio Core in real time.
        </p>
      </div>

      <StatsGrid />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1.3fr_1fr]">
        <NowPlayingCard />
        <div className="lg:min-h-[420px]">
          <QueuePanel />
        </div>
      </div>
    </div>
  )
}

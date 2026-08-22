import { Server, Gauge, Cpu } from "lucide-react"
import { Progress } from "@/components/ui/progress"
import { botStats } from "@/lib/music-data"

export function StatsGrid() {
  const ramPercent = Math.round((botStats.ramUsedGb / botStats.ramTotalGb) * 100)

  return (
    <section aria-label="Bot performance stats" className="grid grid-cols-1 gap-4 sm:grid-cols-3">
      <StatCard
        icon={Server}
        label="Connected Voice Servers"
        value={botStats.connectedServers.toString()}
      />
      <StatCard icon={Gauge} label="System Latency" value={`${botStats.latencyMs}ms`} good />
      <div className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-4">
        <div className="flex items-center gap-2">
          <Cpu className="size-4 text-accent" aria-hidden />
          <p className="text-xs font-medium text-muted-foreground">RAM / CPU Load</p>
        </div>
        <div>
          <div className="flex items-baseline justify-between">
            <span className="font-mono text-sm text-foreground">
              {botStats.ramUsedGb}GB / {botStats.ramTotalGb}GB
            </span>
            <span className="font-mono text-xs text-muted-foreground">{ramPercent}%</span>
          </div>
          <Progress value={ramPercent} className="mt-1.5 h-1.5" />
        </div>
        <div>
          <div className="flex items-baseline justify-between">
            <span className="font-mono text-sm text-foreground">CPU</span>
            <span className="font-mono text-xs text-muted-foreground">{botStats.cpuLoadPercent}%</span>
          </div>
          <Progress value={botStats.cpuLoadPercent} className="mt-1.5 h-1.5" />
        </div>
      </div>
    </section>
  )
}

function StatCard({
  icon: Icon,
  label,
  value,
  good,
}: {
  icon: typeof Server
  label: string
  value: string
  good?: boolean
}) {
  return (
    <div className="flex flex-col justify-between gap-3 rounded-2xl border border-border bg-card p-4">
      <div className="flex items-center gap-2">
        <Icon className="size-4 text-accent" aria-hidden />
        <p className="text-xs font-medium text-muted-foreground">{label}</p>
      </div>
      <p
        className={`font-mono text-3xl font-semibold ${good ? "text-accent" : "text-foreground"}`}
      >
        {value}
      </p>
    </div>
  )
}

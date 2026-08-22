"use client"

import { useEffect, useState } from "react"
import Image from "next/image"
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  RotateCcw,
  Shuffle,
  Repeat,
  Repeat1,
  Volume2,
} from "lucide-react"
import { Slider } from "@/components/ui/slider"
import { WaveVisualizer } from "@/components/music/wave-visualizer"
import { nowPlaying, currentProgressSeconds } from "@/lib/music-data"

function formatTime(totalSeconds: number) {
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = Math.floor(totalSeconds % 60)
  return `${minutes}:${seconds.toString().padStart(2, "0")}`
}

export function NowPlayingCard() {
  const [isPlaying, setIsPlaying] = useState(true)
  const [progress, setProgress] = useState(currentProgressSeconds)
  const [volume, setVolume] = useState(72)
  const [repeatMode, setRepeatMode] = useState<"off" | "all" | "one">("all")
  const [shuffled, setShuffled] = useState(false)

  useEffect(() => {
    if (!isPlaying) return
    const interval = setInterval(() => {
      setProgress((prev) => (prev + 1 >= nowPlaying.durationSeconds ? 0 : prev + 1))
    }, 1000)
    return () => clearInterval(interval)
  }, [isPlaying])

  const percent = (progress / nowPlaying.durationSeconds) * 100

  return (
    <section
      aria-label="Now playing"
      className="rounded-2xl border border-border bg-card p-5 shadow-xl sm:p-6"
    >
      <div className="flex flex-col gap-6 sm:flex-row">
        <div className="relative mx-auto size-40 shrink-0 overflow-hidden rounded-xl border border-border sm:mx-0 sm:size-44">
          <Image
            src={nowPlaying.cover || "/placeholder.svg"}
            alt={`Album art for ${nowPlaying.title} by ${nowPlaying.artist}`}
            fill
            className="object-cover"
          />
        </div>

        <div className="flex flex-1 flex-col justify-between gap-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-accent">Now Playing</p>
            <h2 className="mt-1 text-balance text-xl font-semibold text-foreground sm:text-2xl">
              {nowPlaying.title}
            </h2>
            <p className="text-sm text-muted-foreground">{nowPlaying.artist}</p>
            {nowPlaying.requestedBy && (
              <p className="mt-1 text-xs text-muted-foreground">
                Requested by <span className="text-foreground">{nowPlaying.requestedBy}</span>
              </p>
            )}
          </div>

          <WaveVisualizer playing={isPlaying} />

          <div>
            <Slider
              value={[percent]}
              onValueChange={(val) => {
                const value = Array.isArray(val) ? val[0] : val
                setProgress((value / 100) * nowPlaying.durationSeconds)
              }}
              max={100}
              step={0.1}
              aria-label="Seek"
              className="[&_[data-slot=slider-range]]:bg-primary"
            />
            <div className="mt-1.5 flex justify-between font-mono text-xs text-muted-foreground">
              <span>{formatTime(progress)}</span>
              <span>{nowPlaying.duration}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center justify-center gap-2 sm:justify-start">
          <ControlButton
            label={shuffled ? "Disable shuffle" : "Enable shuffle"}
            active={shuffled}
            onClick={() => setShuffled((s) => !s)}
          >
            <Shuffle className="size-4" aria-hidden />
          </ControlButton>
          <ControlButton label="Previous track">
            <SkipBack className="size-4" aria-hidden />
          </ControlButton>
          <ControlButton label="Replay track" onClick={() => setProgress(0)}>
            <RotateCcw className="size-4" aria-hidden />
          </ControlButton>
          <button
            onClick={() => setIsPlaying((p) => !p)}
            aria-label={isPlaying ? "Pause" : "Play"}
            className="flex size-11 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-[0_0_24px_-4px_color-mix(in_oklch,var(--primary)_75%,transparent)] transition-transform hover:scale-105"
          >
            {isPlaying ? (
              <Pause className="size-5" aria-hidden />
            ) : (
              <Play className="size-5" aria-hidden />
            )}
          </button>
          <ControlButton label="Next track">
            <SkipForward className="size-4" aria-hidden />
          </ControlButton>
          <ControlButton
            label={`Repeat mode: ${repeatMode}`}
            active={repeatMode !== "off"}
            onClick={() =>
              setRepeatMode((mode) => (mode === "off" ? "all" : mode === "all" ? "one" : "off"))
            }
          >
            {repeatMode === "one" ? (
              <Repeat1 className="size-4" aria-hidden />
            ) : (
              <Repeat className="size-4" aria-hidden />
            )}
          </ControlButton>
        </div>

        <div className="flex items-center gap-3">
          <Volume2 className="size-4 shrink-0 text-muted-foreground" aria-hidden />
          <Slider
            value={[volume]}
            onValueChange={(val) => setVolume(Array.isArray(val) ? val[0] : val)}
            max={100}
            step={1}
            aria-label="Volume"
            className="w-32"
          />
          <span className="w-8 shrink-0 font-mono text-xs text-muted-foreground">{volume}%</span>
        </div>
      </div>
    </section>
  )
}

function ControlButton({
  children,
  label,
  active,
  onClick,
}: {
  children: React.ReactNode
  label: string
  active?: boolean
  onClick?: () => void
}) {
  return (
    <button
      onClick={onClick}
      aria-label={label}
      aria-pressed={active}
      className={`flex size-9 items-center justify-center rounded-full border transition-colors ${
        active
          ? "border-accent/40 bg-accent/10 text-accent"
          : "border-border bg-secondary text-muted-foreground hover:text-foreground"
      }`}
    >
      {children}
    </button>
  )
}

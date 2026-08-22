"use client"

import { useState } from "react"
import Image from "next/image"
import { ArrowUp, ArrowUpToLine, ArrowDown, X, Shuffle, Trash2, Copy } from "lucide-react"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { queue as initialQueue, type Track } from "@/lib/music-data"

function shuffleArray<T>(items: T[]) {
  const copy = [...items]
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[copy[i], copy[j]] = [copy[j], copy[i]]
  }
  return copy
}

export function QueuePanel() {
  const [tracks, setTracks] = useState<Track[]>(initialQueue)

  function removeTrack(id: string) {
    setTracks((prev) => prev.filter((t) => t.id !== id))
  }

  function moveToTop(id: string) {
    setTracks((prev) => {
      const track = prev.find((t) => t.id === id)
      if (!track) return prev
      return [track, ...prev.filter((t) => t.id !== id)]
    })
  }

  function moveUp(index: number) {
    if (index === 0) return
    setTracks((prev) => {
      const next = [...prev]
      ;[next[index - 1], next[index]] = [next[index], next[index - 1]]
      return next
    })
  }

  function moveDown(index: number) {
    setTracks((prev) => {
      if (index === prev.length - 1) return prev
      const next = [...prev]
      ;[next[index + 1], next[index]] = [next[index], next[index + 1]]
      return next
    })
  }

  function removeDuplicates() {
    setTracks((prev) => {
      const seen = new Set<string>()
      return prev.filter((t) => {
        const key = `${t.title}-${t.artist}`
        if (seen.has(key)) return false
        seen.add(key)
        return true
      })
    })
  }

  return (
    <section
      aria-label="Live queue manager"
      className="flex h-full flex-col rounded-2xl border border-border bg-card p-5"
    >
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-foreground">Live Queue</h2>
        <span className="rounded-full bg-secondary px-2 py-0.5 font-mono text-xs text-muted-foreground">
          {tracks.length} tracks
        </span>
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        <Button
          size="sm"
          variant="outline"
          className="h-8 gap-1.5 border-border bg-transparent text-xs"
          onClick={() => setTracks([])}
        >
          <Trash2 className="size-3.5" aria-hidden />
          Clear Queue
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="h-8 gap-1.5 border-border bg-transparent text-xs"
          onClick={() => setTracks((prev) => shuffleArray(prev))}
        >
          <Shuffle className="size-3.5" aria-hidden />
          Shuffle All
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="h-8 gap-1.5 border-border bg-transparent text-xs"
          onClick={removeDuplicates}
        >
          <Copy className="size-3.5" aria-hidden />
          Remove Duplicates
        </Button>
      </div>

      <ScrollArea className="mt-4 -mr-2 flex-1 pr-2">
        <ol className="flex flex-col gap-2">
          {tracks.length === 0 && (
            <li className="rounded-lg border border-dashed border-border py-10 text-center text-sm text-muted-foreground">
              Queue is empty
            </li>
          )}
          {tracks.map((track, index) => (
            <li
              key={track.id}
              className="group flex items-center gap-3 rounded-lg border border-border bg-secondary/40 p-2.5 transition-colors hover:bg-secondary"
            >
              <span className="w-4 shrink-0 text-center font-mono text-xs text-muted-foreground">
                {index + 1}
              </span>
              <div className="relative size-10 shrink-0 overflow-hidden rounded-md border border-border">
                <Image
                  src={track.cover || "/placeholder.svg"}
                  alt=""
                  fill
                  className="object-cover"
                />
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-foreground">{track.title}</p>
                <p className="truncate text-xs text-muted-foreground">{track.artist}</p>
              </div>
              <span className="hidden shrink-0 font-mono text-xs text-muted-foreground sm:inline">
                {track.duration}
              </span>
              <div className="flex shrink-0 items-center gap-0.5 opacity-70 transition-opacity group-hover:opacity-100">
                <IconAction label="Move up" onClick={() => moveUp(index)}>
                  <ArrowUp className="size-3.5" aria-hidden />
                </IconAction>
                <IconAction label="Move down" onClick={() => moveDown(index)}>
                  <ArrowDown className="size-3.5" aria-hidden />
                </IconAction>
                <IconAction label="Move to top" onClick={() => moveToTop(track.id)}>
                  <ArrowUpToLine className="size-3.5" aria-hidden />
                </IconAction>
                <IconAction label="Remove from queue" onClick={() => removeTrack(track.id)}>
                  <X className="size-3.5" aria-hidden />
                </IconAction>
              </div>
            </li>
          ))}
        </ol>
      </ScrollArea>
    </section>
  )
}

function IconAction({
  children,
  label,
  onClick,
}: {
  children: React.ReactNode
  label: string
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      aria-label={label}
      className="flex size-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
    >
      {children}
    </button>
  )
}

"use client"

import { useMemo, useState } from "react"
import Image from "next/image"
import { Search, Play, ListPlus, Check } from "lucide-react"
import { Input } from "@/components/ui/input"
import { library, filterTags } from "@/lib/music-data"

export function LibraryView() {
  const [query, setQuery] = useState("")
  const [activeTag, setActiveTag] = useState<string | null>(null)
  const [addedIds, setAddedIds] = useState<Set<string>>(new Set())

  const filtered = useMemo(() => {
    return library.filter((track) => {
      const matchesQuery =
        query.trim().length === 0 ||
        track.title.toLowerCase().includes(query.toLowerCase()) ||
        track.artist.toLowerCase().includes(query.toLowerCase())
      const matchesTag = !activeTag || track.tags?.includes(activeTag)
      return matchesQuery && matchesTag
    })
  }, [query, activeTag])

  function handleAddToQueue(id: string) {
    setAddedIds((prev) => new Set(prev).add(id))
    setTimeout(() => {
      setAddedIds((prev) => {
        const next = new Set(prev)
        next.delete(id)
        return next
      })
    }, 1600)
  }

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-4 py-6 sm:px-6 sm:py-8">
      <div>
        <h1 className="text-balance text-2xl font-semibold tracking-tight text-foreground">
          Library
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Browse and queue tracks from your saved collection.
        </p>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative w-full sm:max-w-xs">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden
          />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search tracks or artists"
            className="border-border bg-card pl-9"
            aria-label="Search library"
          />
        </div>

        <div className="flex flex-wrap gap-2">
          <FilterChip active={activeTag === null} onClick={() => setActiveTag(null)}>
            All
          </FilterChip>
          {filterTags.map((tag) => (
            <FilterChip key={tag} active={activeTag === tag} onClick={() => setActiveTag(tag)}>
              {tag}
            </FilterChip>
          ))}
        </div>
      </div>

      <div className="overflow-hidden rounded-2xl border border-border bg-card">
        <div className="hidden grid-cols-[2rem_1fr_6rem_5rem_6rem] gap-3 border-b border-border px-4 py-2.5 text-xs font-medium uppercase tracking-wide text-muted-foreground sm:grid">
          <span aria-hidden />
          <span>Track</span>
          <span className="text-right">Plays</span>
          <span className="text-right">Length</span>
          <span className="text-right">Action</span>
        </div>

        <ul>
          {filtered.length === 0 && (
            <li className="px-4 py-12 text-center text-sm text-muted-foreground">
              No tracks match your search.
            </li>
          )}
          {filtered.map((track) => {
            const justAdded = addedIds.has(track.id)
            return (
              <li
                key={track.id}
                className="group grid grid-cols-[2.5rem_1fr_auto] items-center gap-3 border-b border-border px-4 py-3 last:border-b-0 hover:bg-secondary/40 sm:grid-cols-[2rem_1fr_6rem_5rem_6rem]"
              >
                <button
                  aria-label={`Play ${track.title}`}
                  className="flex size-8 items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-primary hover:text-primary-foreground"
                >
                  <Play className="size-3.5" aria-hidden />
                </button>

                <div className="flex min-w-0 items-center gap-3">
                  <div className="relative size-10 shrink-0 overflow-hidden rounded-md border border-border">
                    <Image src={track.cover || "/placeholder.svg"} alt="" fill className="object-cover" />
                  </div>
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-foreground">{track.title}</p>
                    <p className="truncate text-xs text-muted-foreground">{track.artist}</p>
                  </div>
                </div>

                <span className="hidden text-right font-mono text-sm text-muted-foreground sm:inline">
                  {track.timesPlayed}
                </span>
                <span className="hidden text-right font-mono text-sm text-muted-foreground sm:inline">
                  {track.duration}
                </span>

                <div className="col-span-1 flex justify-end sm:col-span-1">
                  <button
                    onClick={() => handleAddToQueue(track.id)}
                    disabled={justAdded}
                    className={`flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-xs font-medium transition-colors ${
                      justAdded
                        ? "border-accent/40 bg-accent/10 text-accent"
                        : "border-border bg-secondary text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {justAdded ? (
                      <>
                        <Check className="size-3.5" aria-hidden />
                        Added
                      </>
                    ) : (
                      <>
                        <ListPlus className="size-3.5" aria-hidden />
                        Queue
                      </>
                    )}
                  </button>
                </div>
              </li>
            )
          })}
        </ul>
      </div>
    </div>
  )
}

function FilterChip({
  children,
  active,
  onClick,
}: {
  children: React.ReactNode
  active: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      aria-pressed={active}
      className={`rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
        active
          ? "border-primary/40 bg-primary/15 text-foreground"
          : "border-border bg-card text-muted-foreground hover:text-foreground"
      }`}
    >
      {children}
    </button>
  )
}

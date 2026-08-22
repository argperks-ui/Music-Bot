"use client"

import Image from "next/image"
import { ChevronDown, LogOut, Radio } from "lucide-react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { servers } from "@/lib/music-data"

export type View = "dashboard" | "library"

export function TopNav({
  view,
  onViewChange,
  selectedServer,
  onServerChange,
  onLogout,
}: {
  view: View
  onViewChange: (v: View) => void
  selectedServer: string
  onServerChange: (id: string) => void
  onLogout: () => void
}) {
  const current = servers.find((s) => s.id === selectedServer) ?? servers[0]

  return (
    <header className="sticky top-0 z-20 flex items-center justify-between gap-4 border-b border-border bg-background/85 px-4 py-3 backdrop-blur-md sm:px-6">
      <div className="flex min-w-0 items-center gap-3">
        <div className="hidden size-8 shrink-0 items-center justify-center rounded-lg border border-border bg-card sm:flex">
          <Image src="/images/viper-logo.png" alt="" width={20} height={20} className="size-5" />
        </div>

        <DropdownMenu>
          <DropdownMenuTrigger className="flex min-w-0 items-center gap-2 rounded-lg border border-border bg-card px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-secondary">
            <span className="truncate max-w-[9rem] sm:max-w-[16rem]">{current.name}</span>
            <ChevronDown className="size-4 shrink-0 text-muted-foreground" aria-hidden />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-64">
            <DropdownMenuGroup>
              <DropdownMenuLabel>Your servers</DropdownMenuLabel>
              <DropdownMenuSeparator />
              {servers.map((server) => (
                <DropdownMenuItem key={server.id} onSelect={() => onServerChange(server.id)}>
                  <div className="flex w-full items-center justify-between gap-2">
                    <span className="truncate">{server.name}</span>
                    <span className="text-xs text-muted-foreground">{server.members}</span>
                  </div>
                </DropdownMenuItem>
              ))}
            </DropdownMenuGroup>
          </DropdownMenuContent>
        </DropdownMenu>

        <div className="hidden items-center gap-1.5 rounded-full border border-border bg-card px-3 py-1.5 text-xs text-muted-foreground md:flex">
          <span className="relative flex size-2">
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-accent opacity-60" />
            <span className="relative inline-flex size-2 rounded-full bg-accent" />
          </span>
          Connected to Voice · 24ms
        </div>
      </div>

      <nav className="flex items-center gap-1 rounded-lg border border-border bg-card p-1" aria-label="Views">
        <button
          onClick={() => onViewChange("dashboard")}
          className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
            view === "dashboard"
              ? "bg-primary text-primary-foreground shadow-[0_0_16px_-4px_color-mix(in_oklch,var(--primary)_70%,transparent)]"
              : "text-muted-foreground hover:text-foreground"
          }`}
          aria-current={view === "dashboard" ? "page" : undefined}
        >
          Dashboard
        </button>
        <button
          onClick={() => onViewChange("library")}
          className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
            view === "library"
              ? "bg-primary text-primary-foreground shadow-[0_0_16px_-4px_color-mix(in_oklch,var(--primary)_70%,transparent)]"
              : "text-muted-foreground hover:text-foreground"
          }`}
          aria-current={view === "library" ? "page" : undefined}
        >
          Library
        </button>
      </nav>

      <div className="flex items-center gap-3">
        <Radio className="hidden size-4 text-accent md:block" aria-hidden />
        <DropdownMenu>
          <DropdownMenuTrigger className="flex items-center gap-2 rounded-full border border-border bg-card p-1 pr-2 transition-colors hover:bg-secondary">
            <Avatar className="size-7">
              <AvatarImage src="/images/user-avatar.png" alt="" />
              <AvatarFallback>SB</AvatarFallback>
            </Avatar>
            <span className="hidden text-sm font-medium text-foreground sm:inline">shadowbyte</span>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            <DropdownMenuGroup>
              <DropdownMenuLabel>shadowbyte</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onSelect={onLogout} className="text-destructive">
                <LogOut className="size-4" aria-hidden />
                Log out
              </DropdownMenuItem>
            </DropdownMenuGroup>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}

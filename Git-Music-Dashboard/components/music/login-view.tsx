"use client"

import Image from "next/image"
import { AudioWaveform, SlidersHorizontal, ListMusic } from "lucide-react"
import { Button } from "@/components/ui/button"

const features = [
  {
    icon: AudioWaveform,
    title: "HD Audio Streaming",
    description: "Crystal-clear, low-latency voice channel playback.",
  },
  {
    icon: SlidersHorizontal,
    title: "Custom Equalizers",
    description: "Fine-tune bass, treble, and presets per server.",
  },
  {
    icon: ListMusic,
    title: "Server Queue Control",
    description: "Reorder, skip, and manage tracks in real time.",
  },
]

export function LoginView({ onLogin }: { onLogin: () => void }) {
  return (
    <main className="relative flex min-h-svh flex-col items-center justify-center overflow-hidden px-6 py-16">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 [background:radial-gradient(circle_at_50%_0%,color-mix(in_oklch,var(--primary)_18%,transparent),transparent_60%)]"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-[0.05] [background-image:linear-gradient(to_right,white_1px,transparent_1px),linear-gradient(to_bottom,white_1px,transparent_1px)] [background-size:40px_40px]"
      />

      <div className="relative z-10 flex w-full max-w-md flex-col items-center">
        <div className="mb-8 flex flex-col items-center gap-4">
          <div className="flex size-16 items-center justify-center rounded-2xl border border-border bg-card shadow-[0_0_40px_-8px_color-mix(in_oklch,var(--primary)_60%,transparent)]">
            <Image src="/images/viper-logo.png" alt="" width={40} height={40} className="size-10" />
          </div>
          <div className="text-center">
            <h1 className="text-balance font-sans text-2xl font-semibold tracking-tight text-foreground">
              Viper Audio Core
            </h1>
            <p className="mt-2 text-pretty text-sm leading-relaxed text-muted-foreground">
              Connect your Discord account to manage your server playback.
            </p>
          </div>
        </div>

        <div className="w-full rounded-2xl border border-border bg-card p-6 shadow-2xl">
          <Button
            onClick={onLogin}
            size="lg"
            className="w-full gap-3 bg-primary text-primary-foreground shadow-[0_0_28px_-6px_color-mix(in_oklch,var(--primary)_70%,transparent)] hover:bg-primary/90"
          >
            <DiscordMark className="size-5" />
            Login with Discord
          </Button>
          <p className="mt-4 text-center text-xs leading-relaxed text-muted-foreground">
            By continuing you agree to grant voice channel and playback permissions.
          </p>
        </div>

        <div className="mt-8 grid w-full grid-cols-1 gap-3 sm:grid-cols-3">
          {features.map((feature) => (
            <div
              key={feature.title}
              className="flex flex-col gap-2 rounded-xl border border-border bg-card/60 p-4"
            >
              <feature.icon className="size-5 text-accent" aria-hidden />
              <p className="text-sm font-medium text-foreground">{feature.title}</p>
              <p className="text-xs leading-relaxed text-muted-foreground">{feature.description}</p>
            </div>
          ))}
        </div>
      </div>
    </main>
  )
}

function DiscordMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 127.14 96.36" className={className} fill="currentColor" aria-hidden="true">
      <path d="M107.7,8.07A105.15,105.15,0,0,0,81.47,0a72.06,72.06,0,0,0-3.36,6.83A97.68,97.68,0,0,0,49,6.83,72.37,72.37,0,0,0,45.64,0,105.89,105.89,0,0,0,19.39,8.09C2.79,32.65-1.71,56.6.54,80.21h0A105.73,105.73,0,0,0,32.71,96.36,77.7,77.7,0,0,0,39.6,85.25a68.42,68.42,0,0,1-10.85-5.18c.91-.66,1.8-1.34,2.66-2a75.57,75.57,0,0,0,64.32,0c.87.71,1.76,1.39,2.66,2a68.68,68.68,0,0,1-10.87,5.19,77,77,0,0,0,6.89,11.1A105.25,105.25,0,0,0,126.6,80.22h0C129.24,52.84,122.09,29.11,107.7,8.07ZM42.45,65.69C36.18,65.69,31,60,31,53s5-12.74,11.43-12.74S54,46,53.89,53,48.84,65.69,42.45,65.69Zm42.24,0C78.41,65.69,73.25,60,73.25,53s5-12.74,11.44-12.74S96.23,46,96.12,53,91.08,65.69,84.69,65.69Z" />
    </svg>
  )
}

"use client"

const BAR_COUNT = 32

export function WaveVisualizer({ playing = true }: { playing?: boolean }) {
  return (
    <div
      className="flex h-12 items-center gap-[3px]"
      role="img"
      aria-label={playing ? "Audio waveform, currently playing" : "Audio waveform, paused"}
    >
      {Array.from({ length: BAR_COUNT }).map((_, i) => {
        const baseHeight = 20 + Math.abs(Math.sin(i * 0.7)) * 70
        return (
          <span
            key={i}
            className="w-[3px] rounded-full bg-accent/70"
            style={{
              height: `${baseHeight}%`,
              animation: playing ? `wave-pulse 1.1s ease-in-out ${i * 0.035}s infinite` : "none",
              opacity: playing ? 1 : 0.35,
            }}
          />
        )
      })}
      <style jsx>{`
        @keyframes wave-pulse {
          0%,
          100% {
            transform: scaleY(0.35);
          }
          50% {
            transform: scaleY(1);
          }
        }
      `}</style>
    </div>
  )
}

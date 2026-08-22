export type Track = {
  id: string
  title: string
  artist: string
  duration: string
  durationSeconds: number
  cover: string
  requestedBy?: string
  timesPlayed?: number
  tags?: string[]
}

export const servers = [
  { id: "s1", name: "My Community Server #1", members: 1284 },
  { id: "s2", name: "Late Night Lo-Fi Lounge", members: 342 },
  { id: "s3", name: "Ranked Grind Squad", members: 89 },
]

export const nowPlaying: Track = {
  id: "np-1",
  title: "Neon Skyline",
  artist: "Kaito Volt",
  duration: "3:45",
  durationSeconds: 225,
  cover: "/images/album-1.png",
  requestedBy: "@shadowbyte",
}

export const currentProgressSeconds = 134

export const queue: Track[] = [
  {
    id: "q-1",
    title: "Glass Static",
    artist: "Mira Wolfe",
    duration: "4:02",
    durationSeconds: 242,
    cover: "/images/album-2.png",
    requestedBy: "@nyxa",
  },
  {
    id: "q-2",
    title: "Paper Moon",
    artist: "Yuji Sano",
    duration: "2:58",
    durationSeconds: 178,
    cover: "/images/album-3.png",
    requestedBy: "@driftkid",
  },
  {
    id: "q-3",
    title: "Skull Cartel",
    artist: "Reaper Rex",
    duration: "3:21",
    durationSeconds: 201,
    cover: "/images/album-4.png",
    requestedBy: "@vantablack",
  },
  {
    id: "q-4",
    title: "8-Bit Ascension",
    artist: "Pixel Ronin",
    duration: "3:07",
    durationSeconds: 187,
    cover: "/images/album-5.png",
    requestedBy: "@retrograde",
  },
  {
    id: "q-5",
    title: "Cloud Drift",
    artist: "Sable Rae",
    duration: "5:14",
    durationSeconds: 314,
    cover: "/images/album-6.png",
    requestedBy: "@nyxa",
  },
]

export const botStats = {
  connectedServers: 42,
  latencyMs: 19,
  ramUsedGb: 2.4,
  ramTotalGb: 8,
  cpuLoadPercent: 34,
}

export const library: Track[] = [
  {
    id: "l-1",
    title: "Neon Skyline",
    artist: "Kaito Volt",
    duration: "3:45",
    durationSeconds: 225,
    cover: "/images/album-1.png",
    timesPlayed: 128,
    tags: ["Favorites"],
  },
  {
    id: "l-2",
    title: "Glass Static",
    artist: "Mira Wolfe",
    duration: "4:02",
    durationSeconds: 242,
    cover: "/images/album-2.png",
    timesPlayed: 76,
    tags: ["Recently Played"],
  },
  {
    id: "l-3",
    title: "Paper Moon",
    artist: "Yuji Sano",
    duration: "2:58",
    durationSeconds: 178,
    cover: "/images/album-3.png",
    timesPlayed: 41,
    tags: ["Favorites", "Recently Played"],
  },
  {
    id: "l-4",
    title: "Skull Cartel",
    artist: "Reaper Rex",
    duration: "3:21",
    durationSeconds: 201,
    cover: "/images/album-4.png",
    timesPlayed: 213,
    tags: ["Bass Boosted"],
  },
  {
    id: "l-5",
    title: "8-Bit Ascension",
    artist: "Pixel Ronin",
    duration: "3:07",
    durationSeconds: 187,
    cover: "/images/album-5.png",
    timesPlayed: 302,
    tags: ["Gaming Tracks", "Favorites"],
  },
  {
    id: "l-6",
    title: "Cloud Drift",
    artist: "Sable Rae",
    duration: "5:14",
    durationSeconds: 314,
    cover: "/images/album-6.png",
    timesPlayed: 19,
    tags: ["Recently Played"],
  },
  {
    id: "l-7",
    title: "Sub Zero Cartel",
    artist: "Reaper Rex",
    duration: "3:33",
    durationSeconds: 213,
    cover: "/images/album-4.png",
    timesPlayed: 154,
    tags: ["Bass Boosted"],
  },
  {
    id: "l-8",
    title: "Respawn Anthem",
    artist: "Pixel Ronin",
    duration: "2:41",
    durationSeconds: 161,
    cover: "/images/album-5.png",
    timesPlayed: 88,
    tags: ["Gaming Tracks"],
  },
]

export const filterTags = ["Favorites", "Bass Boosted", "Gaming Tracks", "Recently Played"] as const

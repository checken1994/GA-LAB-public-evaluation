"use client"

import dynamic from "next/dynamic"

const ScpOverview = dynamic(
  () => import("@/components/dashboard/scp-overview").then((mod) => mod.ScpOverview),
  {
    ssr: false,
    loading: () => (
      <div className="flex min-h-screen items-center justify-center bg-[#07111f] text-cyan-300">
        <div className="text-center">
          <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-2 border-cyan-400 border-t-transparent" />
          <p className="font-mono text-sm tracking-widest uppercase">Đang nạp Trung tâm điều khiển SCP...</p>
        </div>
      </div>
    ),
  }
)

export default function HomePage() {
  return <ScpOverview />
}

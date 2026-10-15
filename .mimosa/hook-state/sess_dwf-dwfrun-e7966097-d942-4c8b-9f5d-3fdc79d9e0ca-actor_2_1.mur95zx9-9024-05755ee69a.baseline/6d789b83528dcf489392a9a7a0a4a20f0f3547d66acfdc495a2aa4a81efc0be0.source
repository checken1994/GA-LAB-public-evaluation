import os from "node:os"
import { NextResponse } from "next/server"

export const dynamic = "force-dynamic"

function cpuSnapshot() {
  const cpus = os.cpus()
  let idle = 0
  let total = 0
  for (const cpu of cpus) {
    idle += cpu.times.idle
    total += cpu.times.user + cpu.times.nice + cpu.times.sys + cpu.times.idle + cpu.times.irq
  }
  return { idle, total, cores: cpus.length }
}

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export async function GET() {
  const before = cpuSnapshot()
  await sleep(160)
  const after = cpuSnapshot()
  const idleDelta = after.idle - before.idle
  const totalDelta = after.total - before.total
  const cpuPercent = totalDelta > 0 ? Math.max(0, Math.min(100, (1 - idleDelta / totalDelta) * 100)) : 0
  const totalMemory = os.totalmem()
  const freeMemory = os.freemem()
  const memoryPercent = totalMemory > 0 ? Math.max(0, Math.min(100, (1 - freeMemory / totalMemory) * 100)) : 0
  const loadPercent = Math.max(cpuPercent, memoryPercent)

  return NextResponse.json(
    {
      checkedAt: new Date().toISOString(),
      cpuPercent: Math.round(cpuPercent * 10) / 10,
      memoryPercent: Math.round(memoryPercent * 10) / 10,
      loadPercent: Math.round(loadPercent * 10) / 10,
      cores: after.cores,
      totalMemoryBytes: totalMemory,
      freeMemoryBytes: freeMemory,
      host: "SCP Desktop host",
    },
    { headers: { "Cache-Control": "no-store" } },
  )
}

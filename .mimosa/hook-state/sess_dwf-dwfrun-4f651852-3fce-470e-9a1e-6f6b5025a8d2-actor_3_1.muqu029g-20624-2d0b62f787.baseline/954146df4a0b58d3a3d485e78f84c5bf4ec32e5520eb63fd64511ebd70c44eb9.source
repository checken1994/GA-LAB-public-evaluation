import * as React from "react"

/**
 * useIsMobile — React 19 idiom via useSyncExternalStore.
 *
 * R8 fix for SA-R8-1 (CRITICAL, DNA #22): R7-Full's own self-audit documented
 * the "0 lint errors" claim as TRUE, but `bun run lint` returned 2 errors —
 * one in carousel.tsx:98 (deleted — unused) and one here at use-mobile.ts:14
 * (`react-hooks/set-state-in-effect`: setState inside useEffect). R7-Full
 * committed the exact bug class its SA-1 finding raised against R7.
 *
 * R8 makes the "0 lint errors" claim genuinely TRUE by switching to
 * useSyncExternalStore (the same idiom header.tsx uses for the theme store).
 * No setState in effect; the snapshot is read from matchMedia directly.
 */
const MOBILE_BREAKPOINT = 768

function subscribeMobile(cb: () => void) {
  const mql = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT - 1}px)`)
  mql.addEventListener("change", cb)
  return () => mql.removeEventListener("change", cb)
}

function readMobile(): boolean {
  return window.innerWidth < MOBILE_BREAKPOINT
}

function readMobileServer(): boolean {
  // Server snapshot — default to false (desktop). The inline theme script in
  // layout.tsx runs before hydration; mobile layout adjusts post-hydration.
  return false
}

export function useIsMobile() {
  const isMobile = React.useSyncExternalStore(
    subscribeMobile,
    readMobile,
    readMobileServer
  )
  return isMobile
}

/**
 * Dashboard database facade.
 *
 * The current SCP dashboard has no Prisma schema or database-backed route.
 * Keep this module explicit and fail-closed instead of importing a generated
 * Prisma client that does not exist in a clean checkout. A future database
 * feature must add schema.prisma, run `prisma generate`, and replace this
 * facade in the same change.
 */
export type DashboardDatabaseUnavailable = {
  readonly unavailable: true
  readonly reason: "PRISMA_SCHEMA_NOT_CONFIGURED"
}

export const db: DashboardDatabaseUnavailable = {
  unavailable: true,
  reason: "PRISMA_SCHEMA_NOT_CONFIGURED",
}

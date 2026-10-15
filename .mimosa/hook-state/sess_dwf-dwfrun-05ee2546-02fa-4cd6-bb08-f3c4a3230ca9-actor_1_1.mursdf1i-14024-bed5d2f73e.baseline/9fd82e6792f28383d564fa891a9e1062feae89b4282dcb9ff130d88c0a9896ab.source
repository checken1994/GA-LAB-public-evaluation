const fs = require("fs")
const path = require("path")

const root = path.resolve(__dirname, "..")
const staticSrc = path.join(root, ".next", "static")
const staticDest = path.join(root, ".next", "standalone", ".next", "static")
const publicSrc = path.join(root, "public")
const publicDest = path.join(root, ".next", "standalone", "public")

try {
  if (fs.existsSync(staticSrc)) {
    fs.mkdirSync(path.dirname(staticDest), { recursive: true })
    fs.cpSync(staticSrc, staticDest, { recursive: true, force: true })
    console.log("[copy-standalone-assets] Copied .next/static -> .next/standalone/.next/static")
  }
  if (fs.existsSync(publicSrc)) {
    fs.mkdirSync(path.dirname(publicDest), { recursive: true })
    fs.cpSync(publicSrc, publicDest, { recursive: true, force: true })
    console.log("[copy-standalone-assets] Copied public -> .next/standalone/public")
  }
} catch (err) {
  console.error("[copy-standalone-assets] Error copying standalone assets:", err)
  process.exit(1)
}

// Lightweight read-only viewer for the multi-agent campaign dashboard.
// Serves .openclaw/multi-agent/*.html + status.js on loopback only (DNA #6).
const ROOT = "D:/scp/.openclaw/multi-agent";
const PORT = Number(process.env.SCP_VIEWER_PORT || 8099);

Bun.serve({
  port: PORT,
  hostname: "127.0.0.1",
  fetch(req) {
    const url = new URL(req.url);
    let path = url.pathname === "/" ? "/dashboard.html" : url.pathname;
    path = path.replace(/\\/g, "/").replace(/\.\./g, ""); // traversal guard
    const file = Bun.file(ROOT + path);
    return new Response(file, {
      headers: { "content-type": path.endsWith(".js") ? "text/javascript; charset=utf-8" : "text/html; charset=utf-8" },
    });
  },
});
console.log(`[scp-agent-viewer] serving ${ROOT} at http://127.0.0.1:${PORT}/ (loopback only)`);

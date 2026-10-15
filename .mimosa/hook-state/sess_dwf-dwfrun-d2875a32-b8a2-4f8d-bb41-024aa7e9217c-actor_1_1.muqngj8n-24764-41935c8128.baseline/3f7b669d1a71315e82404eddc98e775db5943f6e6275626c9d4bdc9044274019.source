"""
[Task 8-A] Dashboard HTML constant — extracted from api_server.py

TẠI SAO: api_server.py god file. Tách DASHBOARD_HTML (275 LOC HTML string)
vào module riêng. Backward-compatible — api_server re-exports DASHBOARD_HTML.
"""

# ============================================================
# Dashboard HTML
# ============================================================
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SCP Chat — Self-Correcting Pipeline</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Inter', system-ui, sans-serif; background: #0a0a0a; color: #e0e0e0; height: 100vh; display: flex; flex-direction: column; }

/* Header */
.header { background: #111; padding: 12px 24px; display: flex; align-items: center; gap: 12px; border-bottom: 1px solid #222; }
.header h1 { font-size: 18px; font-weight: 700; color: #fff; }
.header .sub { font-size: 11px; color: #666; }
.header .status-dot { width: 8px; height: 8px; border-radius: 50%; background: #3fb950; animation: pulse 2s infinite; }
.header .stats-btn { margin-left: auto; padding: 6px 16px; background: #1a1a1a; color: #888; border: 1px solid #333; border-radius: 6px; cursor: pointer; font-size: 12px; }
.header .stats-btn:hover { background: #222; color: #fff; }

/* Chat area */
.chat-container { flex: 1; overflow-y: auto; padding: 20px; max-width: 900px; width: 100%; margin: 0 auto; }
.message { margin-bottom: 16px; display: flex; gap: 12px; }
.message.user { flex-direction: row-reverse; }
.message .avatar { width: 36px; height: 36px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 18px; flex-shrink: 0; }
.message.user .avatar { background: #7f1d1d; }
.message.scp .avatar { background: #1e3a5f; }
.message .bubble { max-width: 70%; padding: 12px 16px; border-radius: 12px; font-size: 14px; line-height: 1.6; }
.message.user .bubble { background: #7f1d1d; color: #fff; }
.message.scp .bubble { background: #1a1a1a; border: 1px solid #333; }
.message.scp .verdict { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; margin-bottom: 6px; }
.verdict.PASS { background: #1a4731; color: #3fb950; }
.verdict.FAIL { background: #4a1e1e; color: #f85149; }
.verdict.UNKNOWN { background: #4a381e; color: #f0883e; }
.verdict.CONFLICT { background: #4a1e1e; color: #f85149; }
.verdict.SPECULATIVE { background: #4a381e; color: #f0883e; }
.message.scp .meta { font-size: 11px; color: #666; margin-top: 6px; }
.message.scp .evidence { margin-top: 8px; padding: 8px; background: #0d0d0d; border-radius: 6px; font-size: 12px; color: #888; max-height: 150px; overflow-y: auto; }

/* Input area */
.input-area { padding: 16px 24px; background: #111; border-top: 1px solid #222; }
.input-wrapper { max-width: 900px; margin: 0 auto; display: flex; gap: 12px; align-items: center; }
.input-wrapper input { flex: 1; padding: 14px 18px; background: #1a1a1a; color: #fff; border: 1px solid #333; border-radius: 12px; font-size: 14px; outline: none; transition: border 0.2s; }
.input-wrapper input:focus { border-color: #2563eb; }
.input-wrapper input::placeholder { color: #555; }
.input-wrapper button { padding: 14px 28px; background: #2563eb; color: #fff; border: none; border-radius: 12px; font-size: 14px; font-weight: 600; cursor: pointer; transition: background 0.2s; }
.input-wrapper button:hover { background: #1d4ed8; }
.input-wrapper button:disabled { background: #333; cursor: not-allowed; }
.input-wrapper .domain-select { padding: 10px; background: #1a1a1a; color: #888; border: 1px solid #333; border-radius: 8px; font-size: 12px; }
.input-wrapper .media-btn { padding: 12px 14px; background: #242424; color: #ddd; border: 1px solid #444; border-radius: 10px; cursor: pointer; font-size: 13px; }
.input-wrapper .media-btn.active { background: #7f1d1d; border-color: #f85149; }
#cameraPanel { display: none; max-width: 900px; margin: 10px auto 0; padding: 10px; background: #181818; border: 1px solid #333; border-radius: 10px; }
#cameraPanel.active { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
#cameraPreview { width: 220px; max-height: 165px; background: #000; border-radius: 8px; }
#mediaStatus { color: #aaa; font-size: 12px; }

/* Loading */
.typing { display: inline-block; animation: bounce 1.4s infinite; }
.typing:nth-child(2) { animation-delay: 0.2s; }
.typing:nth-child(3) { animation-delay: 0.4s; }

/* Stats modal */
.stats-modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 100; justify-content: center; align-items: center; }
.stats-modal.active { display: flex; }
.stats-content { background: #111; border-radius: 12px; padding: 24px; max-width: 800px; width: 90%; max-height: 80vh; overflow-y: auto; border: 1px solid #333; }
.stats-content h2 { color: #58a6ff; margin-bottom: 16px; }
.stats-content .close { float: right; cursor: pointer; color: #666; font-size: 24px; }
.stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.stats-card { background: #1a1a1a; padding: 16px; border-radius: 8px; border: 1px solid #222; }
.stats-card h3 { font-size: 11px; color: #888; text-transform: uppercase; margin-bottom: 8px; }
.stats-card .val { font-size: 28px; font-weight: 700; color: #fff; }

/* [Task 37-C] AutoFix Monitor — dark-theme stat row + progress bar + tables */
.monitor-stat-row { display: flex; flex-wrap: wrap; gap: 10px; margin: 12px 0; }
.monitor-stat { background: #1a1a1a; border: 1px solid #222; border-radius: 8px; padding: 12px 16px; min-width: 140px; text-align: center; flex: 1; }
.monitor-stat .lbl { display: block; color: #888; font-size: 11px; text-transform: uppercase; margin-bottom: 6px; letter-spacing: 0.5px; }
.monitor-stat .num { display: block; font-size: 22px; font-weight: 700; color: #fff; }
.monitor-stat .num.ok { color: #3fb950; }
.monitor-stat .num.err { color: #f85149; }
.progress-bar { background: #0d0d0d; border-radius: 4px; height: 6px; margin-top: 8px; overflow: hidden; border: 1px solid #222; }
.progress-fill { background: linear-gradient(90deg, #1f6f3c, #3fb950); height: 100%; transition: width 0.5s ease; }
.progress-fill.low { background: linear-gradient(90deg, #6e2b2b, #f85149); }
.monitor-table { width: 100%; border-collapse: collapse; margin: 8px 0 16px 0; font-size: 12px; }
.monitor-table caption { caption-side: top; text-align: left; color: #58a6ff; font-size: 13px; font-weight: 600; margin-bottom: 6px; padding: 0; }
.monitor-table th { background: #161616; color: #888; font-weight: 600; text-transform: uppercase; font-size: 10px; letter-spacing: 0.5px; padding: 8px 10px; text-align: left; border-bottom: 1px solid #333; }
.monitor-table td { padding: 7px 10px; border-bottom: 1px solid #1f1f1f; color: #e0e0e0; }
.monitor-table tr:hover td { background: #181818; }
.monitor-table .ok-cell { color: #3fb950; }
.monitor-table .err-cell { color: #f85149; }
.monitor-empty { color: #666; font-style: italic; padding: 12px; text-align: center; }
.monitor-section { margin-top: 20px; }

@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
@keyframes bounce { 0%, 60%, 100% { transform: translateY(0); } 30% { transform: translateY(-8px); } }
</style>
</head>
<body>

<div class="header">
  <span class="status-dot"></span>
  <div>
    <h1>🐔 SCP Chat</h1>
    <div class="sub">Self-Correcting Pipeline · Reality > Model · PASS ≠ ĐÚNG</div>
  </div>
  <button class="stats-btn" onclick="toggleStats()">📊 Stats</button>
</div>

<div class="chat-container" id="chat">
  <div class="message scp">
    <div class="avatar">🤖</div>
    <div class="bubble">
      Xin chào! Tôi là SCP — Self-Correcting Pipeline.<br>
      Hỏi tôi bất cứ câu hỏi nào. Tôi sẽ kiểm chứng và trả verdict: <b>PASS</b> / <b>UNKNOWN</b> / <b>FAIL</b>.<br><br>
      <span style="color:#666;font-size:12px;">Reality > Model. WHY = chốt kiểm soát.</span>
    </div>
  </div>
</div>

<div class="input-area">
  <div class="input-wrapper">
    <select class="domain-select" id="domain">
      <option value="general">Tự động</option>
      <option value="geography">Địa lý</option>
      <option value="medical">Y tế</option>
      <option value="cybersecurity">An ninh mạng</option>
      <option value="geology">Địa chất</option>
      <option value="math">Toán</option>
      <option value="physics">Vật lý</option>
      <option value="chemistry">Hóa học</option>
      <option value="history">Lịch sử</option>
      <option value="biology">Sinh học</option>
    </select>
    <input type="text" id="input" placeholder="Nhập câu hỏi..." onkeypress="if(event.key==='Enter')send()">
    <button id="sendBtn" onclick="send()">Gửi</button>
    <button id="micBtn" class="media-btn" onclick="toggleMic()" title="Bấm để nói, bấm lại để dừng">🎙 Mic</button>
    <button id="cameraBtn" class="media-btn" onclick="openCamera()" title="Chỉ bật webcam sau khi bấm">📷 Camera</button>
  </div>
  <div id="cameraPanel">
    <video id="cameraPreview" autoplay muted playsinline></video>
    <button class="media-btn" onclick="captureImage()">Chụp ảnh</button>
    <button class="media-btn" onclick="closeCamera()">Tắt camera</button>
    <span id="mediaStatus">Camera chỉ hoạt động sau khi bạn bấm nút.</span>
  </div>
</div>

<!-- Stats Modal -->
<div class="stats-modal" id="statsModal">
  <div class="stats-content">
    <span class="close" onclick="toggleStats()">&times;</span>
    <h2>SCP System Stats</h2>
    <div class="stats-grid" id="statsGrid">Loading...</div>
    <h2 style="margin-top:24px;">V98 Security</h2>
    <div class="stats-grid" id="v98Grid">Loading...</div>

    <!-- [Task 37-C] AutoFix Monitor Section -->
    <h2 style="margin-top:24px;">🔧 AutoFix Monitor</h2>
    <div class="monitor-stat-row" id="autofixStatRow">
      <div class="monitor-stat"><span class="lbl">Total Attempts</span><span class="num" id="monitor-total">—</span></div>
      <div class="monitor-stat"><span class="lbl">Success Rate</span><span class="num" id="monitor-success-rate">—</span><div class="progress-bar"><div class="progress-fill" id="monitor-success-bar" style="width:0%"></div></div></div>
      <div class="monitor-stat"><span class="lbl">Successes</span><span class="num ok" id="monitor-successes">—</span></div>
      <div class="monitor-stat"><span class="lbl">Errors</span><span class="num err" id="monitor-errors">—</span></div>
    </div>
    <div class="monitor-section">
      <table class="monitor-table">
        <caption>By Bug Type</caption>
        <thead><tr><th>Bug Type</th><th>Total</th><th>Success</th><th>Failure</th><th>Rate</th></tr></thead>
        <tbody id="monitor-by-bug-type"><tr><td colspan="5" class="monitor-empty">Loading…</td></tr></tbody>
      </table>
    </div>
    <div class="monitor-section">
      <table class="monitor-table">
        <caption>By Provider</caption>
        <thead><tr><th>Provider</th><th>Total</th><th>Success</th><th>Rate</th></tr></thead>
        <tbody id="monitor-by-provider"><tr><td colspan="4" class="monitor-empty">Loading…</td></tr></tbody>
      </table>
    </div>
    <div class="monitor-section">
      <table class="monitor-table">
        <caption>By Diagnosis</caption>
        <thead><tr><th>Diagnosis</th><th>Count</th></tr></thead>
        <tbody id="monitor-by-diagnosis"><tr><td colspan="2" class="monitor-empty">Loading…</td></tr></tbody>
      </table>
    </div>
    <div class="monitor-section">
      <table class="monitor-table">
        <caption>Recent Attempts (last 10)</caption>
        <thead><tr><th>Bug ID</th><th>Bug Type</th><th>Provider</th><th>Diagnosis</th><th>Elapsed</th><th>Result</th></tr></thead>
        <tbody id="monitor-recent"><tr><td colspan="6" class="monitor-empty">Loading…</td></tr></tbody>
      </table>
    </div>
  </div>
</div>

<script>
const TOKEN = (() => {
  // [RC-2 FIX Task 6-A] Hardcoded fallback token REMOVED — was a production
  // secret shipped in client-side JS (CODE-AUDIT-001 CRITICAL leak). Now the
  // dashboard REQUIRES a `?token=...` URL parameter. Operators must provision
  // a real token via .env (SCP_AUTH_TOKEN_SECRET) and pass it in the URL.
  const params = new URLSearchParams(location.search);
  const t = params.get('token');
  if (!t) {
    document.addEventListener('DOMContentLoaded', () => {
      document.body.insertAdjacentHTML('afterbegin',
        '<div style="background:#b91c1c;color:white;padding:12px;font-family:sans-serif;">' +
        'SCP: missing <code>?token=...</code> URL parameter. ' +
        'Set SCP_AUTH_TOKEN_SECRET in .env and reload with <code>?token=&lt;your-token&gt;</code>.' +
        '</div>');
    });
    return '';
  }
  return t;
})();

let isSending = false;
let pendingImageData = null;
const SESSION_ID = (() => {
  const key = 'scp-chat-session-id';
  try {
    const old = sessionStorage.getItem(key);
    if (old) return old;
    const fresh = (crypto.randomUUID ? crypto.randomUUID() : String(Date.now()) + '-' + Math.random());
    sessionStorage.setItem(key, fresh);
    return fresh;
  } catch (_) {
    return String(Date.now());
  }
})();
let conversationHistory = [];
let cameraStream = null;
let speechRecognition = null;

function addMsg(text, type, meta) {
  const chat = document.getElementById('chat');
  const div = document.createElement('div');
  div.className = 'message ' + type;

  const avatar = type === 'user' ? '🐔' : '🤖';
  let bubbleHTML = '';

  if (type === 'user') {
    bubbleHTML = escapeHtml(text);
  } else {
    // SCP response
    const v = meta?.verdict || '?';
    const conf = meta ? (meta.confidence * 100).toFixed(0) : '?';
    const answer = meta?.final_answer || text;
    const domain = meta?.domain || '?';
    const elapsed = meta?.elapsed_ms ? meta.elapsed_ms.toFixed(0) : '?';

    let verdictClass = v;
    if (!['PASS','FAIL','UNKNOWN','CONFLICT','SPECULATIVE'].includes(v)) verdictClass = 'UNKNOWN';

    bubbleHTML = `<span class="verdict ${verdictClass}">${v} · ${conf}%</span>`;
    bubbleHTML += `<br>${escapeHtml(answer)}`;

    if (meta?.reasoning) {
      bubbleHTML += `<div class="evidence">💡 ${escapeHtml(meta.reasoning.substring(0, 200))}</div>`;
    }

    bubbleHTML += `<div class="meta">📁 ${domain} · ⏱ ${elapsed}ms · 🔑 ${meta?.session_id?.substring(0,8) || '?'}</div>`;
  }

  div.innerHTML = `<div class="avatar">${avatar}</div><div class="bubble">${bubbleHTML}</div>`;
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML.replace(/\\n/g, '<br>');
}

async function send() {
  const input = document.getElementById('input');
  const question = input.value.trim();
  if (!question || isSending) return;

  const domain = document.getElementById('domain').value;

  addMsg(question, 'user');
  conversationHistory.push({ role: 'user', content: question });
  conversationHistory = conversationHistory.slice(-8);
  input.value = '';
  isSending = true;

  const btn = document.getElementById('sendBtn');
  btn.disabled = true;
  btn.textContent = '...';

  // Typing indicator
  const chat = document.getElementById('chat');
  const typing = document.createElement('div');
  typing.className = 'message scp';
  typing.id = 'typing';
  typing.innerHTML = '<div class="avatar">🤖</div><div class="bubble"><span class="typing">●</span><span class="typing">●</span><span class="typing">●</span></div>';
  chat.appendChild(typing);
  chat.scrollTop = chat.scrollHeight;

  try {
    const res = await fetch('/ask', {
      method: 'POST',
      headers: {
        'Authorization': 'Bearer ' + TOKEN,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        question: question,
        domain: domain,
        ai_answer: '',
        session_id: SESSION_ID,
        conversation_history: conversationHistory.slice(-8),
        image_data: pendingImageData
      })
    });

    const data = await res.json();
    document.getElementById('typing')?.remove();
    addMsg(data.final_answer || '[No answer]', 'scp', data);
    conversationHistory.push({ role: 'assistant', content: data.final_answer || '' });
    conversationHistory = conversationHistory.slice(-8);
    pendingImageData = null;
    closeCamera();

  } catch(e) {
    document.getElementById('typing')?.remove();
    addMsg('❌ Lỗi kết nối: ' + e.message, 'scp', { verdict: 'FAIL', confidence: 0, final_answer: e.message, domain: 'error', elapsed_ms: 0 });
  }

  isSending = false;
  btn.disabled = false;
  btn.textContent = 'Gửi';
  input.focus();
}

function toggleMic() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const btn = document.getElementById('micBtn');
  if (!SpeechRecognition) {
    document.getElementById('mediaStatus').textContent = 'Trình duyệt này không hỗ trợ nhận giọng nói.';
    return;
  }
  if (speechRecognition) {
    speechRecognition.stop();
    speechRecognition = null;
    btn.classList.remove('active');
    btn.textContent = '🎙 Mic';
    return;
  }
  speechRecognition = new SpeechRecognition();
  speechRecognition.lang = 'vi-VN';
  speechRecognition.interimResults = false;
  speechRecognition.continuous = false;
  speechRecognition.onstart = () => { btn.classList.add('active'); btn.textContent = '⏹ Dừng mic'; document.getElementById('mediaStatus').textContent = 'Đang nghe một câu. Bấm lại để dừng.'; };
  speechRecognition.onresult = (event) => { document.getElementById('input').value = event.results[0][0].transcript; };
  speechRecognition.onerror = (event) => { document.getElementById('mediaStatus').textContent = 'Mic lỗi: ' + event.error; };
  speechRecognition.onend = () => { speechRecognition = null; btn.classList.remove('active'); btn.textContent = '🎙 Mic'; };
  speechRecognition.start();
}

async function openCamera() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    document.getElementById('mediaStatus').textContent = 'Trình duyệt không hỗ trợ webcam.';
    return;
  }
  try {
    cameraStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    document.getElementById('cameraPreview').srcObject = cameraStream;
    document.getElementById('cameraPanel').classList.add('active');
    document.getElementById('cameraBtn').classList.add('active');
    document.getElementById('mediaStatus').textContent = 'Webcam đang bật. Chỉ chụp khi bạn bấm Chụp ảnh.';
  } catch (error) {
    document.getElementById('mediaStatus').textContent = 'Không mở được webcam: ' + error.name;
  }
}

function closeCamera() {
  if (cameraStream) cameraStream.getTracks().forEach((track) => track.stop());
  cameraStream = null;
  const preview = document.getElementById('cameraPreview');
  if (preview) preview.srcObject = null;
  document.getElementById('cameraPanel')?.classList.remove('active');
  document.getElementById('cameraBtn')?.classList.remove('active');
}

function captureImage() {
  if (!cameraStream) return;
  const video = document.getElementById('cameraPreview');
  const canvas = document.createElement('canvas');
  canvas.width = video.videoWidth || 640;
  canvas.height = video.videoHeight || 480;
  canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
  pendingImageData = canvas.toDataURL('image/jpeg', 0.82);
  document.getElementById('mediaStatus').textContent = 'Đã chụp ảnh. Ảnh sẽ gửi cùng câu hỏi tiếp theo.';
  closeCamera();
}

// Stats
let statsOpen = false;
function toggleStats() {
  statsOpen = !statsOpen;
  document.getElementById('statsModal').classList.toggle('active', statsOpen);
  if (statsOpen) loadStats();
}

async function loadStats() {
  // [Task 37-C] Load AutoFix monitor in parallel with existing stats — failures
  // are non-fatal (monitor is additive; existing sections still render).
  loadAutoFixMonitor().catch(e => console.error('AutoFix monitor:', e));
  try {
    const [health, status] = await Promise.all([
      fetch('/health').then(r => r.json()),
      fetch('/v98/status').then(r => r.json())
    ]);

    document.getElementById('statsGrid').innerHTML = `
      <div class="stats-card"><h3>Version</h3><div class="val" style="font-size:16px">${health.version}</div></div>
      <div class="stats-card"><h3>SLMs</h3><div class="val">${health.slms}</div></div>
      <div class="stats-card"><h3>V98 Modules</h3><div class="val">${health.v98_modules}</div></div>
      <div class="stats-card"><h3>Routes</h3><div class="val">${health.routes}</div></div>
      <div class="stats-card"><h3>Data Size</h3><div class="val">${health.data_size_mb?.toFixed(1) || '?'}MB</div></div>
      <div class="stats-card"><h3>Status</h3><div class="val" style="color:#3fb950;font-size:16px">● ONLINE</div></div>
    `;

    let v98html = '';
    for (const [name, stat] of Object.entries(status.v98_modules || {})) {
      const active = stat !== 'inactive';
      v98html += `<div class="stats-card"><h3>${name}</h3><div class="val" style="font-size:14px;color:${active?'#3fb950':'#f0883e'}">${active?'● Active':'○ Inactive'}</div></div>`;
    }
    document.getElementById('v98Grid').innerHTML = v98html;
  } catch(e) {
    document.getElementById('statsGrid').innerHTML = '<div class="stats-card"><h3>Error</h3><div class="val" style="font-size:14px;color:#f85149">' + e.message + '</div></div>';
  }
}

// [Task 37-C] AutoFix Monitor — DNA SCP #8 KB accumulation: surface AutoFix
// performance (success rate, per-bug-type / per-provider / per-diagnosis
// breakdowns) in the admin dashboard. Wires to GET /v105/autofix/monitor
// (added in Task 36-A). Uses existing TOKEN constant (URL ?token=... param,
// not localStorage — RC-2 fix removed hardcoded client-side secrets).
async function loadAutoFixMonitor() {
  const $ = (id) => document.getElementById(id);
  const setTBody = (id, rows, emptyMsg) => {
    const tb = document.getElementById(id);
    if (!rows || rows.length === 0) {
      const span = tb.parentElement.querySelector('thead tr').children.length;
      tb.innerHTML = `<tr><td colspan="${span}" class="monitor-empty">${emptyMsg}</td></tr>`;
      return;
    }
    tb.innerHTML = rows.join('');
  };

  try {
    const res = await fetch('/v105/autofix/monitor', {
      headers: { 'Authorization': 'Bearer ' + TOKEN }
    });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();

    // Empty-state: monitor.get_stats() returns {total:0, message:...} when no
    // attempts recorded. Treat as zeroed stats (don't crash UI).
    const rawStats = data.stats || {};
    const stats = rawStats.total_attempts === undefined && rawStats.total === 0
      ? { total_attempts: 0, success_count: 0, failure_count: 0, success_rate: 0,
          by_bug_type: {}, by_provider: {}, by_diagnosis: {} }
      : rawStats;

    const total = stats.total_attempts || 0;
    const successCount = stats.success_count || 0;
    const failureCount = stats.failure_count || 0;
    const rate = stats.success_rate || 0;
    const ratePct = (rate * 100);

    $('monitor-total').textContent = total;
    $('monitor-success-rate').textContent = total > 0 ? ratePct.toFixed(1) + '%' : '—';
    $('monitor-successes').textContent = successCount;
    $('monitor-errors').textContent = failureCount;
    const bar = $('monitor-success-bar');
    bar.style.width = ratePct + '%';
    bar.classList.toggle('low', ratePct < 50);

    // By bug type
    const bugRows = Object.entries(stats.by_bug_type || {}).map(([type, s]) => {
      const t = s.total || 0; const su = s.success || 0;
      const r = t > 0 ? (su / t * 100).toFixed(0) + '%' : '—';
      return `<tr><td>${escapeHtml(type)}</td><td>${t}</td><td class="ok-cell">${su}</td><td class="err-cell">${s.failure || 0}</td><td>${r}</td></tr>`;
    });
    setTBody('monitor-by-bug-type', bugRows, 'No attempts recorded');

    // By provider
    const provRows = Object.entries(stats.by_provider || {}).map(([prov, s]) => {
      const t = s.total || 0; const su = s.success || 0;
      const r = (s.success_rate !== undefined) ? (s.success_rate * 100).toFixed(0) + '%' : (t > 0 ? (su/t*100).toFixed(0) + '%' : '—');
      return `<tr><td>${escapeHtml(prov)}</td><td>${t}</td><td class="ok-cell">${su}</td><td>${r}</td></tr>`;
    });
    setTBody('monitor-by-provider', provRows, 'No attempts recorded');

    // By diagnosis
    const diagRows = Object.entries(stats.by_diagnosis || {}).map(([diag, count]) =>
      `<tr><td>${escapeHtml(diag)}</td><td>${count}</td></tr>`
    );
    setTBody('monitor-by-diagnosis', diagRows, 'No attempts recorded');

    // Recent attempts
    const recent = data.recent_attempts || [];
    const recentRows = recent.map(a => {
      const elapsed = a.elapsed_ms ? a.elapsed_ms.toFixed(0) + 'ms' : '—';
      const okBadge = a.success ? '<span class="ok-cell">✓ PASS</span>' : '<span class="err-cell">✗ FAIL</span>';
      return `<tr><td>${escapeHtml(a.bug_id || '?')}</td><td>${escapeHtml(a.bug_type || '?')}</td><td>${escapeHtml(a.provider || '?')}</td><td>${escapeHtml(a.diagnosis || '?')}</td><td>${elapsed}</td><td>${okBadge}</td></tr>`;
    });
    setTBody('monitor-recent', recentRows, 'No recent attempts');
  } catch (e) {
    console.error('AutoFix monitor load error:', e);
    $('monitor-total').textContent = 'err';
    $('monitor-success-rate').textContent = 'err';
    $('monitor-successes').textContent = 'err';
    $('monitor-errors').textContent = 'err';
    const errMsg = 'Error: ' + escapeHtml(e.message);
    setTBody('monitor-by-bug-type', [], errMsg);
    setTBody('monitor-by-provider', [], errMsg);
    setTBody('monitor-by-diagnosis', [], errMsg);
    setTBody('monitor-recent', [], errMsg);
  }
}

// Auto-focus input
document.getElementById('input').focus();
</script>
</body>
</html>
"""

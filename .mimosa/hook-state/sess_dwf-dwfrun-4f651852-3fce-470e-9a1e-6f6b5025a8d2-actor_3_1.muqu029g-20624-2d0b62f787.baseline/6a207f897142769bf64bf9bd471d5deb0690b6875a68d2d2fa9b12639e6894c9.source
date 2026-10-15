"use client"

import { useCallback, useEffect, useRef, useState } from "react"

type JsonRecord = Record<string, unknown>

type ConversationState = "idle" | "starting" | "ready" | "recording" | "processing" | "speaking" | "error"

function asText(value: unknown, fallback = "") {
  return typeof value === "string" || typeof value === "number" ? String(value) : fallback
}

function getSpeechRecognitionSupport() {
  if (typeof window === "undefined") return false
  const browserWindow = window as Window & {
    SpeechRecognition?: new () => unknown
    webkitSpeechRecognition?: new () => unknown
  }
  return Boolean(browserWindow.SpeechRecognition || browserWindow.webkitSpeechRecognition)
}

export function VideoCallPanel() {
  const [state, setState] = useState<ConversationState>("idle")
  const [status, setStatus] = useState("Chưa bắt đầu cuộc nói chuyện")
  const [cameraEnabled, setCameraEnabled] = useState(false)
  const [micEnabled, setMicEnabled] = useState(false)
  const [transcript, setTranscript] = useState("")
  const [answer, setAnswer] = useState("")
  const [verdict, setVerdict] = useState("")
  const [speechOutput, setSpeechOutput] = useState(true)
  const [speechSupported, setSpeechSupported] = useState(false)
  const [conversationOn, setConversationOn] = useState(false)

  const videoRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const recorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const sessionIdRef = useRef("")
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null)

  const ensureSessionId = useCallback(() => {
    if (sessionIdRef.current) return sessionIdRef.current
    if (typeof window !== "undefined") {
      const key = "scp-desktop-chat-session-id"
      const old = window.sessionStorage.getItem(key)
      sessionIdRef.current = old || (window.crypto?.randomUUID?.() ?? `desktop-${Date.now()}`)
      window.sessionStorage.setItem(key, sessionIdRef.current)
    } else {
      sessionIdRef.current = `desktop-${Date.now()}`
    }
    return sessionIdRef.current
  }, [])

  const stopSpeech = useCallback(() => {
    if (typeof window !== "undefined" && "speechSynthesis" in window) window.speechSynthesis.cancel()
    utteranceRef.current = null
  }, [])

  const speakAnswer = useCallback((text: string) => {
    if (!speechOutput || !text.trim() || typeof window === "undefined" || !("speechSynthesis" in window)) return
    stopSpeech()
    const utterance = new SpeechSynthesisUtterance(text.slice(0, 4000))
    utterance.lang = "vi-VN"
    utterance.rate = 0.98
    utterance.pitch = 1
    utterance.onstart = () => { setState("speaking"); setStatus("SCP đang nói qua loa của PC…") }
    utterance.onend = () => { utteranceRef.current = null; setState("ready"); setStatus("SCP đã trả lời. Bạn có thể bấm mic để nói tiếp.") }
    utterance.onerror = () => { utteranceRef.current = null; setState("ready"); setStatus("Đã có câu trả lời, nhưng loa không đọc được. Bạn vẫn xem được chữ trên màn hình.") }
    utteranceRef.current = utterance
    window.speechSynthesis.speak(utterance)
  }, [speechOutput, stopSpeech])

  const stopConversation = useCallback(() => {
    recorderRef.current?.stop()
    recorderRef.current = null
    chunksRef.current = []
    stopSpeech()
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
    setConversationOn(false)
    if (videoRef.current) videoRef.current.srcObject = null
    setCameraEnabled(false)
    setMicEnabled(false)
    setState("idle")
    setStatus("Đã tắt camera và mic. SCP không còn dùng thiết bị.")
  }, [stopSpeech])

  const startConversation = useCallback(async () => {
    if (streamRef.current) return
    if (!navigator.mediaDevices?.getUserMedia) {
      setState("error")
      setStatus("Desktop không hỗ trợ camera/mic. Hãy dùng bản Desktop mới nhất.")
      return
    }
    try {
      setState("starting")
      setStatus("Đang xin quyền camera và mic. Bạn cần bấm Allow/Cho phép nếu Windows hỏi…")
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true })
      streamRef.current = stream
      setConversationOn(true)
      setCameraEnabled(stream.getVideoTracks().some((track) => track.readyState === "live"))
      setMicEnabled(stream.getAudioTracks().some((track) => track.readyState === "live"))
      setState("ready")
      setStatus("Đã kết nối bạn với SCP trên cùng PC. Bấm ‘Bấm để nói’ rồi nói một câu.")
    } catch (error) {
      setState("error")
      setStatus(`Không mở được camera/mic: ${error instanceof Error ? error.message : "Windows đã từ chối quyền"}`)
    }
  }, [])

  useEffect(() => {
    if (conversationOn && videoRef.current && streamRef.current) videoRef.current.srcObject = streamRef.current
  }, [conversationOn])

  const toggleCamera = useCallback(() => {
    const track = streamRef.current?.getVideoTracks()[0]
    if (!track) {
      void startConversation()
      return
    }
    track.enabled = !track.enabled
    setCameraEnabled(track.enabled)
    setStatus(track.enabled ? "Camera đã bật." : "Camera đã tắt; SCP vẫn giữ cuộc nói chuyện bằng mic.")
  }, [startConversation])

  const toggleMic = useCallback(() => {
    const track = streamRef.current?.getAudioTracks()[0]
    if (!track) {
      void startConversation()
      return
    }
    if (recorderRef.current) {
      recorderRef.current.stop()
      setStatus("Đã dừng ghi âm. SCP đang kiểm tra câu nói…")
      return
    }
    if (!track.enabled) {
      track.enabled = true
      setMicEnabled(true)
    }
    const audioStream = new MediaStream([track])
    const supportedType = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg"].find((type) => MediaRecorder.isTypeSupported(type))
    const recorder = supportedType ? new MediaRecorder(audioStream, { mimeType: supportedType }) : new MediaRecorder(audioStream)
    recorderRef.current = recorder
    chunksRef.current = []
    recorder.ondataavailable = (event) => { if (event.data.size > 0) chunksRef.current.push(event.data) }
    recorder.onstop = () => {
      recorderRef.current = null
      const audio = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" })
      chunksRef.current = []
      void sendAudioToScp(audio)
    }
    recorder.onerror = () => {
      recorderRef.current = null
      chunksRef.current = []
      setState("error")
      setStatus("Mic ghi âm bị lỗi. Kiểm tra quyền microphone của Windows.")
    }
    recorder.start()
    setState("recording")
    setStatus("Đang nghe bạn nói. Nói xong bấm ‘Dừng ghi âm’.")
  }, [startConversation])

  const sendQuestionToScp = useCallback(async (question: string) => {
    const cleanQuestion = question.trim()
    if (!cleanQuestion) {
      setState("error")
      setStatus("SCP chưa nhận được câu chữ. Hãy nói lại một câu rõ hơn.")
      return
    }
    setTranscript(cleanQuestion)
    setState("processing")
    setStatus("SCP đang kiểm tra câu hỏi, đối chiếu và tạo câu trả lời…")
    try {
      const response = await fetch("/api/scp/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: cleanQuestion, domain: "general", session_id: ensureSessionId() }),
        cache: "no-store",
      })
      const data = await response.json().catch(() => ({ error: "Không đọc được câu trả lời" })) as JsonRecord
      const text = asText(data.final_answer ?? data.answer ?? data.error, "SCP chưa có câu trả lời rõ ràng.")
      setAnswer(text)
      setVerdict(asText(data.verdict, response.ok ? "Đã nhận" : `HTTP ${response.status}`))
      if (!response.ok) {
        setState("error")
        setStatus(`SCP trả lỗi HTTP ${response.status}. Câu hỏi vẫn được giữ trên màn hình.`)
        return
      }
      setState("ready")
      setStatus("SCP đã trả lời bằng chữ.")
      speakAnswer(text)
    } catch (error) {
      setState("error")
      setStatus(`Không kết nối được SCP: ${error instanceof Error ? error.message : "lỗi không rõ"}`)
    }
  }, [ensureSessionId, speakAnswer])

  const sendAudioToScp = useCallback(async (audio: Blob) => {
    setState("processing")
    setStatus("Đang chuyển giọng nói thành chữ bằng Whisper local của SCP…")
    try {
      const dataUrl = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader()
        reader.onloadend = () => resolve(String(reader.result || ""))
        reader.onerror = () => reject(new Error("Không đọc được audio"))
        reader.readAsDataURL(audio)
      })
      const audioBase64 = dataUrl.split(",", 2)[1] || ""
      const response = await fetch("/api/scp/voice", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ audio_base64: audioBase64 }),
        cache: "no-store",
      })
      const data = await response.json().catch(() => ({ error: "Không đọc được kết quả voice" })) as JsonRecord
      if (data.jailbreak_detected === true) {
        const blocked = asText(data.error, "SCP đã chặn câu nói vì phát hiện nội dung nguy hiểm.")
        setAnswer(blocked)
        setVerdict("FAIL · VOICE_BLOCK")
        setState("ready")
        setStatus("SCP đã chặn câu nói nguy hiểm và ghi nhận sự kiện.")
        speakAnswer(blocked)
        return
      }
      const text = asText(data.text_extracted ?? data.transcript ?? data.text, "")
      if (!text) {
        setState("error")
        setStatus(asText(data.error, `SCP chưa chuyển được giọng nói thành chữ · HTTP ${response.status}`))
        return
      }
      await sendQuestionToScp(text)
    } catch (error) {
      setState("error")
      setStatus(`Voice lỗi: ${error instanceof Error ? error.message : "không rõ"}`)
    }
  }, [sendQuestionToScp, speakAnswer])

  useEffect(() => {
    setSpeechSupported(typeof window !== "undefined" && "speechSynthesis" in window)
    void getSpeechRecognitionSupport()
    return () => stopConversation()
  }, [stopConversation])

  const recording = state === "recording"
  const busy = state === "starting" || state === "processing" || state === "speaking"

  return (
    <section className="mt-5 rounded-3xl border border-emerald-300/20 bg-emerald-300/[0.045] p-5 sm:p-7" aria-label="Nói chuyện trực tiếp với SCP">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div>
          <div className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-200">00 · Nói chuyện trực tiếp</div>
          <h2 className="mt-2 text-xl font-semibold text-white">Bạn nói với SCP bằng camera và mic trên chính PC</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">Đây không phải phòng gọi giữa hai PC. Bạn bấm bắt đầu, SCP xin quyền camera/mic, nghe từng câu bằng Whisper local, gửi câu qua luồng kiểm tra hiện tại và đọc câu trả lời qua loa PC.</p>
        </div>
        <div className="flex gap-2">
          {!conversationOn ? <button type="button" onClick={() => void startConversation()} disabled={busy} className="rounded-xl bg-emerald-300 px-4 py-2.5 text-sm font-semibold text-slate-950 disabled:opacity-50">Bắt đầu nói chuyện</button> : <button type="button" onClick={stopConversation} className="rounded-xl border border-rose-300/30 px-4 py-2.5 text-sm text-rose-100">Tắt camera/mic</button>}
        </div>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,1.2fr)_minmax(280px,0.8fr)]">
        <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-black/30">
          {conversationOn ? <video ref={videoRef} autoPlay muted playsInline className="aspect-video w-full object-cover" /> : <div className="grid aspect-video place-items-center text-center text-sm text-slate-500">Camera đang tắt.<br />Bấm “Bắt đầu nói chuyện” để Windows hỏi quyền.</div>}
          <div className="absolute bottom-3 left-3 rounded-full bg-black/65 px-3 py-1.5 text-xs text-white">Bạn · camera {cameraEnabled ? "đang bật" : "đang tắt"}</div>
        </div>
        <div className="flex flex-col justify-between rounded-2xl border border-white/10 bg-black/20 p-4">
          <div className="flex items-center gap-3"><div className="grid h-14 w-14 place-items-center rounded-full bg-emerald-300 text-lg font-bold text-slate-950" aria-label="Ảnh đại diện SCP">SCP</div><div><div className="font-semibold text-white">SCP DNA</div><div className="text-xs text-slate-500">Trợ lý đang ở trên PC của bạn</div></div></div>
          <div className="mt-4 text-sm leading-6 text-slate-300">{status}</div>
          <div className="mt-4 flex flex-wrap gap-2"><button type="button" onClick={toggleMic} disabled={!conversationOn || busy} className={`rounded-xl border px-3 py-2 text-sm ${recording ? "border-rose-300/50 bg-rose-300/10 text-rose-100" : "border-white/10 text-slate-200"}`}>{recording ? "Dừng ghi âm" : "Bấm để nói"}</button><button type="button" onClick={toggleCamera} disabled={!conversationOn || busy} className="rounded-xl border border-white/10 px-3 py-2 text-sm text-slate-200">{cameraEnabled ? "Tắt camera" : "Bật camera"}</button><button type="button" onClick={() => { setSpeechOutput((value) => !value); if (speechOutput) stopSpeech() }} disabled={!speechSupported} className="rounded-xl border border-white/10 px-3 py-2 text-sm text-slate-200">Loa: {speechOutput ? "Bật" : "Tắt"}</button></div>
          <div className="mt-3 text-xs text-slate-500">Mic: {micEnabled ? "đang sẵn sàng" : "đang tắt"} · Loa đọc câu trả lời: {speechSupported ? "có" : "không có"} · Nhận dạng trình duyệt: {getSpeechRecognitionSupport() ? "có" : "không dùng; SCP dùng Whisper local"}</div>
        </div>
      </div>

      {(transcript || answer) && <div className="mt-4 grid gap-3 md:grid-cols-2"><div className="rounded-2xl border border-white/10 bg-black/20 p-4"><div className="text-xs uppercase tracking-[0.16em] text-slate-500">Bạn vừa nói</div><div className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-200">{transcript || "—"}</div></div><div className="rounded-2xl border border-emerald-300/20 bg-emerald-300/[0.06] p-4"><div className="text-xs uppercase tracking-[0.16em] text-emerald-200">SCP · {verdict || "đang xử lý"}</div><div className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-100">{answer || "SCP đang chuẩn bị câu trả lời…"}</div></div></div>}
      <div className="mt-3 text-xs text-slate-500">Quyền chỉ được xin sau khi bạn bấm nút. Khi bấm “Tắt camera/mic”, các track đều bị dừng; SCP không tự mở lại.</div>
    </section>
  )
}

import { api } from "@/lib/api"

interface Callbacks {
  partial: (text: string) => void
  turn: (text: string) => void
  ready: () => void
  ended: () => void
  error: (message: string) => void
}

/** Browser-owned capture and transcription; no server audio device is involved. */
export class BrowserVoice {
  private stream?: MediaStream
  private context?: AudioContext
  private capture?: AudioWorkletNode
  private source?: MediaStreamAudioSourceNode
  private socket?: WebSocket
  private timer?: number
  private deadline?: number
  private destroyed = false
  private stopping = false
  private speaking = false
  private lastActivity = 0
  private pending = new Set<string>()
  private finals = new Set<string>()
  private segments: { start: number; text: string }[] = []
  private flushed?: () => void
  private callbacks: Callbacks

  constructor(callbacks: Callbacks) {
    this.callbacks = callbacks
  }

  private check() {
    if (this.destroyed) throw new Error("Microphone capture cancelled.")
  }

  async start() {
    if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
      throw new Error("Open Jesse over HTTPS to use your microphone.")
    }
    // Resume from the click gesture, before permission/network requests can consume it.
    this.context = new AudioContext({ sampleRate: 16000 })
    await this.context.resume()
    this.check()
    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true },
    })
    if (this.destroyed) {
      this.stream.getTracks().forEach((track) => track.stop())
      this.check()
    }
    this.stream.getAudioTracks().forEach((track) => {
      track.onended = () => this.fail("Microphone disconnected. Reconnect it and try again.")
    })
    await this.context.audioWorklet.addModule(`${import.meta.env.BASE_URL}voice-capture.js`)
    this.check()
    if (this.context.sampleRate !== 16000) throw new Error("This browser cannot capture audio at 16 kHz.")
    const { url } = await api.voiceSession()
    this.check()
    const socket = new WebSocket(url)
    this.socket = socket
    socket.onmessage = (event) => this.message(event)
    socket.onclose = (event) => {
      if (this.destroyed) return
      if (event.code !== 1000 || (!this.stopping && this.pending.size)) {
        this.fail("Voice connection interrupted. Please try again.")
        return
      }
      this.flush(true)
      if (this.pending.size) this.callbacks.error("Some speech was not finalized. Please repeat it.")
      this.destroy()
      this.callbacks.ended()
    }
    await new Promise<void>((resolve, reject) => {
      const timeout = window.setTimeout(() => reject(new Error("Gladia did not connect. Try again.")), 20000)
      const finish = (error?: Error) => {
        window.clearTimeout(timeout)
        socket.removeEventListener("close", closed)
        if (error) reject(error)
        else resolve()
      }
      const closed = () => finish(new Error("Voice connection closed before recording started."))
      socket.addEventListener("close", closed, { once: true })
      socket.onopen = () => finish()
      socket.onerror = () => finish(new Error("Could not connect to Gladia. Check your connection and try again."))
    })
    this.check()
    socket.onerror = () => this.fail("Voice connection failed. Check your connection and try again.")
    this.capture = new AudioWorkletNode(this.context, "voice-capture")
    this.capture.port.onmessage = (event: MessageEvent<ArrayBuffer | string>) => {
      if (event.data === "flushed") {
        this.flushed?.()
      } else if (event.data instanceof ArrayBuffer && socket.readyState === WebSocket.OPEN) {
        if (socket.bufferedAmount > 1024 * 1024) {
          this.fail("The connection is too slow for voice input. Please try again.")
          return
        }
        socket.send(event.data)
      }
    }
    this.capture.onprocessorerror = () => this.fail("Audio capture stopped. Try the microphone again.")
    this.source = this.context.createMediaStreamSource(this.stream)
    // The processor outputs silence; connect it so browsers keep processing without microphone feedback.
    this.source.connect(this.capture)
    this.capture.connect(this.context.destination)
    this.timer = window.setInterval(() => this.flush(), 100)
    this.callbacks.ready()
  }

  private message(event: MessageEvent) {
    if (this.destroyed) return
    try {
      const message = JSON.parse(event.data)
      const now = Date.now()
      if (message.type === "error") {
        this.fail("Gladia could not transcribe your microphone. Please try again.")
      } else if (message.type === "speech_start") {
        this.speaking = true
        this.lastActivity = now
      } else if (message.type === "speech_end") {
        this.speaking = false
        this.lastActivity = now
      } else if (message.type === "transcript") {
        const { id, is_final, utterance } = message.data
        if (this.finals.has(id)) return
        const text = utterance.text.trim()
        this.lastActivity = now
        if (is_final) {
          this.finals.add(id)
          this.pending.delete(id)
          if (text) this.segments.push({ start: utterance.start, text })
        } else {
          this.pending.add(id)
        }
        this.callbacks.partial([...this.segments.map((segment) => segment.text), ...(!is_final ? [text] : [])].join(" "))
      }
    } catch {
      this.fail("Received an unreadable voice transcript. Please try again.")
    }
  }

  private flush(finishing = false) {
    if (this.destroyed || this.pending.size || !this.segments.length) return
    if (!finishing && (this.stopping || this.speaking || Date.now() - this.lastActivity < 1500)) return
    const text = this.segments.sort((a, b) => a.start - b.start).map((segment) => segment.text).join(" ")
    this.segments = []
    this.callbacks.partial("")
    this.callbacks.turn(text)
  }

  async stop() {
    if (this.stopping || this.destroyed) return
    this.stopping = true
    if (!this.capture || this.socket?.readyState !== WebSocket.OPEN) {
      this.destroy()
      this.callbacks.ended()
      return
    }
    // Flush the worklet's last partial chunk before asking Gladia for final transcripts.
    await new Promise<void>((resolve) => {
      const timeout = window.setTimeout(resolve, 250)
      this.flushed = () => { window.clearTimeout(timeout); resolve() }
      this.capture!.port.postMessage("flush")
    })
    this.releaseMicrophone()
    if (this.destroyed) return
    this.socket?.send(JSON.stringify({ type: "stop_recording" }))
    this.deadline = window.setTimeout(() => this.fail("Gladia did not finish the last transcript. Please repeat it."), 30000)
  }

  private releaseMicrophone() {
    this.source?.disconnect()
    this.capture?.disconnect()
    this.stream?.getTracks().forEach((track) => { track.onended = null; track.stop() })
    if (this.context && this.context.state !== "closed") void this.context.close().catch(() => undefined)
    this.source = undefined
    this.capture = undefined
    this.stream = undefined
    this.context = undefined
  }

  private fail(message: string) {
    if (this.destroyed) return
    this.destroy()
    this.callbacks.error(message)
    this.callbacks.ended()
  }

  destroy() {
    this.destroyed = true
    window.clearInterval(this.timer)
    window.clearTimeout(this.deadline)
    this.releaseMicrophone()
    this.socket?.close()
  }
}

export function microphoneError(error: unknown): string {
  if (error instanceof DOMException) {
    if (error.name === "NotAllowedError") return "Microphone access was denied. Allow the microphone for Jesse in your browser’s site settings."
    if (error.name === "NotFoundError") return "No microphone was found. Connect a microphone and try again."
    if (error.name === "NotReadableError") return "Your microphone is unavailable. Check whether another app is using it."
  }
  return error instanceof Error ? error.message : "Could not start your microphone."
}

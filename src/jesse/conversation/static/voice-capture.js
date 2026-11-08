// AudioContext resamples the microphone to 16 kHz. Send mono, little-endian PCM16.
class VoiceCapture extends AudioWorkletProcessor {
  constructor() {
    super()
    this.buffer = new ArrayBuffer(3200 * 2)
    this.view = new DataView(this.buffer)
    this.offset = 0
    this.port.onmessage = () => {
      this.flush()
      this.port.postMessage("flushed")
    }
  }

  flush() {
    if (!this.offset) return
    const chunk = this.buffer.slice(0, this.offset * 2)
    this.port.postMessage(chunk, [chunk])
    this.offset = 0
  }

  process(inputs) {
    for (const sample of inputs[0]?.[0] ?? []) {
      const value = Math.max(-1, Math.min(1, sample))
      this.view.setInt16(this.offset * 2, value * (value < 0 ? 32768 : 32767), true)
      this.offset += 1
      if (this.offset === 3200) this.flush()
    }
    return true
  }
}

registerProcessor("voice-capture", VoiceCapture)

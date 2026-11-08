import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import vm from 'node:vm'
import ts from 'typescript'

// Exercise the production capture controller with browser devices and Gladia replaced at their boundaries.
const source = readFileSync(new URL('../src/lib/browser-voice.ts', import.meta.url), 'utf8')
  .replace('import { api } from "@/lib/api"', 'const api = globalThis.__voiceApi')
  .replace('import.meta.env.BASE_URL', '"/static/"')
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText

function harness({ permissionError, deferredPermission } = {}) {
  let now = 10000
  let tick
  const calls = { turns: [], errors: [], partials: [], ended: 0, ready: 0, devices: 0, sockets: [] }
  const track = { stopped: false, stop() { this.stopped = true } }
  const stream = { getTracks: () => [track], getAudioTracks: () => [track] }
  const contexts = []
  let capture
  class AudioContext {
    constructor(options) { this.sampleRate = options.sampleRate; this.state = 'running'; contexts.push(this) }
    resume() { return Promise.resolve() }
    close() { this.state = 'closed'; return Promise.resolve() }
    audioWorklet = { addModule: async (url) => { assert.equal(url, '/static/voice-capture.js') } }
    createMediaStreamSource() { return { connect() {}, disconnect() {} } }
    destination = {}
  }
  class AudioWorkletNode {
    constructor() { capture = this }
    connect() {}
    disconnect() {}
    port = { postMessage: () => queueMicrotask(() => this.port.onmessage?.({ data: 'flushed' })) }
  }
  class WebSocket {
    static OPEN = 1
    readyState = 0
    bufferedAmount = 0
    sent = []
    listeners = new Map()
    constructor() { calls.sockets.push(this); queueMicrotask(() => { this.readyState = 1; this.onopen?.() }) }
    addEventListener(type, listener) { this.listeners.set(type, listener) }
    removeEventListener(type) { this.listeners.delete(type) }
    send(data) { this.sent.push(data) }
    close() { this.readyState = 3 }
    emit(type, data = {}) { this.onmessage({ data: JSON.stringify({ type, data }) }) }
    finish(code = 1000) { this.readyState = 3; this.onclose({ code }) }
  }
  const exports = {}
  const context = {
    exports, ArrayBuffer, DOMException, AudioContext, AudioWorkletNode, WebSocket,
    Date: class extends Date { static now() { return now } },
    window: { isSecureContext: true, setTimeout, clearTimeout, setInterval: (callback) => { tick = callback; return 1 }, clearInterval() {} },
    navigator: { mediaDevices: { getUserMedia: async () => {
      calls.devices++
      if (permissionError) throw permissionError
      if (deferredPermission) await deferredPermission
      return stream
    } } },
    __voiceApi: { voiceSession: async () => ({ url: 'wss://transcription.test' }) },
  }
  vm.runInNewContext(compiled, context)
  const session = new exports.BrowserVoice({
    partial: (text) => calls.partials.push(text), turn: (text) => calls.turns.push(text),
    ready: () => calls.ready++, ended: () => calls.ended++, error: (text) => calls.errors.push(text),
  })
  return { session, calls, track, contexts, exports,
    socket: () => calls.sockets.at(-1), capture: () => capture,
    advance: (ms) => { now += ms; tick?.() },
  }
}

const transcript = (socket, id, text, final = true, start = 0) => socket.emit('transcript', { id, is_final: final, utterance: { text, start } })

test('captures the browser microphone and sends PCM bytes to the session socket', async () => {
  const h = harness()
  await h.session.start()
  assert.equal(h.calls.devices, 1)
  assert.equal(h.calls.ready, 1)
  const pcm = new ArrayBuffer(6400)
  h.capture().port.onmessage({ data: pcm })
  assert.equal(h.socket().sent[0], pcm)
  h.session.destroy()
  assert.equal(h.track.stopped, true)
  assert.equal(h.contexts[0].state, 'closed')
})

test('groups finalized segments in audio order; partials and duplicate finals never submit twice', async () => {
  const h = harness()
  await h.session.start()
  const socket = h.socket()
  socket.emit('speech_start')
  transcript(socket, 'b', 'and repeat.', true, 2)
  transcript(socket, 'a', 'Measure gravity', false, 0)
  socket.emit('speech_end')
  h.advance(2000)
  assert.deepEqual(h.calls.turns, [])
  transcript(socket, 'a', 'Measure gravity', true, 0)
  h.advance(1600)
  assert.deepEqual(h.calls.turns, ['Measure gravity and repeat.'])
  transcript(socket, 'a', 'Measure gravity', true, 0)
  h.advance(2000)
  assert.equal(h.calls.turns.length, 1)
  h.session.destroy()
})

test('stop releases the microphone and preserves trailing final transcripts', async () => {
  const h = harness()
  await h.session.start()
  transcript(h.socket(), 'last', 'Repeat', false)
  await h.session.stop()
  assert.equal(h.track.stopped, true)
  assert.equal(JSON.parse(h.socket().sent.at(-1)).type, 'stop_recording')
  transcript(h.socket(), 'last', 'Repeat the measurement.', true)
  assert.deepEqual(h.calls.turns, [])
  h.socket().finish()
  assert.deepEqual(h.calls.turns, ['Repeat the measurement.'])
  assert.equal(h.calls.ended, 1)
})

test('disconnect frees devices and reports incomplete audio instead of submitting partial words', async () => {
  const h = harness()
  await h.session.start()
  transcript(h.socket(), 'partial', 'Repeat', false)
  h.socket().finish(1006)
  assert.equal(h.track.stopped, true)
  assert.equal(h.calls.ended, 1)
  assert.equal(h.calls.errors.length, 1)
  assert.deepEqual(h.calls.turns, [])
})

test('permission denial is actionable and no provider connection is opened', async () => {
  const denied = new DOMException('denied', 'NotAllowedError')
  const h = harness({ permissionError: denied })
  await assert.rejects(h.session.start(), { name: 'NotAllowedError' })
  h.session.destroy()
  assert.equal(h.contexts[0].state, 'closed')
  assert.equal(h.calls.sockets.length, 0)
  assert.match(h.exports.microphoneError(denied), /site settings/)
})

test('unmount during a permission prompt stops the eventual stream and creates no session', async () => {
  let grant
  const permission = new Promise((resolve) => { grant = resolve })
  const h = harness({ deferredPermission: permission })
  const starting = h.session.start()
  await new Promise((resolve) => setImmediate(resolve))
  assert.equal(h.calls.devices, 1)
  h.session.destroy()
  grant()
  await assert.rejects(starting, /cancelled/)
  assert.equal(h.track.stopped, true)
  assert.equal(h.calls.sockets.length, 0)
})

test('worklet encodes bounded little-endian PCM16 and flushes the last short chunk', () => {
  let Processor
  const sent = []
  const context = { ArrayBuffer, DataView,
    AudioWorkletProcessor: class { port = { postMessage: (data) => sent.push(data) } },
    registerProcessor: (name, processor) => { assert.equal(name, 'voice-capture'); Processor = processor },
  }
  vm.runInNewContext(readFileSync(new URL('../public/voice-capture.js', import.meta.url), 'utf8'), context)
  const processor = new Processor()
  processor.process([[[-2, -1, 0, 1, 2]]])
  processor.port.onmessage()
  const pcm = new DataView(sent[0])
  assert.deepEqual([0, 1, 2, 3, 4].map((index) => pcm.getInt16(index * 2, true)), [-32768, -32768, 0, 32767, 32767])
  assert.equal(sent[1], 'flushed')
})

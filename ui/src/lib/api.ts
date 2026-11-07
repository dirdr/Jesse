// Typed client for the local Jesse controller (src/jesse/conversation/web.py).

export type Author = "researcher" | "jesse" | "controller"

export interface ConversationEvent {
  id: string
  kind: string
  text: string
  author: Author
  speak: boolean
  at: string
  source?: "text" | "voice"
  message_id?: string
}

export type RunStatus =
  | "planning"
  | "running"
  | "waiting"
  | "supported_conclusion"
  | "inconclusive"
  | "blocked"

export interface Selection {
  status: "ready" | "blocked"
  question: string
  reason: string
  experiment_id: string | null
  surface: "web" | "desktop" | null
  maximum_trials: number | null
}

export interface Snapshot {
  run_id: string
  active: boolean
  status: RunStatus
  can_message: boolean
  agent_view_url: string | null
  events: ConversationEvent[]
  outcome: { outcome: string; reason?: string } | null
  report_available: boolean
  report_url: string | null
  selection: Selection | null
}

export interface Frame {
  index: number
  at: string
  viewport: [number, number] | null
  cursor: [number, number] | null
}

export interface Action {
  index: number
  at: string
  tool: string
  frame: number | null
  text: string
  args: Record<string, unknown>
}

export interface PlanGoal {
  title: string
  status: string
}

export interface Measurement {
  id: string
  at: string | null
  fields: Record<string, string>
  result: string | null
  status: string
}

export interface LiveState {
  frames: Frame[]
  actions: Action[]
  plan: PlanGoal[]
  measurements: Measurement[]
  steps: number | null
  cost_usd: number | null
  errors: number
}

export interface VoiceTurn {
  id: string
  text: string
  action: "started" | "steered" | "failed"
  run_id: string | null
  detail: string | null
}

export interface VoiceState {
  available: boolean
  reason: string | null
  listening: boolean
  partial: string
  error: string | null
  turns: VoiceTurn[]
}

const token =
  document.querySelector<HTMLMetaElement>('meta[name="jesse-token"]')?.content ?? ""

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { "content-type": "application/json", "x-jesse-token": token, ...init.headers },
  })
  if (!response.ok) {
    let detail = response.statusText || "Request failed"
    try {
      const body = await response.json()
      if (typeof body.detail === "string") detail = body.detail
    } catch {
      /* non-JSON error */
    }
    throw new Error(detail)
  }
  const type = response.headers.get("content-type") ?? ""
  return (type.includes("application/json") ? response.json() : response.text()) as Promise<T>
}

export const api = {
  current: () => request<{ run_id: string | null }>("/api/current"),
  snapshot: (id: string) => request<Snapshot>(`/api/runs/${id}`),
  start: (text: string) =>
    request<{ run_id: string }>("/api/runs", { method: "POST", body: JSON.stringify({ text }) }),
  message: (id: string, text: string, source: "text" | "voice") =>
    request(`/api/runs/${id}/messages`, {
      method: "POST",
      body: JSON.stringify({ text, source, event_id: crypto.randomUUID() }),
    }),
  stop: (id: string) => request(`/api/runs/${id}/stop`, { method: "POST" }),
  report: (url: string) => request<string>(url),
  live: (id: string) => request<LiveState>(`/api/runs/${id}/live`),
  frameUrl: (id: string, index: number) => `/api/runs/${id}/frames/${index}`,
  voice: () => request<VoiceState>("/api/voice"),
  voiceStart: () => request<VoiceState>("/api/voice/start", { method: "POST" }),
  voiceStop: () => request<VoiceState>("/api/voice/stop", { method: "POST" }),
}

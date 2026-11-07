import { useEffect, useState } from "react"
import { toast } from "sonner"
import { api, type PersonaId, type PersonaState } from "@/lib/api"

export function usePersonas() {
  const [state, setState] = useState<PersonaState>({ selected: "pinkman", personas: [] })
  const [pending, setPending] = useState(false)

  useEffect(() => {
    let cancelled = false
    api.personas().then((next) => { if (!cancelled) setState(next) }).catch(() => {
      if (!cancelled) toast.error("Could not load personas. Refresh to try again.")
    })
    return () => { cancelled = true }
  }, [])

  const select = async (id: PersonaId) => {
    const previous = state
    setState({ ...state, selected: id })
    setPending(true)
    try {
      setState(await api.selectPersona(id))
    } catch (error) {
      setState(previous)
      toast.error(error instanceof Error ? error.message : "Could not select persona")
    } finally {
      setPending(false)
    }
  }

  return { ...state, pending, select }
}

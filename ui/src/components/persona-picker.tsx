import type { PersonaId, PersonaState } from "@/lib/api"

export function PersonaPicker({ state, value, disabled, onSelect }: {
  state: PersonaState
  value: PersonaId
  disabled: boolean
  onSelect: (id: PersonaId) => void
}) {
  return (
    <label className="flex items-center gap-2 text-sm">
      <span className="hidden text-muted-foreground sm:inline">Persona</span>
      <select
        aria-label="Persona"
        value={value}
        disabled={disabled || !state.personas.length}
        onChange={(event) => onSelect(event.target.value as PersonaId)}
        className="h-9 max-w-40 rounded-md border border-input bg-background px-2 text-sm font-medium outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-default disabled:opacity-60"
        title={disabled ? "Choose a persona before starting a new investigation" : "Personality and matching voice"}
      >
        {!state.personas.length && <option value="pinkman">Jesse Pinkman</option>}
        {state.personas.map((persona) => <option key={persona.id} value={persona.id}>{persona.name}{!persona.available ? " (text only)" : ""}</option>)}
      </select>
    </label>
  )
}

import { AnimatePresence, motion } from "motion/react"
import { Mic, MicOff } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import type { VoiceState } from "@/lib/api"
import { cn } from "@/lib/utils"

export function VoiceButton({ state, onToggle, className }: { state: VoiceState | null; onToggle: () => void; className?: string }) {
  const listening = Boolean(state?.listening)
  const label = !state?.available ? state?.reason ?? "Microphone unavailable" : listening ? "Stop listening" : "Speak to Jesse"
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className={cn("inline-flex", className)}>
          <Button
            type="button"
            variant={listening ? "destructive" : "outline"}
            size="icon"
            onClick={onToggle}
            disabled={!state?.available}
            aria-pressed={listening}
            aria-label={label}
            className="relative rounded-full"
          >
            {listening && <span className="absolute inset-0 animate-ping rounded-full bg-destructive/40" />}
            {state && !state.available ? <MicOff /> : <Mic />}
          </Button>
        </span>
      </TooltipTrigger>
      <TooltipContent>{label}</TooltipContent>
    </Tooltip>
  )
}

/** Live transcript while the microphone is open. */
export function TranscriptPill({ state }: { state: VoiceState | null }) {
  return (
    <AnimatePresence>
      {state?.listening && (
        <motion.div
          initial={{ y: 16, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 16, opacity: 0 }}
          className="pointer-events-none fixed inset-x-0 bottom-6 z-40 flex justify-center px-4"
        >
          <div className="flex max-w-2xl items-center gap-3 rounded-full border border-border/70 bg-background/90 px-5 py-3 shadow-2xl backdrop-blur-xl">
            <span className="relative flex size-2.5 shrink-0">
              <span className="absolute inset-0 animate-ping rounded-full bg-destructive/60" />
              <span className="relative size-2.5 rounded-full bg-destructive" />
            </span>
            <span className={cn("truncate text-base", !state.partial && "text-muted-foreground")}>
              {state.partial || "Listening…"}
            </span>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

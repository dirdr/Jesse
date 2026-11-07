import { cn } from "@/lib/utils"
import { STATUS, TONE_CLASS } from "@/lib/kinds"
import type { RunStatus } from "@/lib/api"

export function StatusBadge({ status }: { status: RunStatus | "idle" }) {
  const config = STATUS[status] ?? STATUS.idle
  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset",
        TONE_CLASS[config.tone],
      )}
    >
      <span className="relative flex size-2">
        {config.live && (
          <span className="absolute inline-flex size-full animate-ping rounded-full bg-current opacity-60" />
        )}
        <span className="relative inline-flex size-2 rounded-full bg-current" />
      </span>
      {config.label}
    </span>
  )
}

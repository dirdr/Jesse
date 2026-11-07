import { cn } from "@/lib/utils"

const MARK = `${import.meta.env.BASE_URL}jesse-mark.png`

/** The README logo: the "Je" element tile followed by "sse", drawn in the theme's text colour. */
export function Logo({ size = "sm", className }: { size?: "sm" | "lg"; className?: string }) {
  const large = size === "lg"
  return (
    <span className={cn("inline-flex items-center", large ? "gap-1" : "gap-0.5", className)} aria-label="Jesse">
      <img src={MARK} alt="" className={cn("shrink-0 rounded-[3px]", large ? "h-20 w-auto sm:h-24" : "h-8 w-auto")} />
      <span
        aria-hidden="true"
        className={cn("leading-none font-black tracking-[-0.04em]", large ? "text-[5.6rem] sm:text-[6.8rem]" : "text-[2.1rem]")}
        style={{ fontWeight: 900 }}
      >
        sse
      </span>
    </span>
  )
}

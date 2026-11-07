import { useEffect, useState } from "react"
import { cn } from "@/lib/utils"

const PHOTO = `${import.meta.env.BASE_URL}jesse-pinkman.png`
const JAW = "polygon(30% 50%, 64% 50%, 63% 58%, 56% 64.5%, 47% 66.5%, 38% 64%, 31% 57%)"
const SHAPES = [0, 0.35, 0.7, 1, 0.5, 0.15]
const GREETINGS = ["Yo! Ask me a question, let's do some science.", "Yeah, science! What are we testing?", "Lab's ready. Just say the word."]

export function TalkingJesse({ speaking: said }: { speaking: string | null }) {
  const [greeting, setGreeting] = useState<string | null>(null)
  useEffect(() => {
    if (!greeting) return
    const timer = window.setTimeout(() => setGreeting(null), 2600)
    return () => window.clearTimeout(timer)
  }, [greeting])
  const speaking = said ?? greeting
  const [open, setOpen] = useState(0)
  const [tilt, setTilt] = useState(0)
  const talking = Boolean(speaking)

  useEffect(() => {
    if (!talking) {
      setOpen(0)
      setTilt(0)
      return
    }
    let tick = 0
    const flap = window.setInterval(() => {
      tick += 1
      setOpen(SHAPES[Math.floor(Math.random() * SHAPES.length)])
      if (tick % 2 === 0) setTilt((value) => (value > 0 ? -7 : 7))
    }, 110)
    return () => window.clearInterval(flap)
  }, [talking])

  return (
    <div className="pointer-events-none fixed right-4 bottom-4 z-40 flex items-end gap-2 sm:right-6 sm:bottom-6">
      {speaking && (
        <div
          role="status"
          className="relative mb-10 max-w-[min(18rem,calc(100vw-9rem))] rounded-md border-2 border-foreground bg-card px-3 py-2 text-sm font-medium text-foreground shadow-lg"
        >
          <p className="line-clamp-4">{speaking}</p>
          <span
            aria-hidden
            className="absolute -right-2 bottom-3 size-3 rotate-45 border-t-2 border-r-2 border-foreground bg-card"
          />
        </div>
      )}
      <button
        type="button"
        aria-label="Say hi to Jesse"
        onClick={() => setGreeting(GREETINGS[Math.floor(Math.random() * GREETINGS.length)])}
        className={cn(
          "pointer-events-auto cursor-pointer focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring",
          "relative aspect-[273/365] w-24 origin-bottom overflow-hidden rounded-[45%_45%_40%_40%] border-[3px] border-foreground bg-black shadow-[4px_4px_0_0_var(--brand)] sm:w-32",
          !speaking && "opacity-80",
        )}
        style={{ transform: `translateY(${talking ? -open * 14 : 0}px) rotate(${tilt}deg) scale(${1 + open * 0.07}, ${1 - open * 0.05})` }}
      >
        <img src={PHOTO} alt="" draggable={false} className="pointer-events-none absolute inset-0 size-full select-none" />
        <span
          className="absolute rounded-[50%] bg-[#2a0a0a]"
          style={{
            left: "37%",
            top: "49%",
            width: "20%",
            height: "9%",
            transformOrigin: "top",
            transform: `scaleY(${open})`,
            boxShadow: "inset 0 -2px 0 #b33",
          }}
        />
        <img
          src={PHOTO}
          alt=""
          draggable={false}
          className="pointer-events-none absolute inset-0 size-full select-none"
          style={{ clipPath: JAW, transform: `translateY(${open * 7}%)` }}
        />
      </button>
    </div>
  )
}

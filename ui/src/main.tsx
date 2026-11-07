import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import "@fontsource-variable/geist"
import "@fontsource-variable/geist-mono"
import "katex/dist/katex.min.css"
import "./index.css"
import App from "./App.tsx"

// Follow the operating system theme; shadcn's dark tokens hang off the .dark class.
const media = window.matchMedia("(prefers-color-scheme: dark)")
const applyTheme = () => document.documentElement.classList.toggle("dark", media.matches)
applyTheme()
media.addEventListener("change", applyTheme)

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

import { useState } from "react"
import { Theme } from "./constants/colors"
import { HomePage }       from "./pages/HomePage"
import { ExperimentPage } from "./pages/ExperimentPage"
import { ReplayPage }     from "./pages/ReplayPage"

export default function App() {
  const [page, setPage] = useState("home")
  const [ctx,  setCtx]  = useState({})

  const nav = (nextPage, nextCtx = {}) => {
    setCtx(nextCtx)
    setPage(nextPage)
  }

  return (
    <div style={{ minHeight: "100vh", background: Theme.bg, fontFamily: "'Inter', 'Segoe UI', sans-serif" }}>
      {page === "home"       && <HomePage       nav={nav} />}
      {page === "experiment" && <ExperimentPage nav={nav} ctx={ctx} />}
      {page === "replay"     && <ReplayPage     nav={nav} ctx={ctx} />}
    </div>
  )
}
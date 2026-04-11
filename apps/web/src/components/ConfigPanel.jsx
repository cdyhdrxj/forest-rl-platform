import { useEffect } from "react"
import { Theme, card, secLabel, selStyle } from "../constants/colors"
import { TASKS_BY_ENV, ALGOS_BY_ENV, SLIDER_CONFIG } from "../constants/config"

const Label = ({ children }) =>
  <div style={{ fontSize: 11, color: Theme.textSecond, marginBottom: 4 }}>{children}</div>

export function ConfigPanel({
  activeEnv, setActiveEnv,
  activeTask, setActiveTask,
  algo, setAlgo,
  params, setParams,
  tab, setTab,
  running,
}) {
  const set = (k, v) => setParams(p => ({ ...p, [k]: v }))

  const availableTabs = ["Алгоритм", "Карта", "Робот"].filter(t => {
    if (t === "Алгоритм") return true
    const s = SLIDER_CONFIG[activeEnv]?.[t] ?? []
    return s.some(sl =>
      (!sl.algoOnly || sl.algoOnly.includes(algo)) &&
      (!sl.taskOnly  || sl.taskOnly.includes(activeTask))
    )
  })

  // Сброс активной вкладки если она пропала
  useEffect(() => {
    if (!availableTabs.includes(tab)) setTab(availableTabs[0])
  }, [availableTabs.join(",")])

  // Сброс алгоритма при смене среды
  useEffect(() => {
    const available = ALGOS_BY_ENV[activeEnv] ?? ["PPO"]
    if (!available.includes(algo)) setAlgo(available[0])
  }, [activeEnv])

  const sliders = SLIDER_CONFIG[activeEnv]?.[tab] ?? []
  const algos   = ALGOS_BY_ENV[activeEnv] ?? ["PPO"]

  const Slider = ({ label, param, min, max, step }) => (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, marginBottom: 4 }}>
        <span style={{ color: Theme.textSecond }}>{label}</span>
        <span style={{ color: Theme.textPrimary, fontWeight: 600, fontFamily: Theme.mono, fontSize: 11 }}>
          {params[param]}
        </span>
      </div>
      <input type="range" min={min} max={max} step={step} value={params[param]}
        onChange={e => set(param, +e.target.value)} disabled={running}
        style={{ width: "100%", accentColor: Theme.accent, cursor: running ? "not-allowed" : "pointer" }} />
    </div>
  )

  return (
    <div style={{ width: 220, flexShrink: 0, display: "flex", flexDirection: "column", gap: 10 }}>

      {/* Среда и задача */}
      <div style={{ ...card, padding: 14 }}>
        <div style={secLabel}>Конфигурация</div>
        <Label>Среда</Label>
        <select value={activeEnv} disabled={running} style={{ ...selStyle, marginBottom: 10 }}
          onChange={e => {
            const env = e.target.value
            setActiveEnv(env)
            const tasks = TASKS_BY_ENV[env]
            if (!tasks.includes(activeTask)) setActiveTask(tasks[0])
          }}>
          {Object.keys(TASKS_BY_ENV).map(e => <option key={e}>{e}</option>)}
        </select>
        <Label>Задача</Label>
        <select value={activeTask} onChange={e => setActiveTask(e.target.value)}
          disabled={running} style={selStyle}>
          {TASKS_BY_ENV[activeEnv].map(t => <option key={t}>{t}</option>)}
        </select>
      </div>

      {/* Параметры */}
      <div style={{ ...card, overflow: "hidden" }}>
        <div style={{
          display: "grid",
          gridTemplateColumns: `repeat(${availableTabs.length}, 1fr)`,
          background: "#f8fafc",
          borderBottom: `1px solid ${Theme.border}`,
        }}>
          {availableTabs.map(t => (
            <button key={t} onClick={() => setTab(t)} style={{
              padding: "8px 2px", fontSize: 11,
              fontWeight: tab === t ? 600 : 400,
              color: tab === t ? Theme.accent : Theme.textMuted,
              background: tab === t ? Theme.surface : "transparent",
              border: "none",
              borderBottom: tab === t ? `2px solid ${Theme.accent}` : "2px solid transparent",
              cursor: "pointer",
            }}>{t}</button>
          ))}
        </div>

        <div style={{ padding: 14 }}>
          {tab === "Алгоритм" && (
            <>
              <Label>Алгоритм</Label>
              <select value={algo} onChange={e => setAlgo(e.target.value)}
                disabled={running} style={{ ...selStyle, marginBottom: 14 }}>
                {algos.map(a => <option key={a}>{a}</option>)}
              </select>
            </>
          )}
          {sliders.length === 0
            ? <div style={{ fontSize: 11, color: Theme.textMuted }}>Нет параметров</div>
            : sliders.map(s => {
                if (s.algoOnly && !s.algoOnly.includes(algo)) return null
                if (s.taskOnly && !s.taskOnly.includes(activeTask)) return null
                return <Slider key={s.param} label={s.label} param={s.param} min={s.min} max={s.max} step={s.step} />
              })
          }
        </div>
      </div>
    </div>
  )
}
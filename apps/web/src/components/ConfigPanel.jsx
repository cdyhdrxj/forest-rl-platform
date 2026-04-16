import { useEffect, useRef, useState } from "react"
import { Theme, card, secLabel, selStyle } from "../constants/colors"
import { TASKS_BY_ENV, ALGOS_BY_ENV, SLIDER_CONFIG, DEFAULT_PARAMS } from "../constants/config"

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

  const [fitTabs, setFitTabs] = useState(false)
  const [canScrollRight, setCanScrollRight] = useState(false)

  const tabsRef = useRef(null)
  const dragState = useRef({ isDown: false, startX: 0, scrollLeft: 0, moved: false })
  
  useEffect(() => {
    console.log("PARAMS UPDATED:", params)
  }, [params])

  useEffect(() => {
    console.trace("PARAMS SET")
  }, [params])
  const checkTabs = () => {
    const el = tabsRef.current
    if (!el) return
    setFitTabs(el.scrollWidth <= el.clientWidth)
    setCanScrollRight(el.scrollLeft < el.scrollWidth - el.clientWidth - 2)
  }

  const onMouseDown = (e) => {
    const el = tabsRef.current
    dragState.current = {
      isDown: true,
      startX: e.pageX - el.offsetLeft,
      scrollLeft: el.scrollLeft,
      moved: false,
    }
    el.style.cursor = "grabbing"
  }

  const onMouseUp = () => {
    dragState.current.isDown = false
    if (tabsRef.current) tabsRef.current.style.cursor = "grab"
  }

  const onMouseMove = (e) => {
    if (!dragState.current.isDown) return
    const x = e.pageX - tabsRef.current.offsetLeft
    const diff = x - dragState.current.startX
    if (Math.abs(diff) > 3) dragState.current.moved = true
    tabsRef.current.scrollLeft = dragState.current.scrollLeft - diff
  }

  const onTabClick = (t) => {
    if (!dragState.current.moved) setTab(t)
    dragState.current.moved = false
  }

  const shouldShowSlider = (slider) => {
    if (slider.algoOnly && !slider.algoOnly.includes(algo)) return false
    if (slider.taskOnly && !slider.taskOnly.includes(activeTask)) return false
    return true
  }

  const availableTabs = ["Алгоритм", "Карта", "Агент", "Наблюдение", "Нарушитель", "Робот"]
    .filter(t => {
      const sliders = SLIDER_CONFIG[activeEnv]?.[t] ?? []
      return sliders.some(sl => shouldShowSlider(sl))
    })

  useEffect(() => {
    checkTabs()
    window.addEventListener("resize", checkTabs)
    return () => window.removeEventListener("resize", checkTabs)
  }, [availableTabs])

  useEffect(() => {
    if (!availableTabs.includes(tab)) setTab(availableTabs[0])
  }, [availableTabs.join(","), tab, setTab])

  useEffect(() => {
    const available = ALGOS_BY_ENV[activeEnv] ?? ["PPO"]
    if (!available.includes(algo)) setAlgo(available[0])
  }, [activeEnv, algo, setAlgo])

  const sliders = SLIDER_CONFIG[activeEnv]?.[tab] ?? []
  const algos = ALGOS_BY_ENV[activeEnv] ?? ["PPO"]

  const Slider = ({ label, param, min, max, step, type }) => {
    if (type === "bool") {
      return (
        <div style={{ marginBottom: 12 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <input
              type="checkbox"
              checked={params[param] ?? false}
              onChange={e => set(param, e.target.checked)}
              disabled={running}
              style={{
                accentColor: Theme.accent,
                cursor: running ? "not-allowed" : "pointer",
              }}
            />
            <span style={{ fontSize: 11, color: Theme.textSecond }}>{label}</span>
          </div>
        </div>
      )
    }

    const value = params[param] ?? DEFAULT_PARAMS[param] ?? min

    return (
      <div style={{ marginBottom: 12 }}>
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, marginBottom: 4 }}>
          <span style={{ color: Theme.textSecond }}>{label}</span>
          <span style={{ color: Theme.textPrimary, fontWeight: 600, fontFamily: Theme.mono, fontSize: 11 }}>
            {value}
          </span>
        </div>
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={e => set(param, +e.target.value)}
          disabled={running}
          style={{
            width: "100%",
            accentColor: Theme.accent,
            cursor: running ? "not-allowed" : "pointer",
          }}
        />
      </div>
    )
  }

  return (
    <div style={{ width: 220, flexShrink: 0, display: "flex", flexDirection: "column", gap: 10 }}>

      {/* Конфигурация */}
      <div style={{ ...card, padding: 14 }}>
        <div style={secLabel}>Конфигурация</div>

        <Label>Среда</Label>
        <select
          value={activeEnv}
          disabled={running}
          style={{ ...selStyle, marginBottom: 10 }}
          onChange={e => {
            const env = e.target.value
            setActiveEnv(env)
            const tasks = TASKS_BY_ENV[env]
            if (!tasks.includes(activeTask)) setActiveTask(tasks[0])
          }}
        >
          {Object.keys(TASKS_BY_ENV).map(e => <option key={e}>{e}</option>)}
        </select>

        <Label>Задача</Label>
        <select
          value={activeTask}
          onChange={e => setActiveTask(e.target.value)}
          disabled={running}
          style={selStyle}
        >
          {TASKS_BY_ENV[activeEnv].map(t => <option key={t}>{t}</option>)}
        </select>
      </div>

      {/* Параметры */}
      <div style={{ ...card, overflow: "hidden" }}>
        <div style={{ position: "relative" }}>
          <div
            ref={tabsRef}
            onMouseDown={onMouseDown}
            onMouseUp={onMouseUp}
            onMouseLeave={onMouseUp}
            onMouseMove={onMouseMove}
            onScroll={checkTabs}
            style={{
              overflowX: "auto",
              scrollbarWidth: "none",
              cursor: "grab",
              userSelect: "none",
              background: "#f8fafc",
              borderBottom: `1px solid ${Theme.border}`,
            }}
          >
            <div style={{ display: "flex", width: "100%" }}>
              {availableTabs.map(t => (
                <button
                  key={t}
                  onClick={() => onTabClick(t)}
                  style={{
                    padding: "8px 10px",
                    fontSize: 11,
                    fontWeight: tab === t ? 600 : 400,
                    color: tab === t ? Theme.accent : Theme.textMuted,
                    background: tab === t ? Theme.surface : "transparent",
                    border: "none",
                    borderBottom: tab === t ? `2px solid ${Theme.accent}` : "2px solid transparent",
                    cursor: "pointer",
                    flex: fitTabs ? 1 : "0 0 auto",
                    textAlign: "center",
                    whiteSpace: "nowrap",
                  }}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          {canScrollRight && (
            <div style={{
              position: "absolute",
              right: 0,
              top: 0,
              bottom: 0,
              width: 24,
              background: "linear-gradient(270deg, #f8fafc, transparent)",
              pointerEvents: "none",
              zIndex: 1,
            }} />
          )}
        </div>
      
        <div style={{ padding: 14 }}>
          {tab === "Алгоритм" && (
            <>
              <Label>Алгоритм</Label>
              <select
                value={algo}
                onChange={e => setAlgo(e.target.value)}
                disabled={running}
                style={{ ...selStyle, marginBottom: 14 }}
              >
                {algos.map(a => <option key={a}>{a}</option>)}
              </select>
            </>
          )}

          {sliders.filter(s => shouldShowSlider(s)).length === 0
            ? <div style={{ fontSize: 11, color: Theme.textMuted }}>Нет параметров</div>
            : sliders.map(s => shouldShowSlider(s) && <Slider key={s.param} {...s} />)
          }
        </div>
      </div>
    </div>
  )
}
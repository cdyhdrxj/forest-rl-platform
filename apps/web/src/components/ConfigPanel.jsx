import { useEffect, useRef, useState } from "react"
import { Theme, card, secLabel, selStyle } from "../constants/colors"
import { 
  TASKS_BY_ENV, 
  ALGOS_BY_ROUTE, 
  SLIDER_CONFIG, 
  DEFAULT_PARAMS,
  ALGO_SUPPORTED_PARAMS,
  filterParamsForAlgo,
  isParamLockedForInference
} from "../constants/config"
import { ENV, TASK, CLASSIC_ALGOS } from "../constants/envs"

const Label = ({ children }) =>
  <div style={{ fontSize: 11, color: Theme.textSecond, marginBottom: 4 }}>{children}</div>

const Slider = ({ label, param, min, max, step, type, options, value, onChange, disabled }) => {
  if (type === "select") {
    return (
      <div style={{ marginBottom: 12 }}>
        <div style={{ fontSize: 11, color: Theme.textSecond, marginBottom: 4 }}>{label}</div>
        <select
          value={value || options?.[0] || ""}
          onChange={e => onChange(param, e.target.value)}
          disabled={disabled}
          style={selStyle}
        >
          {options?.map(opt => <option key={opt}>{opt}</option>)}
        </select>
      </div>
    )
  }

  // Чекбокс
  if (type === "bool") {
    return (
      <div style={{ marginBottom: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <input type="checkbox" checked={value}
            onChange={e => onChange(param, e.target.checked)} disabled={disabled}
            style={{ accentColor: Theme.accent, cursor: disabled ? "not-allowed" : "pointer" }} />
          <span style={{ fontSize: 11, color: Theme.textSecond }}>{label}</span>
        </div>
      </div>
    )
  }
  
  // Слайдер 
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, marginBottom: 4 }}>
        <span style={{ color: Theme.textSecond }}>{label}</span>
        <span style={{ color: Theme.textPrimary, fontWeight: 600, fontFamily: Theme.mono, fontSize: 11 }}>{value}</span>
      </div>
      <input type="range" min={min} max={max} step={step} value={value}
        onChange={e => onChange(param, +e.target.value)} disabled={disabled}
        style={{ width: "100%", accentColor: Theme.accent, cursor: disabled ? "not-allowed" : "pointer" }} />
    </div>
  )
}

export function normalizeAlgorithm(algo) {
  return (algo || "PPO").toUpperCase()
}

export function extractParamsFromRun(run, defaultParams = DEFAULT_PARAMS) {
  const config = run?.config_json || {}
  const trainingParams = config.training_params || {}
  const runtimeConfig = config.runtime_config || {}
  
  const algorithm = normalizeAlgorithm(
    trainingParams.algorithm || runtimeConfig.algorithm || config.algorithm
  )
  
  const mergedParams = { ...defaultParams, ...trainingParams, ...runtimeConfig }
  
  const routeKeyFromRun = run.route_key || config.route_key
  let env = ENV.CONTINUOUS
  let task = TASK.TRAIL
  
  if (routeKeyFromRun) {
    if (routeKeyFromRun.startsWith("continuous")) env = ENV.CONTINUOUS
    else if (routeKeyFromRun.startsWith("discrete")) env = ENV.DISCRETE
    else if (routeKeyFromRun.startsWith("threed")) env = ENV.SIM_3D
    
    if (routeKeyFromRun.endsWith("trail")) task = TASK.TRAIL
    else if (routeKeyFromRun.endsWith("patrol")) task = TASK.PATROL
    else if (routeKeyFromRun.endsWith("coverage")) task = TASK.COVERAGE
    else if (routeKeyFromRun.endsWith("reforestation")) task = TASK.REFORESTATION
  }
  
  return { algorithm, mergedParams, env, task, routeKey: routeKeyFromRun }
}

export function ConfigPanel({
  activeEnv, setActiveEnv,
  activeTask, setActiveTask,
  envLocked = false,
  paramsLocked = false,      
  isInference = false,
  readOnly = false,         
  algo, setAlgo,
  params, setParams,
  tab, setTab,
  running,
  jsonConfig, setJsonConfig,
}) {
 
  // Функция изменения параметров с учетом блокировки
  const set = (k, v) => {
    if (isInference && isParamLockedForInference(k, activeEnv, true)) {
      return
    }
    if (readOnly || paramsLocked) return
    setParams(p => ({ ...p, [k]: v }))
  }

  const isPatrol   = activeEnv === ENV.DISCRETE && activeTask === TASK.PATROL
  const isCoverage = activeEnv === ENV.CONTINUOUS && activeTask === TASK.COVERAGE
  const isClassic  = CLASSIC_ALGOS.has(algo)
  
  const isControlDisabled = running || readOnly || paramsLocked
  const isEnvDisabled = running || envLocked || readOnly

  const routeKey = `${activeEnv}/${activeTask}`
  const algos = ALGOS_BY_ROUTE?.[routeKey] ?? ["PPO"]

  const classicAlgos = algos.filter(a => CLASSIC_ALGOS.has(a))
  const rlAlgos      = algos.filter(a => !CLASSIC_ALGOS.has(a))
  const hasBothTypes = classicAlgos.length > 0 && rlAlgos.length > 0

  const [algoType, setAlgoType] = useState(() => CLASSIC_ALGOS.has(algo) ? "classic" : "rl")

  useEffect(() => {
    const newType = CLASSIC_ALGOS.has(algo) ? "classic" : "rl"
    if (algoType !== newType) {
      setAlgoType(newType)
    }
  }, [algo])

  // Обработчик смены алгоритма с фильтрацией параметров
  const handleAlgoChange = (e) => {
    const newAlgo = e.target.value
    if (newAlgo === algo) return
    
    const filteredParams = filterParamsForAlgo(params, newAlgo)
    
    setAlgo(newAlgo)
    setParams(filteredParams)
    setAlgoType(CLASSIC_ALGOS.has(newAlgo) ? "classic" : "rl")
  }

  const handleAlgoType = (type) => {
    if (readOnly || paramsLocked) return
    setAlgoType(type)
    const list = type === "classic" ? classicAlgos : rlAlgos
    if (list.length > 0 && !list.includes(algo)) {
      const newAlgo = list[0]
      const filteredParams = filterParamsForAlgo(params, newAlgo)
      setAlgo(newAlgo)
      setParams(filteredParams)
    }
  }

  useEffect(() => {
    const normalizedAlgo = algo?.toUpperCase()
    const normalizedAlgos = algos.map(a => a.toUpperCase())
    const isAlgoInList = normalizedAlgos.includes(normalizedAlgo)
    
    if (isAlgoInList) {
      if (algo !== algos[normalizedAlgos.indexOf(normalizedAlgo)]) {
        const correctCaseAlgo = algos[normalizedAlgos.indexOf(normalizedAlgo)]
        setAlgo(correctCaseAlgo)
      }
      return
    }
    
    if (algo && !isAlgoInList) {
      const first = algos[0]
      setAlgo(first)
      setAlgoType(CLASSIC_ALGOS.has(first) ? "classic" : "rl")
    }
  }, [routeKey, algo, algos, setAlgo])

  const handleJsonFile = (e) => {
    if (readOnly || paramsLocked) return
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (ev) => {
      try { setJsonConfig({ ...JSON.parse(ev.target.result), _fileName: file.name }) }
      catch { alert("Ошибка разбора JSON файла") }
    }
    reader.readAsText(file)
    e.target.value = ""
  }

  const [fitTabs, setFitTabs] = useState(false)
  const [canScrollRight, setCanScrollRight] = useState(false)
  const tabsRef = useRef(null)
  const dragState = useRef({ isDown: false, startX: 0, scrollLeft: 0, moved: false })

  const checkTabs = () => {
    const el = tabsRef.current
    if (!el) return
    setFitTabs(el.scrollWidth <= el.clientWidth)
    setCanScrollRight(el.scrollLeft < el.scrollWidth - el.clientWidth - 2)
  }
  
  const onMouseDown = (e) => {
    const el = tabsRef.current
    dragState.current = { isDown: true, startX: e.pageX - el.offsetLeft, scrollLeft: el.scrollLeft, moved: false }
    el.style.cursor = "grabbing"
  }
  
  const onMouseUp = () => { 
    dragState.current.isDown = false
    if (tabsRef.current) tabsRef.current.style.cursor = "grab" 
  }
  
  const onMouseMove = (e) => {
    if (!dragState.current.isDown) return
    const diff = (e.pageX - tabsRef.current.offsetLeft) - dragState.current.startX
    if (Math.abs(diff) > 3) dragState.current.moved = true
    tabsRef.current.scrollLeft = dragState.current.scrollLeft - diff
  }
  
  const onTabClick = (t) => { 
    if (!dragState.current.moved) setTab(t)
    dragState.current.moved = false 
  }

 const shouldShowSlider = (s) => {
    if (s.algoOnly) {
      const normalizedAlgo = algo.toUpperCase()
      const normalizedAlgoOnly = s.algoOnly.map(a => a.toUpperCase())
      const show = normalizedAlgoOnly.includes(normalizedAlgo)
          
      return show
    }
    return true
  }

  const availableTabs = ["Алгоритм", "Карта", "Агент", "Наблюдение", "Нарушитель", "Робот"]
    .filter(t => (SLIDER_CONFIG[activeEnv]?.[activeTask]?.[t] ?? []).some(sl => shouldShowSlider(sl)))

  useEffect(() => { 
    checkTabs()
    window.addEventListener("resize", checkTabs)
    return () => window.removeEventListener("resize", checkTabs)
  }, [availableTabs])
  
  useEffect(() => { 
    if (!availableTabs.includes(tab)) setTab(availableTabs[0]) 
  }, [availableTabs.join(","), tab])

  const sliders = SLIDER_CONFIG[activeEnv]?.[activeTask]?.[tab] ?? []
  const hideSliders = isPatrol && jsonConfig

  const isAlgoLocked = isInference || isControlDisabled

  return (
    <div style={{ width: 220, flexShrink: 0, display: "flex", flexDirection: "column", gap: 10 }}>

      {/* Конфигурация среды */}
      <div style={{ ...card, padding: 14 }}>
        <div style={secLabel}>Конфигурация</div>

        {envLocked ? (
          <>
            <Label>Среда</Label>
            <div style={{
              ...selStyle, marginBottom: 10,
              background: Theme.bg, color: Theme.textSecond,
              boxSizing: "border-box", overflow: "hidden",
              textOverflow: "ellipsis", whiteSpace: "nowrap",
            }}>{activeEnv}</div>
            <Label>Задача</Label>
            <div style={{
              ...selStyle, marginBottom: 6,
              background: Theme.bg, color: Theme.textSecond,
              boxSizing: "border-box", overflow: "hidden",
              textOverflow: "ellipsis", whiteSpace: "nowrap",
            }}>{activeTask}</div>
          </>
        ) : (
          <>
            <Label>Среда</Label>
            <select 
              value={activeEnv} 
              disabled={isEnvDisabled} 
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
              disabled={isEnvDisabled} 
              style={selStyle}
            >
              {TASKS_BY_ENV[activeEnv].map(t => <option key={t}>{t}</option>)}
            </select>
          </>
        )}

        <div style={{ marginTop: 12 }}>
          <Label>Конфиг (.json)</Label>
          {jsonConfig ? (
            <div style={{
              display: "flex", alignItems: "center", gap: 6, padding: "6px 8px",
              background: `${Theme.accent}12`, border: `1px solid ${Theme.accent}`, borderRadius: 6,
            }}>
              <span style={{ flex: 1, fontSize: 10, color: Theme.accent, fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {jsonConfig._fileName ?? "config.json"}
              </span>
              <button 
                onClick={() => setJsonConfig(null)} 
                disabled={isControlDisabled}
                style={{
                  padding: "1px 6px", fontSize: 10, color: Theme.textMuted,
                  background: "transparent", border: `1px solid ${Theme.border}`, borderRadius: 4,
                  cursor: isControlDisabled ? "not-allowed" : "pointer", flexShrink: 0,
                }}
              >✕</button>
            </div>
          ) : (
            <label style={{
              display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
              padding: "7px 0", fontSize: 11, color: Theme.textSecond,
              border: `1px dashed ${Theme.border}`, borderRadius: 6,
              cursor: isControlDisabled ? "not-allowed" : "pointer", 
              background: "transparent",
              opacity: isControlDisabled ? 0.6 : 1,
            }}>
              <input 
                type="file" accept=".json" 
                onChange={handleJsonFile} 
                disabled={isControlDisabled} 
                style={{ display: "none" }} 
              />
              + Загрузить файл
            </label>
          )}
        </div>
      </div>

      {/* Параметры */}
      <div style={{ ...card, overflow: "hidden", display: hideSliders ? "none" : undefined }}>
        <div style={{ position: "relative" }}>
          <div ref={tabsRef}
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
              borderBottom: `1px solid ${Theme.border}`
            }}
          >
            <div style={{ display: "flex", width: "100%" }}>
              {availableTabs.map(t => (
                <button 
                  key={t} 
                  onClick={() => onTabClick(t)} 
                  style={{
                    padding: "8px 10px", fontSize: 11,
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
                >{t}</button>
              ))}
            </div>
          </div>
          {canScrollRight && (
            <div style={{
              position: "absolute", right: 0, top: 0, bottom: 0, width: 24,
              background: "linear-gradient(270deg, #f8fafc, transparent)",
              pointerEvents: "none", zIndex: 1,
            }} />
          )}
        </div>

        <div style={{ padding: 14 }}>
          {tab === "Алгоритм" && (
            <>
              {hasBothTypes && (
                <div style={{ 
                  display: "flex", gap: 0, marginBottom: 12, 
                  border: `1px solid ${Theme.border}`, 
                  borderRadius: Theme.radiusSm, 
                  overflow: "hidden" 
                }}>
                  {[["rl", "RL"], ["classic", "Классический"]].map(([type, label]) => (
                    <button 
                      key={type} 
                      disabled={isAlgoLocked}  // ← блокируем в inference
                      onClick={() => handleAlgoType(type)}
                      style={{
                        flex: 1, padding: "5px 0", fontSize: 11, fontWeight: 600,
                        border: "none", 
                        cursor: isAlgoLocked ? "not-allowed" : "pointer",
                        background: algoType === type ? Theme.accent : "transparent",
                        color: algoType === type ? "#fff" : Theme.textSecond,
                        opacity: isAlgoLocked ? 0.6 : 1,
                        transition: "background 0.15s",
                      }}
                    >{label}</button>
                  ))}
                </div>
              )}

              <Label>Алгоритм</Label>
              <select 
                value={algo} 
                onChange={handleAlgoChange} 
                disabled={isAlgoLocked} 
                style={{ ...selStyle, marginBottom: 14, opacity: isAlgoLocked ? 0.6 : 1 }}
              >
                {(hasBothTypes
                  ? (algoType === "classic" ? classicAlgos : rlAlgos)
                  : algos
                ).map(a => <option key={a}>{a}</option>)}
              </select>
            </>
          )}

          {sliders.filter(s => shouldShowSlider(s)).length === 0
            ? <div style={{ fontSize: 11, color: Theme.textMuted }}>Нет параметров</div>
            : sliders.map(s => {
                const value = s.type === "bool"
                  ? (params[s.param] ?? false)
                  : (params[s.param] ?? DEFAULT_PARAMS[s.param] ?? s.min)
                
                const isLocked = isInference && isParamLockedForInference(s.param, activeEnv, true)
                
                return (
                  <Slider 
                    key={s.param} 
                    {...s} 
                    value={value} 
                    onChange={(k, v) => set(k, v)} 
                    disabled={isControlDisabled || isLocked}
                  />
                )
              })
          }
        </div>
      </div>
    </div>
  )
}
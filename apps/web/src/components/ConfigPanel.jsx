import { useEffect, useRef, useState } from "react"
import { Theme, card, secLabel, selStyle } from "../constants/colors"
import { 
  TASKS_BY_ENV,
  SLIDER_CONFIG,
  ALGO_SLIDER_PARAMS,
  filterParamsForAlgo,
  isParamLocked,
} from "../constants/config"
import { ENV, TASK, CLASSIC_ALGOS } from "../constants/envs"

// ── Dev-флаги раздела «Дискретная / Патруль» ───────────────────────────────
// Скрываем старые вкладки, оставляем только "Генерировать сценарий"
const HIDDEN_PATROL_TABS = ["Карта", "Агент", "Наблюдение", "Нарушитель", "Награды", "Окружение"]
const FREEZE_PATROL_SETTINGS = true

const Label = ({ children }) =>
  <div style={{ fontSize: 11, color: Theme.textSecond, marginBottom: 4 }}>{children}</div>

const CheckRow = ({ label, checked, onChange, disabled }) => (
  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
    <input
      type="checkbox"
      checked={!!checked}
      onChange={e => onChange?.(e.target.checked)}
      disabled={disabled}
      style={{ accentColor: Theme.accent, cursor: disabled ? "not-allowed" : "pointer" }}
    />
    <span style={{ fontSize: 11, color: Theme.textSecond }}>{label}</span>
  </div>
)

const CoordinatesGroup = ({ label, prefix, valueX, valueY, valueZ, onChange, disabled }) => {
  const setCoord = (coord, val) => {
    onChange(`${prefix}_position_${coord}`, parseFloat(val))
  }

  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ fontSize: 11, color: Theme.textSecond, marginBottom: 4 }}>{label}</div>
      <div style={{ display: "flex", gap: 8 }}>
        {["x", "y", "z"].map(coord => (
          <div key={coord} style={{ flex: 1 }}>
            <div style={{ fontSize: 10, color: Theme.textMuted, marginBottom: 2 }}>{coord.toUpperCase()}</div>
            <input
              type="number"
              value={coord === "x" ? valueX : coord === "y" ? valueY : valueZ ?? 0}
              onChange={e => setCoord(coord, e.target.value)}
              disabled={disabled}
              step={0.5}
              style={{
                width: "100%",
                padding: "4px 6px",
                fontSize: 11,
                background: disabled ? Theme.bgDisabled : Theme.bg,
                border: `1px solid ${Theme.border}`,
                borderRadius: Theme.radiusSm,
                color: Theme.textPrimary,
                boxSizing: "border-box",
              }}
            />
          </div>
        ))}
      </div>
    </div>
  )
}

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

  if (type === "number") {
    return (
      <div style={{ marginBottom: 12 }}>
        <div style={{ fontSize: 11, color: Theme.textSecond, marginBottom: 4 }}>{label}</div>
        <input
          type="number"
          value={value}
          onChange={e => onChange(param, parseFloat(e.target.value))}
          disabled={disabled}
          min={min} max={max} step={step}
          style={{
            width: "100%",
            padding: "6px 8px",
            fontSize: 11,
            background: disabled ? Theme.bgDisabled : Theme.bg,
            border: `1px solid ${Theme.border}`,
            borderRadius: Theme.radiusSm,
            color: Theme.textPrimary,
            boxSizing: "border-box",
          }}
        />
      </div>
    )
  }

  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, marginBottom: 4 }}>
        <span style={{ color: Theme.textSecond }}>{label}</span>
        <span style={{ color: Theme.textPrimary, fontWeight: 600, fontFamily: Theme.mono, fontSize: 11 }}>{value}</span>
      </div>
      <input type="range" min={min} max={max} step={step} value={value}
        onChange={e => onChange(param, type === "int" ? parseInt(e.target.value) : parseFloat(e.target.value))}
        disabled={disabled}
        style={{ width: "100%", accentColor: Theme.accent, cursor: disabled ? "not-allowed" : "pointer" }} />
    </div>
  )
}

export function normalizeAlgorithm(algo) {
  return (algo || "PPO").toUpperCase()
}

export function extractParamsFromRun(run) {
  const config = run?.config_json || {}
  const trainingParams = config.training_params || {}
  const runtimeConfig = config.runtime_config || {}

  const algorithm = normalizeAlgorithm(
    trainingParams.algorithm || runtimeConfig.algorithm || config.algorithm
  )

  const mergedParams = { ...trainingParams, ...runtimeConfig }

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
  isResuming = false,
  readOnly = false,
  algo, setAlgo,
  params, setParams,
  tab, setTab,
  running,
  jsonConfig, setJsonConfig,
  useConfigFiles = false,
  setUseConfigFiles,
  loadMapFromConfig = false,
  setLoadMapFromConfig,
  visualize = false,
  setVisualize,
  algoConfigJson = null,
  setAlgoConfigJson,
  envConfigJson = null,
  setEnvConfigJson,
  valEnvConfigJson = null,
  setValEnvConfigJson,
  stepDelay = 0,
  setStepDelay,
  useGeneratedForValidation = false,
  setUseGeneratedForValidation,
}) {

  const isPatrol = activeEnv === ENV.DISCRETE && activeTask === TASK.PATROL
  const isClassic = CLASSIC_ALGOS.has(algo)
  const isControlDisabled = running || readOnly || paramsLocked || isResuming
  const isEnvDisabled = running || envLocked || readOnly
  const isAlgoLocked = isInference || isResuming || isControlDisabled
  const isSlidersDisabled = isControlDisabled

  const valConfigProvided = valEnvConfigJson !== null
  const validationEnabled = valConfigProvided || useGeneratedForValidation

  const set = (k, v) => {
    if ((isInference || isResuming || running) && isParamLocked(k, activeEnv)) return
    if (readOnly || paramsLocked) return
    setParams(p => ({ ...p, [k]: v }))
  }

  const algosConfig = SLIDER_CONFIG[activeEnv]?.[activeTask]?.algos ?? { "PPO": { excludeParams: [] } }
  const algos = Object.keys(algosConfig)
  const classicAlgos = algos.filter(a => CLASSIC_ALGOS.has(a))
  const rlAlgos = algos.filter(a => !CLASSIC_ALGOS.has(a))
  const hasBothTypes = classicAlgos.length > 0 && rlAlgos.length > 0

  const [algoType, setAlgoType] = useState(() => CLASSIC_ALGOS.has(algo) ? "classic" : "rl")

  useEffect(() => {
    const newType = CLASSIC_ALGOS.has(algo) ? "classic" : "rl"
    if (algoType !== newType) setAlgoType(newType)
  }, [algo])

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
      const correctCase = algos[normalizedAlgos.indexOf(normalizedAlgo)]
      if (algo !== correctCase) setAlgo(correctCase)
      return
    }

    if (!isAlgoInList && algos.length > 0) {
      const first = algos[0]
      setAlgo(first)
      setAlgoType(CLASSIC_ALGOS.has(first) ? "classic" : "rl")
    }
  }, [activeEnv, activeTask, algo, algos, setAlgo])

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

  const handleConfigFile = (e, setter) => {
    if (isControlDisabled) return
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (ev) => {
      try { setter({ ...JSON.parse(ev.target.result), _fileName: file.name }) }
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

  const shouldShowEnvSlider = (s) => {
    if (["robot_position_y", "robot_position_z", "target_position_y", "target_position_z"].includes(s.param)) {
      return false
    }
    if (s.algoOnly) {
      const normalizedAlgo = algo.toUpperCase()
      const normalizedAlgoOnly = s.algoOnly.map(a => a.toUpperCase())
      return normalizedAlgoOnly.includes(normalizedAlgo)
    }
    return true
  }

  const renderSliderOrCoordinates = (s) => {
    if (s.type === "coordinates" && s.group === "robot") {
      if (s.param !== "robot_position_x") return null
      return (
        <CoordinatesGroup
          key="robot_coords"
          label="Позиция робота"
          prefix="robot"
          valueX={params.robot_position_x ?? s.default ?? 0}
          valueY={params.robot_position_y ?? 0}
          valueZ={params.robot_position_z ?? 0}
          onChange={set}
          disabled={isSlidersDisabled}
        />
      )
    }

    if (s.type === "coordinates" && s.group === "target") {
      if (s.param !== "target_position_x") return null
      return (
        <CoordinatesGroup
          key="target_coords"
          label="Позиция цели"
          prefix="target"
          valueX={params.target_position_x ?? s.default ?? 5}
          valueY={params.target_position_y ?? 0}
          valueZ={params.target_position_z ?? 5}
          onChange={set}
          disabled={isSlidersDisabled}
        />
      )
    }

    const value = s.type === "bool"
      ? (params[s.param] ?? s.default ?? false)
      : (params[s.param] ?? s.default ?? s.min)
    const isLocked = (isInference || isResuming || running) && isParamLocked(s.param, activeEnv)

    return (
      <Slider
        key={s.param}
        {...s}
        value={value}
        onChange={(k, v) => set(k, v)}
        disabled={isSlidersDisabled || isLocked}
      />
    )
  }

  const envConfig = SLIDER_CONFIG[activeEnv]?.[activeTask] ?? {}
  const excludeParams = algosConfig[algo]?.excludeParams ?? []
  const algoSliders = (ALGO_SLIDER_PARAMS[algo] ?? []).filter(s => !excludeParams.includes(s.param))

  // Вкладки из SLIDER_CONFIG (все, кроме algos и Алгоритм)
  const tabsFromConfig = Object.keys(envConfig)
    .filter(key => key !== "algos" && key !== "Алгоритм")
    .filter(key => (envConfig[key] ?? []).some(sl => shouldShowEnvSlider(sl)))
    .filter(key => !(isPatrol && HIDDEN_PATROL_TABS.includes(key)))

  // Для патруля: Алгоритм + Генерировать сценарий + Настройки + Конфигурации
  // Для остальных: Алгоритм + все вкладки из SLIDER_CONFIG
  const availableTabs = isPatrol
    ? ["Алгоритм", "Генерировать сценарий", "Настройки", "Конфигурации"]
    : ["Алгоритм", ...tabsFromConfig]

  useEffect(() => {
    checkTabs()
    window.addEventListener("resize", checkTabs)
    return () => window.removeEventListener("resize", checkTabs)
  }, [availableTabs])

  useEffect(() => {
    if (!availableTabs.includes(tab)) setTab(availableTabs[0])
  }, [availableTabs.join(","), tab])

  const envSliders = (envConfig[tab] ?? []).filter(shouldShowEnvSlider)
  const hideSliders = isPatrol && jsonConfig

  const fileUploadStyle = (disabled) => ({
    display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
    padding: "7px 0", fontSize: 11, color: Theme.textSecond,
    border: `1px dashed ${Theme.border}`, borderRadius: 6,
    cursor: disabled ? "not-allowed" : "pointer",
    background: "transparent",
    opacity: disabled ? 0.6 : 1,
  })

  const fileLoadedStyle = {
    display: "flex", alignItems: "center", gap: 6, padding: "6px 8px",
    background: `${Theme.accent}12`, border: `1px solid ${Theme.accent}`, borderRadius: 6,
  }

  const fileRemoveBtn = (disabled) => ({
    padding: "1px 6px", fontSize: 10, color: Theme.textMuted,
    background: "transparent", border: `1px solid ${Theme.border}`, borderRadius: 4,
    cursor: disabled ? "not-allowed" : "pointer", flexShrink: 0,
  })

  return (
    <div style={{ width: 220, flexShrink: 0, display: "flex", flexDirection: "column", gap: 10 }}>

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

        {!isPatrol && <div style={{ marginTop: 12 }}>
          <Label>Конфиг (.json)</Label>
          {jsonConfig ? (
            <div style={fileLoadedStyle}>
              <span style={{ flex: 1, fontSize: 10, color: Theme.accent, fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {jsonConfig._fileName ?? "config.json"}
              </span>
              <button
                onClick={() => setJsonConfig(null)}
                disabled={isControlDisabled}
                style={fileRemoveBtn(isControlDisabled)}
              >✕</button>
            </div>
          ) : (
            <label style={fileUploadStyle(isControlDisabled)}>
              <input
                type="file" accept=".json"
                onChange={handleJsonFile}
                disabled={isControlDisabled}
                style={{ display: "none" }}
              />
              + Загрузить файл
            </label>
          )}
        </div>}
      </div>

      <div style={{ ...card, overflow: "hidden", display: hideSliders ? "none" : undefined }}>
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
                  overflow: "hidden",
                }}>
                  {[["rl", "RL"], ["classic", "Классический"]].map(([type, label]) => (
                    <button
                      key={type}
                      disabled={isAlgoLocked}
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

              <div style={{
                maxHeight: 380,
                overflowY: "auto",
                overflowX: "hidden",
                scrollbarWidth: "thin",
                scrollbarColor: "#d1d5db #f9fafb",
                marginRight: -8,
                paddingRight: 8,
              }}>
                {envConfig["Алгоритм"]?.length > 0 && (
                  <>
                    <div style={{ height: 12 }} />
                    {envConfig["Алгоритм"]
                      .filter(shouldShowEnvSlider)
                      .map(s => renderSliderOrCoordinates(s))}
                  </>
                )}

                {algoSliders.length === 0
                  ? <div style={{ fontSize: 11, color: Theme.textMuted }}>Нет параметров</div>
                  : algoSliders.map(s => {
                      const value = params[s.param] ?? s.default ?? s.min
                      const isLocked = (isInference || isResuming || running) && isParamLocked(s.param, activeEnv)
                      return (
                        <Slider
                          key={s.param}
                          {...s}
                          value={value}
                          onChange={(k, v) => set(k, v)}
                          disabled={isSlidersDisabled || isLocked}
                        />
                      )
                    })
                }
              </div>
            </>
          )}

          {tab === "Настройки" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <CheckRow
                label="Визуализировать обучение"
                checked={visualize}
                onChange={v => setVisualize?.(v)}
                disabled={FREEZE_PATROL_SETTINGS || isControlDisabled}
              />
              <CheckRow
                label="Использовать конфиги"
                checked={useConfigFiles}
                onChange={v => {
                  setUseConfigFiles?.(v)
                  if (!v) setLoadMapFromConfig?.(false)
                }}
                disabled={FREEZE_PATROL_SETTINGS || isControlDisabled}
              />
              <CheckRow
                label="Загрузка карты из конфига"
                checked={loadMapFromConfig}
                onChange={v => setLoadMapFromConfig?.(v)}
                disabled={isControlDisabled || !useConfigFiles}
              />
              {FREEZE_PATROL_SETTINGS && (
                <div style={{ fontSize: 10, color: Theme.textMuted, lineHeight: 1.4 }}>
                  Режимы «Визуализировать обучение» и «Использовать конфиги» зафиксированы.
                </div>
              )}
            </div>
          )}

          {tab === "Конфигурации" && (
            <div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 16 }}>
                <div>
                  <Label>Шагов обучения</Label>
                  <input
                    type="number"
                    value={params.total_timesteps ?? 3000000}
                    min={100000} max={20000000} step={100000}
                    disabled={isControlDisabled}
                    onChange={e => setParams?.(p => ({ ...p, total_timesteps: parseInt(e.target.value) || 3000000 }))}
                    style={{
                      width: "100%", padding: "6px 8px", fontSize: 12,
                      background: Theme.surface, color: Theme.textPrimary,
                      border: `1px solid ${Theme.border}`, borderRadius: Theme.radiusSm,
                      boxSizing: "border-box",
                      opacity: isControlDisabled ? 0.5 : 1,
                    }}
                  />
                </div>
                <div>
                  <Label>Сид</Label>
                  <input
                    type="number"
                    value={params.seed ?? 42}
                    min={0} max={999999} step={1}
                    disabled={isControlDisabled}
                    onChange={e => setParams?.(p => ({ ...p, seed: parseInt(e.target.value) || 0 }))}
                    style={{
                      width: "100%", padding: "6px 8px", fontSize: 12,
                      background: Theme.surface, color: Theme.textPrimary,
                      border: `1px solid ${Theme.border}`, borderRadius: Theme.radiusSm,
                      boxSizing: "border-box",
                      opacity: isControlDisabled ? 0.5 : 1,
                    }}
                  />
                </div>
              </div>

              <div style={{ marginBottom: 16 }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, marginBottom: 4 }}>
                  <span style={{ color: visualize ? Theme.textSecond : Theme.textMuted }}>Задержка обновления</span>
                  <span style={{ color: Theme.textPrimary, fontWeight: 600, fontFamily: Theme.mono, fontSize: 11 }}>{stepDelay} мс</span>
                </div>
                <input
                  type="range"
                  min={0} max={500} step={10}
                  value={stepDelay}
                  onChange={e => setStepDelay?.(parseInt(e.target.value))}
                  disabled={isControlDisabled || !visualize}
                  style={{ width: "100%", accentColor: Theme.accent, cursor: (isControlDisabled || !visualize) ? "not-allowed" : "pointer", opacity: visualize ? 1 : 0.4 }}
                />
              </div>

              <div style={{ marginBottom: 16 }}>
                <Label>Конфиг алгоритма (.json)</Label>
                <div style={{ fontSize: 10, color: Theme.textMuted, marginBottom: 6 }}>
                  {algo}TrainConfig
                </div>
                {algoConfigJson ? (
                  <div style={fileLoadedStyle}>
                    <span style={{ flex: 1, fontSize: 10, color: Theme.accent, fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {algoConfigJson._fileName ?? "algo_config.json"}
                    </span>
                    <button
                      onClick={() => setAlgoConfigJson?.(null)}
                      disabled={isControlDisabled}
                      style={fileRemoveBtn(isControlDisabled)}
                    >✕</button>
                  </div>
                ) : (
                  <label style={fileUploadStyle(isControlDisabled)}>
                    <input type="file" accept=".json" onChange={e => handleConfigFile(e, setAlgoConfigJson)} disabled={isControlDisabled} style={{ display: "none" }} />
                    + Загрузить
                  </label>
                )}
              </div>

              <div style={{ marginBottom: 16 }}>
                <Label>Конфиг среды (.json)</Label>
                <div style={{ fontSize: 10, color: Theme.textMuted, marginBottom: 6 }}>
                  GridForestConfig
                </div>
                {envConfigJson ? (
                  <div style={fileLoadedStyle}>
                    <span style={{ flex: 1, fontSize: 10, color: Theme.accent, fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {envConfigJson._fileName ?? "env_config.json"}
                    </span>
                    <button
                      onClick={() => setEnvConfigJson?.(null)}
                      disabled={isControlDisabled}
                      style={fileRemoveBtn(isControlDisabled)}
                    >✕</button>
                  </div>
                ) : (
                  <label style={fileUploadStyle(isControlDisabled)}>
                    <input type="file" accept=".json" onChange={e => handleConfigFile(e, setEnvConfigJson)} disabled={isControlDisabled} style={{ display: "none" }} />
                    + Загрузить
                  </label>
                )}
              </div>

              <div>
                <Label>Конфиг среды для валидации (.json)</Label>
                <div style={{ fontSize: 10, color: Theme.textMuted, marginBottom: 6 }}>
                  GridForestConfig (опционально)
                </div>
                {valEnvConfigJson ? (
                  <div style={fileLoadedStyle}>
                    <span style={{ flex: 1, fontSize: 10, color: Theme.accent, fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {valEnvConfigJson._fileName ?? "val_env_config.json"}
                    </span>
                    <button
                      onClick={() => setValEnvConfigJson?.(null)}
                      disabled={isControlDisabled}
                      style={fileRemoveBtn(isControlDisabled)}
                    >✕</button>
                  </div>
                ) : (
                  <label style={fileUploadStyle(isControlDisabled)}>
                    <input type="file" accept=".json" onChange={e => handleConfigFile(e, setValEnvConfigJson)} disabled={isControlDisabled} style={{ display: "none" }} />
                    + Загрузить
                  </label>
                )}
              </div>

              {(() => {
                const valDisabled = isControlDisabled || !validationEnabled
                const valInput = (key, def, min, max, step) => (
                  <input
                    type="number"
                    value={params[key] ?? def}
                    min={min} max={max} step={step}
                    disabled={valDisabled}
                    onChange={e => setParams?.(p => ({ ...p, [key]: parseInt(e.target.value) || def }))}
                    style={{
                      width: "100%", padding: "6px 8px", fontSize: 12,
                      background: Theme.surface, color: Theme.textPrimary,
                      border: `1px solid ${Theme.border}`, borderRadius: Theme.radiusSm,
                      boxSizing: "border-box", opacity: valDisabled ? 0.5 : 1,
                    }}
                  />
                )
                return (
                  <div style={{ marginTop: 16 }}>
                    <Label>Настройки валидации</Label>
                    <div style={{ fontSize: 10, color: validationEnabled ? Theme.accent : Theme.textMuted, marginBottom: 8 }}>
                      {validationEnabled
                        ? (valConfigProvided ? "Включена (конфиг среды задан)" : "Включена (сгенерированный сценарий)")
                        : "Выключена — задайте конфиг среды или отметьте «Использовать для валидации»"}
                    </div>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 8 }}>
                      <div>
                        <Label>Сид</Label>
                        {valInput("validation_seed", 2026, 0, 999999, 1)}
                      </div>
                      <div>
                        <Label>Эпизодов</Label>
                        {valInput("validation_n_episodes", 20, 1, 200, 1)}
                      </div>
                    </div>
                    <div>
                      <Label>Частота (шагов)</Label>
                      {valInput("validation_freq", 100000, 1000, 5000000, 1000)}
                    </div>
                  </div>
                )
              })()}
            </div>
          )}

          {tab === "Генерировать сценарий" && (
            <>
              {envSliders.map(s => renderSliderOrCoordinates(s))}
              <div style={{ marginTop: 10, paddingTop: 12, borderTop: `1px solid ${Theme.border}` }}>
                <CheckRow
                  label="Использовать для валидации"
                  checked={useGeneratedForValidation}
                  onChange={v => setUseGeneratedForValidation?.(v)}
                  disabled={isControlDisabled || valConfigProvided}
                />
                <div style={{ fontSize: 10, color: Theme.textMuted, marginTop: 4, lineHeight: 1.4 }}>
                  {valConfigProvided
                    ? "Валидация уже задана конфигом во вкладке «Конфигурации»."
                    : "После генерации эта же карта будет использоваться для валидации."}
                </div>
              </div>
            </>
          )}

          {tab !== "Алгоритм" && tab !== "Настройки" && tab !== "Конфигурации" && tab !== "Генерировать сценарий" && (
            envSliders.length === 0
              ? <div style={{ fontSize: 11, color: Theme.textMuted }}>Нет параметров</div>
              : envSliders.map(s => renderSliderOrCoordinates(s))
          )}
        </div>
      </div>
    </div>
  )
}
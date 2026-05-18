import { useState, useEffect, useRef, useCallback } from "react"
import { Theme, card } from "../constants/colors"
import { useCanvasRender } from "../hooks/useCanvasRender"
import { ConfigPanel, extractParamsFromRun } from "../components/ConfigPanel"
import { CanvasPanel } from "../components/CanvasPanel"
import { ENV, TASK } from "../constants/envs"
import { API_PROTOCOL, API_ADDRESS, API_PORT } from "../constants/envs"

const API_BASE = `${API_PROTOCOL}${API_ADDRESS}:${API_PORT}`

function routeKeyToEnv(routeKey) {
  if (!routeKey) return ENV.DISCRETE
  if (routeKey.startsWith("continuous")) return ENV.CONTINUOUS
  if (routeKey.startsWith("threed"))     return ENV.SIM_3D
  return ENV.DISCRETE
}

function routeKeyToTask(routeKey) {
  if (!routeKey) return TASK.TRAIL
  if (routeKey.endsWith("trail")) return TASK.TRAIL
  if (routeKey.endsWith("patrol")) return TASK.PATROL
  if (routeKey.endsWith("coverage")) return TASK.COVERAGE
  if (routeKey.endsWith("reforestation")) return TASK.REFORESTATION
  return TASK.TRAIL
}

function Btn({ onClick, disabled, color = Theme.accent, children, style = {} }) {
  return (
    <button onClick={onClick} disabled={disabled} style={{
      padding: "6px 10px",
      fontSize: 12,
      fontWeight: 700,
      border: "none",
      borderRadius: Theme.radiusSm,
      background: disabled ? Theme.textMuted : color,
      color: "#fff",
      cursor: disabled ? "not-allowed" : "pointer",
      opacity: disabled ? 0.6 : 1,
      whiteSpace: "nowrap",
      ...style,
    }}>{children}</button>
  )
}

export function ReplayPage({ nav, ctx = {} }) {
  const { runId, runTitle, routeKey } = ctx

  const [frames,      setFrames]      = useState([])
  const [cursor,      setCursor]      = useState(0)
  const [playing,     setPlaying]     = useState(false)
  const [loading,     setLoading]     = useState(true)
  const [error,       setError]       = useState(null)
  const [speed,       setSpeed]       = useState(1)
  const [runData,     setRunData]     = useState(null)
  
  const [activeEnv,   setActiveEnv]   = useState(routeKeyToEnv(routeKey))
  const [activeTask,  setActiveTask]  = useState(routeKeyToTask(routeKey))
  const [algo,        setAlgo]        = useState("PPO")
  const [params,      setParams]      = useState({})
  const [tab,         setTab]         = useState("Алгоритм")
  const [showTrail,   setShowTrail]   = useState(true)
  const [showObs,     setShowObs]     = useState(true)

  const intervalRef = useRef(null)

  const currentFrame = frames[cursor] ?? null
  const frameState   = currentFrame?.state ?? null
  const gridSize     = frameState?.grid_size ?? frameState?.world_size ?? 20

  const { canvasRef } = useCanvasRender(activeEnv, frameState, gridSize, showTrail, showObs, 3)

  useEffect(() => {
    if (!runId) { setError("Не указан run"); setLoading(false); return }
    
    Promise.all([
      fetch(`${API_BASE}/api/runs/${runId}`).then(r => r.ok ? r.json() : null),
      fetch(`${API_BASE}/api/runs/${runId}/replay`).then(r => r.ok ? r.json() : null)
    ])
      .then(([run, replay]) => {
        if (run) {
          setRunData(run)
          
          const { algorithm, mergedParams, env, task } = extractParamsFromRun(run)
          
          setAlgo(algorithm)
          setParams(mergedParams)
          setActiveEnv(env)
          setActiveTask(task)
        }
        
        if (!replay || !replay.frames || replay.frames.length === 0) {
          setError("Реплей пуст или не найден")
        } else {
          setFrames(replay.frames)
          setCursor(0)
        }
      })
      .catch(() => setError("Не удалось загрузить реплей"))
      .finally(() => setLoading(false))
  }, [runId])

  const stopPlayback = useCallback(() => {
    clearInterval(intervalRef.current)
    setPlaying(false)
  }, [])

  const startPlayback = useCallback(() => {
    if (frames.length === 0) return
    setCursor(prev => prev >= frames.length - 1 ? 0 : prev)
    setPlaying(true)
  }, [frames.length])

  useEffect(() => {
    if (!playing || frames.length === 0) return
    const fps = Math.max(1, Math.round(10 * speed))
    intervalRef.current = setInterval(() => {
      setCursor(prev => {
        const next = prev + 1
        if (next >= frames.length) { stopPlayback(); return prev }
        return next
      })
    }, 1000 / fps)
    return () => clearInterval(intervalRef.current)
  }, [playing, speed, frames.length, stopPlayback])

  return (
    <div style={{ minHeight: "100vh", background: Theme.bg }}>

      {/* Header */}
      <div style={{
        background: Theme.surface,
        borderBottom: `1px solid ${Theme.border}`,
        padding: "0 20px",
        height: 46,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        boxShadow: Theme.shadowSm,
      }}>
        <button
          onClick={() => nav("home")}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            background: "none",
            border: "none",
            cursor: "pointer",
            color: Theme.textSecond,
            fontSize: 13,
            padding: "4px 8px",
            borderRadius: Theme.radiusSm,
          }}
        >
          ← Эксперименты
        </button>
        <span style={{ fontSize: 13, fontWeight: 600, color: Theme.textPrimary }}>
          Реплей: {runTitle || `Run #${runId}`}
        </span>
        <span style={{ fontSize: 11, color: Theme.textMuted, minWidth: 80, textAlign: "right" }}>
          {loading ? "загрузка..." : error ? "ошибка" : `${frames.length} кадров`}
        </span>
      </div>

      <div style={{ padding: "24px 32px" }}>
        <div style={{
          display: "flex",
          gap: 24,
          justifyContent: "center",
          alignItems: "flex-start",
        }}>
          <ConfigPanel
            activeEnv={activeEnv}
            setActiveEnv={() => {}}
            activeTask={activeTask}
            setActiveTask={() => {}}
            envLocked={true}
            readOnly={true}   
            isInference={false}
            algo={algo}
            setAlgo={() => {}}
            params={params}
            setParams={() => {}}
            tab={tab}
            setTab={setTab}
            running={false}
            jsonConfig={null}
            setJsonConfig={() => {}}
          />

          <div style={{ flexShrink: 0 }}>
            <CanvasPanel
              activeEnv={activeEnv}
              activeTask={activeTask}
              state={frameState}
              canvasRef={canvasRef}
              showTrail={showTrail}
              setShowTrail={setShowTrail}
              showObs={showObs}
              setShowObs={setShowObs}
            />

            {/* Панель управления воспроизведением */}
            <div style={{
              ...card,
              padding: "10px 12px",
              marginTop: 10,
              display: "flex",
              alignItems: "center",
              gap: 8,
              flexWrap: "nowrap",  
            }}>
              <div style={{ fontSize: 11, color: Theme.textMuted, whiteSpace: "nowrap", minWidth: 45 }}>
                Кадры {cursor + 1}/{frames.length}
              </div>
              
              <input
                type="range"
                min={0}
                max={Math.max(0, frames.length - 1)}
                value={cursor}
                onChange={e => { stopPlayback(); setCursor(+e.target.value) }}
                style={{ width: 200, accentColor: Theme.accent }}  
              />

              <Btn
                onClick={() => { stopPlayback(); setCursor(p => Math.max(0, p - 1)) }}
                disabled={cursor <= 0}
                color={Theme.textMuted}
              >◀</Btn>

              {playing
                ? <Btn onClick={stopPlayback} color={Theme.red}>⏸</Btn>
                : <Btn
                    onClick={startPlayback}
                    disabled={frames.length === 0}
                    color={Theme.green}
                  >
                    ▶
                  </Btn>
              }

              <Btn
                onClick={() => { stopPlayback(); setCursor(p => Math.min(frames.length - 1, p + 1)) }}
                disabled={cursor >= frames.length - 1}
                color={Theme.textMuted}
              >▶</Btn>

              <Btn
                onClick={() => { stopPlayback(); setCursor(0) }}
                disabled={cursor === 0}
                color={Theme.textMuted}
              >↺</Btn>

              {/* Скорость */}
              <div style={{ display: "flex", alignItems: "center", gap: 6, whiteSpace: "nowrap" }}>
                <span style={{ fontSize: 10, color: Theme.textMuted }}>Скорость ×{speed}</span>
                <input
                  type="range"
                  min={0.5}
                  max={5}
                  step={0.5}
                  value={speed}
                  onChange={e => setSpeed(+e.target.value)}
                  style={{ width: 80, accentColor: Theme.accent }}
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
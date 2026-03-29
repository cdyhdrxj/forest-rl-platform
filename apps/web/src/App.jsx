import { useCallback, useEffect, useRef, useState } from "react"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts"
import { Theme, card, secLabel, selStyle } from "./constants/colors"

const TASKS_BY_ENV = {
  "Continuous 2D": ["Trail"],
  "Three-dimensional": ["Patrol", "Trail"],
  "Discrete": ["Patrol", "Planting"],
}

const WS_MAP = {
  "Continuous 2D/Trail": "ws://127.0.0.1:8000/continuous/trail",
  "Three-dimensional/Patrol": "ws://127.0.0.1:8000/threed/patrol",
  "Three-dimensional/Trail": "ws://127.0.0.1:8000/threed/trail",
  "Discrete/Patrol": "ws://127.0.0.1:8000/discrete/patrol",
  "Discrete/Planting": "ws://127.0.0.1:8000/discrete/reforestation",
}

const CANVAS_SIZE = 380

const METRICS = [
  ["Episode", s => s?.episode ?? 0, null],
  ["Step", s => s?.step ?? 0, null],
  ["Reward", s => (s?.total_reward != null ? s.total_reward.toFixed(1) : "0.0"), null],
  ["Completed", s => s?.goal_count ?? 0, Theme.green],
  ["Blocked", s => s?.collision_count ?? 0, Theme.red],
]

const LEGEND = [
  [Theme.accent, "Robot"],
  [Theme.green, "Plantable"],
  ["#16a34a", "Planted"],
  [Theme.textMuted, "Obstacle"],
  [Theme.red, "Collision"],
]

const Label = ({ children }) => (
  <div style={{ fontSize: 11, color: Theme.textSecond, marginBottom: 4 }}>{children}</div>
)

const Dot = ({ color, size = 7 }) => (
  <span
    style={{
      display: "inline-block",
      width: size,
      height: size,
      borderRadius: "50%",
      background: color,
      flexShrink: 0,
    }}
  />
)

const Btn = ({ onClick, disabled, color, children }) => (
  <button
    onClick={onClick}
    disabled={disabled}
    style={{
      padding: "10px",
      background: disabled ? Theme.textMuted : color,
      color: "white",
      border: "none",
      borderRadius: Theme.radiusSm,
      cursor: disabled ? "not-allowed" : "pointer",
      fontWeight: 700,
      fontSize: 13,
      boxShadow: disabled ? "none" : `0 1px 3px ${color}55`,
    }}
  >
    {children}
  </button>
)

function drawCanvas(canvas, state, terrain) {
  const ctx = canvas.getContext("2d")
  ctx.clearRect(0, 0, CANVAS_SIZE, CANVAS_SIZE)
  ctx.fillStyle = "#fafafa"
  ctx.fillRect(0, 0, CANVAS_SIZE, CANVAS_SIZE)

  const map = terrain ?? state?.terrain_map
  if (map?.length) {
    const rows = map.length
    const cols = map[0].length
    const cw = CANVAS_SIZE / cols
    const ch = CANVAS_SIZE / rows

    for (let y = 0; y < rows; y += 1) {
      for (let x = 0; x < cols; x += 1) {
        ctx.strokeStyle = "#e5e7eb"
        ctx.lineWidth = 1
        ctx.strokeRect(x * cw, y * ch, cw, ch)

        if (map[y][x] > 0.5) {
          ctx.fillStyle = "rgba(156,163,175,0.55)"
          ctx.fillRect(x * cw, y * ch, cw, ch)
        }
      }
    }

    const fillCells = (positions, color, inset = 0.18) => {
      positions?.forEach(([py, px]) => {
        ctx.fillStyle = color
        ctx.fillRect(
          px * cw + cw * inset,
          py * ch + ch * inset,
          cw * (1 - inset * 2),
          ch * (1 - inset * 2),
        )
      })
    }

    fillCells(state?.goal_pos, "rgba(34,197,94,0.35)", 0.08)
    fillCells(state?.planted_pos, "#16a34a", 0.18)
    fillCells(state?.landmark_pos, "#9ca3af", 0.12)

    const trajectory = state?.trajectory ?? []
    if (trajectory.length > 1) {
      ctx.beginPath()
      ctx.strokeStyle = "rgba(37,99,235,0.35)"
      ctx.lineWidth = 2
      trajectory.forEach(([py, px], index) => {
        const tx = px * cw + cw / 2
        const ty = py * ch + ch / 2
        if (index === 0) ctx.moveTo(tx, ty)
        else ctx.lineTo(tx, ty)
      })
      ctx.stroke()
    }

    state?.agent_pos?.forEach(([py, px]) => {
      ctx.fillStyle = state?.is_collision ? Theme.red : Theme.accent
      ctx.beginPath()
      ctx.arc(px * cw + cw / 2, py * ch + ch / 2, Math.min(cw, ch) * 0.24, 0, Math.PI * 2)
      ctx.fill()
    })
    return
  }

  ctx.strokeStyle = "#e5e7eb"
  ctx.strokeRect(0, 0, CANVAS_SIZE, CANVAS_SIZE)
}

function describeExecutionPhase(executionPhase, scenarioReady, activeEnv, activeTask, algo, runId) {
  const runLabel = `run ${runId ?? "?"}`
  const statusLabel = executionPhase === "running"
    ? `Running - ${runLabel}`
    : executionPhase === "finished"
      ? `Finished - ${runLabel}`
      : executionPhase === "cancelled" || executionPhase === "stopped"
        ? `Stopped - ${runLabel}`
        : executionPhase === "failed"
          ? `Failed - ${runLabel}`
          : scenarioReady
            ? `Preview ready - ${runLabel}`
            : "Waiting for generation"

  const bannerLabel = executionPhase === "running"
    ? `Training - ${activeEnv} / ${activeTask} - ${algo}`
    : executionPhase === "finished"
      ? `Finished - ${activeEnv} / ${activeTask}`
      : executionPhase === "cancelled" || executionPhase === "stopped"
        ? `Stopped - ${activeEnv} / ${activeTask}`
        : executionPhase === "failed"
          ? `Failed - ${activeEnv} / ${activeTask}`
          : scenarioReady
            ? `Preview ready - ${activeEnv} / ${activeTask}`
            : "Waiting to start"

  return { statusLabel, bannerLabel }
}

export default function App() {
  const [activeEnv, setActiveEnv] = useState("Discrete")
  const [activeTask, setActiveTask] = useState("Planting")
  const [algo, setAlgo] = useState("PPO")
  const [state, setState] = useState(null)
  const [chartData, setChartData] = useState([])
  const [running, setRunning] = useState(false)
  const [tab, setTab] = useState("Algorithm")
  const [terrain, setTerrain] = useState(null)
  const canvasRef = useRef(null)
  const wsRef = useRef(null)

  const [params, setParams] = useState({
    learning_rate: 0.0003,
    gamma: 0.99,
    tau: 0.005,
    grid_size: 12,
    max_steps: 240,
    obstacle_density: 0.12,
    plantable_density: 0.7,
    initial_seedlings: 30,
    min_plant_distance: 1,
    uniformity_radius: 1,
    target_density: 0.35,
    alpha_plant: 4.0,
    alpha_quality: 2.0,
    beta_move: 0.08,
    beta_turn: 0.04,
    beta_fail_move: 0.25,
    beta_stay: 0.12,
    beta_invalid_plant: 0.6,
    lambda_uniformity: 3.0,
    lambda_underplanting: 1.5,
    goal_reward: 50.0,
    collision_penalty: 0.3,
    step_penalty: 0.0,
    action_scale: 1.0,
    max_speed: 50.0,
    accel: 40.0,
    damping: 0.6,
    dt: 0.01,
    terrain_penalty: 0.03,
  })

  const set = (key, value) => setParams(prev => ({ ...prev, [key]: value }))
  const endpoint = WS_MAP[`${activeEnv}/${activeTask}`]

  useEffect(() => {
    if (!endpoint) return undefined

    if (running) {
      wsRef.current?.send(JSON.stringify({ action: "stop" }))
      setRunning(false)
    }

    setState(null)
    setChartData([])
    setTerrain(null)
    wsRef.current?.close()

    const ws = new WebSocket(endpoint)
    wsRef.current = ws
    ws.onmessage = event => {
      const data = JSON.parse(event.data)
      setState(data)
      setRunning(data?.execution_phase === "running" || Boolean(data?.running))
      if (data.terrain_map) setTerrain(data.terrain_map)
      if (data.new_episode) {
        setChartData(prev => {
          const episodeNum = Math.max(0, (data.episode ?? 1) - 1)
          if (prev.length && prev[prev.length - 1].i === episodeNum) return prev
          return [...prev.slice(-99), { i: episodeNum, r: data.last_episode_reward ?? 0 }]
        })
      }
    }
    ws.onerror = error => console.error("ws error", error)
    return () => ws.close()
  }, [endpoint])

  useEffect(() => {
    if (canvasRef.current) drawCanvas(canvasRef.current, state, terrain)
  }, [state, terrain])

  const generate = useCallback(() => {
    if (!endpoint) return
    const mode = activeTask === "Trail" ? "trail" : activeTask === "Planting" ? "reforestation" : "patrol"
    wsRef.current?.send(JSON.stringify({
      action: "generate",
      params: {
        ...params,
        algorithm: algo.toLowerCase(),
        mode,
      },
    }))
    setChartData([])
    setRunning(false)
  }, [activeTask, algo, endpoint, params])

  const start = useCallback(() => {
    if (!endpoint) return
    const mode = activeTask === "Trail" ? "trail" : activeTask === "Planting" ? "reforestation" : "patrol"
    wsRef.current?.send(JSON.stringify({
      action: "start",
      params: {
        ...params,
        algorithm: algo.toLowerCase(),
        mode,
      },
    }))
    setChartData([])
    setRunning(true)
  }, [activeTask, algo, endpoint, params])

  const stop = useCallback(() => {
    wsRef.current?.send(JSON.stringify({ action: "stop" }))
    setRunning(false)
  }, [])

  const reset = useCallback(() => {
    wsRef.current?.send(JSON.stringify({ action: "reset" }))
    setRunning(false)
  }, [])

  const Slider = ({ label, param, min, max, step }) => (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, marginBottom: 4 }}>
        <span style={{ color: Theme.textSecond }}>{label}</span>
        <span style={{ color: Theme.textPrimary, fontWeight: 600, fontFamily: Theme.mono, fontSize: 11 }}>{params[param]}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={params[param]}
        onChange={e => set(param, Number(e.target.value))}
        disabled={running}
        style={{ width: "100%", accentColor: Theme.accent, cursor: running ? "not-allowed" : "pointer" }}
      />
    </div>
  )

  const TABS = ["Algorithm", "Map", "Robot"]
  const isPlanting = activeTask === "Planting"
  const scenarioReady = Boolean(state?.scenario_generated && state?.run_id)
  const executionPhase = state?.execution_phase ?? (running ? "running" : scenarioReady ? "preview" : "idle")
  const { statusLabel, bannerLabel } = describeExecutionPhase(
    executionPhase,
    scenarioReady,
    activeEnv,
    activeTask,
    algo,
    state?.run_id,
  )

  return (
    <div style={{ minHeight: "100vh", background: Theme.bg, fontFamily: "'Inter', 'Segoe UI', sans-serif" }}>
      <div
        style={{
          background: Theme.surface,
          borderBottom: `1px solid ${Theme.border}`,
          padding: "0 28px",
          height: 46,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          boxShadow: Theme.shadowSm,
        }}
      >
        <span style={{ fontSize: 14, fontWeight: 700, color: Theme.textPrimary }}>Forest RL</span>
        <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: Theme.textSecond }}>
          <Dot color={executionPhase === "running" ? Theme.green : executionPhase === "failed" ? Theme.red : Theme.border} />
          {bannerLabel}
        </div>
      </div>

      <div style={{ padding: "16px 28px" }}>
        <div style={{ display: "flex", gap: 14, maxWidth: 1320, margin: "0 auto", alignItems: "flex-start" }}>
          <div style={{ width: 230, flexShrink: 0, display: "flex", flexDirection: "column", gap: 10 }}>
            <div style={{ ...card, padding: 14 }}>
              <div style={secLabel}>Configuration</div>
              <Label>Environment</Label>
              <select
                value={activeEnv}
                disabled={running}
                style={{ ...selStyle, marginBottom: 10 }}
                onChange={e => {
                  const nextEnv = e.target.value
                  setActiveEnv(nextEnv)
                  if (!TASKS_BY_ENV[nextEnv].includes(activeTask)) setActiveTask(TASKS_BY_ENV[nextEnv][0])
                }}
              >
                {Object.keys(TASKS_BY_ENV).map(name => <option key={name}>{name}</option>)}
              </select>
              <Label>Task</Label>
              <select
                value={activeTask}
                onChange={e => setActiveTask(e.target.value)}
                disabled={running}
                style={selStyle}
              >
                {TASKS_BY_ENV[activeEnv].map(name => <option key={name}>{name}</option>)}
              </select>
            </div>

            <div style={{ ...card, overflow: "hidden" }}>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr 1fr",
                  background: "#f8fafc",
                  borderBottom: `1px solid ${Theme.border}`,
                }}
              >
                {TABS.map(name => (
                  <button
                    key={name}
                    onClick={() => setTab(name)}
                    style={{
                      padding: "8px 2px",
                      fontSize: 11,
                      fontWeight: tab === name ? 600 : 400,
                      color: tab === name ? Theme.accent : Theme.textMuted,
                      background: tab === name ? Theme.surface : "transparent",
                      border: "none",
                      borderBottom: tab === name ? `2px solid ${Theme.accent}` : "2px solid transparent",
                      cursor: "pointer",
                    }}
                  >
                    {name}
                  </button>
                ))}
              </div>

              <div style={{ padding: 14 }}>
                {tab === "Algorithm" && (
                  <>
                    <Label>Algorithm</Label>
                    <select
                      value={algo}
                      onChange={e => setAlgo(e.target.value)}
                      disabled={running}
                      style={{ ...selStyle, marginBottom: 14 }}
                    >
                      <option>PPO</option>
                      <option>A2C</option>
                      {!isPlanting && <option>SAC</option>}
                      {!isPlanting && <option>TD3</option>}
                    </select>
                    <Slider label="Learning rate" param="learning_rate" min={0.00001} max={0.01} step={0.00001} />
                    <Slider label="Gamma" param="gamma" min={0.9} max={0.999} step={0.001} />
                    <Slider label="Max steps" param="max_steps" min={50} max={1000} step={10} />
                    {!isPlanting && (algo === "SAC" || algo === "TD3") && (
                      <Slider label="Tau" param="tau" min={0.001} max={0.1} step={0.001} />
                    )}
                    {isPlanting && (
                      <>
                        <div style={{ borderTop: `1px solid ${Theme.border}`, margin: "12px 0" }} />
                        <Slider label="Plant reward" param="alpha_plant" min={0.5} max={10} step={0.1} />
                        <Slider label="Quality weight" param="alpha_quality" min={0} max={5} step={0.1} />
                        <Slider label="Move penalty" param="beta_move" min={0} max={1} step={0.01} />
                        <Slider label="Turn penalty" param="beta_turn" min={0} max={1} step={0.01} />
                        <Slider label="Invalid plant penalty" param="beta_invalid_plant" min={0} max={2} step={0.01} />
                      </>
                    )}
                  </>
                )}

                {tab === "Map" && (
                  <>
                    <Slider label="Grid size" param="grid_size" min={5} max={20} step={1} />
                    <Slider label="Obstacle density" param="obstacle_density" min={0} max={0.4} step={0.01} />
                    {isPlanting && (
                      <>
                        <Slider label="Plantable density" param="plantable_density" min={0.1} max={1} step={0.01} />
                        <Slider label="Min plant distance" param="min_plant_distance" min={0} max={3} step={1} />
                        <Slider label="Uniformity radius" param="uniformity_radius" min={0} max={3} step={1} />
                        <Slider label="Target density" param="target_density" min={0.05} max={0.8} step={0.01} />
                        <Slider label="Uniformity penalty" param="lambda_uniformity" min={0} max={10} step={0.1} />
                        <Slider label="Underplant penalty" param="lambda_underplanting" min={0} max={10} step={0.1} />
                      </>
                    )}
                  </>
                )}

                {tab === "Robot" && (
                  <>
                    {isPlanting ? (
                      <>
                        <Slider label="Seedlings on board" param="initial_seedlings" min={5} max={80} step={1} />
                        <Slider label="Stay penalty" param="beta_stay" min={0} max={1} step={0.01} />
                        <Slider label="Failed move penalty" param="beta_fail_move" min={0} max={2} step={0.01} />
                      </>
                    ) : (
                      <>
                        <Slider label="Action scale" param="action_scale" min={0.1} max={5} step={0.1} />
                        <Slider label="Max speed" param="max_speed" min={1} max={200} step={1} />
                        <Slider label="Acceleration" param="accel" min={1} max={100} step={1} />
                        <Slider label="Damping" param="damping" min={0.01} max={0.99} step={0.01} />
                        <Slider label="Physics dt" param="dt" min={0.001} max={0.05} step={0.001} />
                      </>
                    )}
                  </>
                )}
              </div>
            </div>
          </div>

          <div style={{ width: 560, flexShrink: 0, display: "flex", flexDirection: "column", gap: 10 }}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 6 }}>
              {METRICS.map(([label, getter, color]) => (
                <div key={label} style={{ ...card, padding: "8px 6px", textAlign: "center" }}>
                  <div
                    style={{
                      fontSize: 9,
                      color: Theme.textMuted,
                      fontWeight: 700,
                      letterSpacing: "0.07em",
                      textTransform: "uppercase",
                      marginBottom: 4,
                    }}
                  >
                    {label}
                  </div>
                  <div style={{ fontSize: 17, fontWeight: 700, color: color ?? Theme.textPrimary, fontFamily: Theme.mono }}>
                    {getter(state)}
                  </div>
                </div>
              ))}
            </div>

            <div style={{ ...card, padding: 14 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                <span style={{ fontSize: 11, fontWeight: 700, color: Theme.textPrimary }}>{activeEnv} - {activeTask}</span>
                <div style={{ display: "flex", gap: 10, fontSize: 10, color: Theme.textSecond }}>
                  {LEGEND.map(([color, text]) => (
                    <span key={text} style={{ display: "flex", alignItems: "center", gap: 3 }}>
                      <Dot color={color} size={6} />
                      {text}
                    </span>
                  ))}
                </div>
              </div>
              <div style={{ display: "flex", justifyContent: "center" }}>
                <canvas
                  ref={canvasRef}
                  width={CANVAS_SIZE}
                  height={CANVAS_SIZE}
                  style={{ display: "block", borderRadius: Theme.radiusSm, border: `1px solid ${Theme.border}` }}
                />
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
              <Btn onClick={generate} disabled={running || !endpoint} color={Theme.accent}>Generate</Btn>
              <Btn onClick={start} disabled={running || !endpoint || !scenarioReady} color={Theme.green}>Start</Btn>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
              <Btn onClick={stop} disabled={!running} color={Theme.red}>Stop</Btn>
              <Btn onClick={reset} disabled={running || !scenarioReady} color={Theme.textMuted}>Reset</Btn>
            </div>
          </div>

          <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", gap: 10 }}>
            <div style={{ ...card, padding: 16 }}>
              <div style={secLabel}>Reward Dynamics</div>
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 24 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f2f5" />
                  <XAxis
                    dataKey="i"
                    tick={{ fontSize: 10, fill: Theme.textMuted }}
                    label={{ value: "Episode", position: "insideBottom", offset: -10, fontSize: 10, fill: Theme.textSecond }}
                  />
                  <YAxis
                    width={40}
                    tick={{ fontSize: 10, fill: Theme.textMuted }}
                    label={{ value: "Reward", angle: -90, position: "insideLeft", fontSize: 10, fill: Theme.textSecond }}
                  />
                  <Tooltip
                    contentStyle={{
                      fontSize: 11,
                      borderRadius: Theme.radiusSm,
                      border: `1px solid ${Theme.border}`,
                      boxShadow: Theme.shadow,
                      background: Theme.surface,
                    }}
                    labelStyle={{ color: Theme.textSecond }}
                  />
                  <Line type="monotone" dataKey="r" stroke={Theme.accent} dot={false} strokeWidth={1.5} name="Reward" />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div style={{ ...card, padding: 16 }}>
              <div style={secLabel}>Live State</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, fontSize: 12, color: Theme.textSecond }}>
                <div>Run ID: <strong style={{ color: Theme.textPrimary }}>{state?.run_id ?? "-"}</strong></div>
                <div>Scenario version: <strong style={{ color: Theme.textPrimary }}>{state?.scenario_version_id ?? "-"}</strong></div>
                <div>Coverage: <strong style={{ color: Theme.textPrimary }}>{state?.coverage_ratio != null ? state.coverage_ratio.toFixed(2) : "0.00"}</strong></div>
                <div>Seedlings left: <strong style={{ color: Theme.textPrimary }}>{state?.remaining_seedlings ?? 0}</strong></div>
                <div>Invalid plants: <strong style={{ color: Theme.textPrimary }}>{state?.invalid_plant_count ?? 0}</strong></div>
                <div>Endpoint: <strong style={{ color: Theme.textPrimary }}>{endpoint ?? "Unavailable"}</strong></div>
                <div>Scenario ready: <strong style={{ color: Theme.textPrimary }}>{scenarioReady ? "yes" : "no"}</strong></div>
                <div>Validation: <strong style={{ color: Theme.textPrimary }}>{state?.validation_passed == null ? "n/a" : state.validation_passed ? "ok" : "failed"}</strong></div>
                <div>Status: <strong style={{ color: Theme.textPrimary }}>{statusLabel}</strong></div>
                {state?.error && (
                  <div style={{ gridColumn: "1 / -1" }}>
                    Error: <strong style={{ color: Theme.red }}>{state.error}</strong>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

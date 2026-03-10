import { useState, useEffect, useRef, useCallback } from "react"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts"
import { Theme, card, secLabel, selStyle } from "./constants/colors"

const TASKS_BY_ENV = {
  "Непрерывная двумерная": ["Патруль", "Тропы"],
  "Трёхмерная": ["Патруль", "Тропы"],
  "Дискретная": ["Патруль", "Тропы"],
}

const WS_MAP = {
  "Непрерывная двумерная/Патруль": "ws://127.0.0.1:8000/continuous/patrol",
  "Непрерывная двумерная/Тропы": "ws://127.0.0.1:8000/continuous/trail",
  "Трёхмерная/Патруль": "ws://127.0.0.1:8000/threed/patrol",
  "Трёхмерная/Тропы": "ws://127.0.0.1:8000/threed/trail",
  "Дискретная/Патруль": "ws://127.0.0.1:8000/discrete/patrol",
  "Дискретная/Тропы": "ws://127.0.0.1:8000/discrete/trail",
}

const CANVAS_SIZE = 360
const CENTER_WIDTH = CANVAS_SIZE + 120

const Label = ({ children }) =>
  <div style={{ fontSize: 11, color: Theme.textSecond, marginBottom: 4 }}>{children}</div>

const Dot = ({ color, size = 7 }) =>
  <span style={{ display: "inline-block", width: size, height: size, borderRadius: "50%", background: color, flexShrink: 0 }} />

const Btn = ({ onClick, disabled, color, children }) => (
  <button onClick={onClick} disabled={disabled} style={{
    padding: "10px",
    background: disabled ? Theme.textMuted : color,
    color: "white",
    border: "none",
    borderRadius: Theme.radiusSm,
    cursor: disabled ? "not-allowed" : "pointer",
    fontWeight: 700,
    fontSize: 13,
    boxShadow: disabled ? "none" : `0 1px 3px ${color}55`,
  }}>{children}</button>
)

// Метрики для панели
const METRICS = [
  ["Эпизод", s => s?.episode ?? 0, null],
  ["Шаг", s => s?.step ?? 0, null],
  ["Награда", s => s?.total_reward != null ? s.total_reward.toFixed(1) : "0", null],
  ["Целей", s => s?.goal_count ?? 0, Theme.green],
  ["Столкн.", s => s?.collision_count ?? 0, Theme.red],
]

const LEGEND = [
  [Theme.accent, "Агент"],
  [Theme.green, "Цель"],
  [Theme.textMuted, "Препятствие"],
  [Theme.red, "Столкновение"],
]

function drawCanvas(canvas, state, gridSize = 10, gridCache = null, terrain = null) {
  const ctx = canvas.getContext("2d")
  const size = CANVAS_SIZE
  const half = gridSize * 0.2 + 0.15
  const range = half * 2
  const pu = size / range
  const tc = ([x, y]) => [(x + half) / range * size, (half - y) / range * size]

  // Фон и сетка
  ctx.clearRect(0, 0, size, size)
  if (gridCache) ctx.drawImage(gridCache, 0, 0)
  else { ctx.fillStyle = "#fafafa"; ctx.fillRect(0, 0, size, size) }

  // Рельеф
  if (terrain) {
    const rows = terrain.length
    const cols = terrain[0].length
    const cw = size / cols
    const ch = size / rows
    for (let iy = 0; iy < rows; iy++) {
      for (let ix = 0; ix < cols; ix++) {
        const val = terrain[iy][ix]
        if (val > 0.5) {
          const a = ((val - 0.5) / 0.5 * 0.45).toFixed(3)
          ctx.fillStyle = `rgba(156,163,175,${a})`
          ctx.fillRect(ix * cw, iy * ch, cw, ch)
        }
      }
    }
  }

  if (!state) return

  // Траектория
  const traj = state.trajectory ?? []
  if (traj.length > 1) {
    ctx.beginPath()
    ctx.strokeStyle = "rgba(37,99,235,0.2)"
    ctx.lineWidth = 1.5
    const [x0, y0] = tc(traj[0])
    ctx.moveTo(x0, y0)
    traj.forEach(p => { const [cx, cy] = tc(p); ctx.lineTo(cx, cy) })
    ctx.stroke()
  }

  // Объекты
  const dot = (positions, color, r) => positions?.forEach(p => {
    const [cx, cy] = tc(p)
    ctx.fillStyle = color
    ctx.beginPath()
    ctx.arc(cx, cy, pu * r, 0, Math.PI * 2)
    ctx.fill()
  })

  dot(state.landmark_pos, "#9ca3af", 0.1)
  dot(state.goal_pos, Theme.green, 0.18)
  dot(state.agent_pos, state.is_collision ? Theme.red : Theme.accent, 0.14)
}

export default function App() {
  const [activeEnv, setActiveEnv] = useState("Непрерывная двумерная")
  const [activeTask, setActiveTask] = useState("Тропы")
  const [algo, setAlgo] = useState("PPO")
  const [state, setState] = useState(null)
  const [chartData, setChartData] = useState([])
  const [running, setRunning] = useState(false)
  const [tab, setTab] = useState("Алгоритм")
  const canvasRef = useRef(null)
  const wsRef = useRef(null)
  const gridCacheRef = useRef(null)
  const [terrain, setTerrain] = useState(null)
  const [activeGridSize, setActiveGridSize] = useState(10)

  const [params, setParams] = useState({
    lr: 0.0003, gamma: 0.99, tau: 0.005,
    obstacle_density: 0.05, grid_size: 15, max_steps: 500,
    goal_reward: 50.0, collision_penalty: 0.3, step_penalty: 0.0, action_scale: 1.0,
    max_speed: 50.0, accel: 40.0, damping: 0.6, dt: 0.01, terrain_penalty: 0.03,
  })
  const set = (k, v) => setParams(p => ({ ...p, [k]: v }))

  // WebSocket
  useEffect(() => {
    if (running) { wsRef.current?.send(JSON.stringify({ action: "stop" })); setRunning(false) }
    setState(null)
    setChartData([])
    wsRef.current?.close()

    const ws = new WebSocket(WS_MAP[`${activeEnv}/${activeTask}`])
    wsRef.current = ws

    ws.onmessage = (e) => {
      const data = JSON.parse(e.data)

      // Обновление состояния и траектории
      setState(prev => {
        if (data.new_episode && prev?.trajectory?.length > 0) {
          return { ...data, trajectory: prev.trajectory, agent_pos: prev.agent_pos }
        }
        return data
      })

      // Обновление рельефа
      if (data.terrain_map) setTerrain(data.terrain_map)

      // Обновление графика награды
      if (data.new_episode) {
        setChartData(prev => {
          const episodeNum = data.episode - 1
          if (prev.length > 0 && prev[prev.length - 1].i === episodeNum) return prev
          return [...prev.slice(-99), { i: episodeNum, r: data.last_episode_reward }]
        })
      }
    }
    ws.onerror = (e) => console.error("ws error", e)

    return () => ws.close()
  }, [activeEnv, activeTask])

  const start = useCallback(() => {
    wsRef.current?.send(JSON.stringify({ action: "start", algo, params }))
    setActiveGridSize(params.grid_size)
    setChartData([])
    setRunning(true)
  }, [algo, params])

  const stop = useCallback(() => {
    wsRef.current?.send(JSON.stringify({ action: "stop" }))
    setRunning(false)
    setChartData([])
    setTerrain(null)
  }, [])

  // Кэширование сетки 
  useEffect(() => {
    const offscreen = document.createElement("canvas")
    offscreen.width = CANVAS_SIZE
    offscreen.height = CANVAS_SIZE
    const ctx = offscreen.getContext("2d")
    ctx.fillStyle = "#fafafa"
    ctx.fillRect(0, 0, CANVAS_SIZE, CANVAS_SIZE)
    ctx.strokeStyle = "#e5e7eb"
    ctx.lineWidth = 0.5
    for (let i = 0; i <= activeGridSize; i++) {
      const v = i * CANVAS_SIZE / activeGridSize
      ctx.beginPath(); ctx.moveTo(v, 0); ctx.lineTo(v, CANVAS_SIZE); ctx.stroke()
      ctx.beginPath(); ctx.moveTo(0, v); ctx.lineTo(CANVAS_SIZE, v); ctx.stroke()
    }
    gridCacheRef.current = offscreen
  }, [activeGridSize])

  // Отрисовка канваса при изменении состояния 
  useEffect(() => {
    if (canvasRef.current) drawCanvas(canvasRef.current, state, activeGridSize, gridCacheRef.current, terrain)
  }, [state, activeGridSize, terrain])

  // Ползунки параметров 
  const Slider = ({ label, param, min, max, step }) => (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, marginBottom: 4 }}>
        <span style={{ color: Theme.textSecond }}>{label}</span>
        <span style={{ color: Theme.textPrimary, fontWeight: 600, fontFamily: Theme.mono, fontSize: 11 }}>{params[param]}</span>
      </div>
      <input type="range" min={min} max={max} step={step} value={params[param]}
        onChange={e => set(param, +e.target.value)} disabled={running}
        style={{ width: "100%", accentColor: Theme.accent, cursor: running ? "not-allowed" : "pointer" }} />
    </div>
  )

  const TABS = ["Алгоритм", "Карта", "Робот"]

  return (
    <div style={{ minHeight: "100vh", background: Theme.bg, fontFamily: "'Inter', 'Segoe UI', sans-serif" }}>
      {/* Шапка с состоянием */}
      <div style={{ background: Theme.surface, borderBottom: `1px solid ${Theme.border}`, padding: "0 28px", height: 46, display: "flex", alignItems: "center", justifyContent: "space-between", boxShadow: Theme.shadowSm }}>
        <span style={{ fontSize: 14, fontWeight: 700, color: Theme.textPrimary }}>Forest RL</span>
        <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: Theme.textSecond }}>
          <Dot color={running ? Theme.green : Theme.border} />
          {running ? `Обучение · ${activeEnv} / ${activeTask} · ${algo}` : "Ожидание запуска"}
        </div>
      </div>

      <div style={{ padding: "16px 28px" }}>
        <div style={{ display: "flex", gap: 14, maxWidth: 1280, margin: "0 auto", alignItems: "flex-start" }}>
          
          <div style={{ width: 210, flexShrink: 0, display: "flex", flexDirection: "column", gap: 10 }}>
            {/* Конфигурация среды и задачи */}
            <div style={{ ...card, padding: 14 }}>
              <div style={secLabel}>Конфигурация</div>
              <Label>Среда</Label>
              <select value={activeEnv} disabled={running} style={{ ...selStyle, marginBottom: 10 }}
                onChange={e => {
                  setActiveEnv(e.target.value)
                  if (!TASKS_BY_ENV[e.target.value].includes(activeTask))
                    setActiveTask(TASKS_BY_ENV[e.target.value][0])
                }}>
                {Object.keys(TASKS_BY_ENV).map(e => <option key={e}>{e}</option>)}
              </select>
              <Label>Задача</Label>
              <select value={activeTask} onChange={e => setActiveTask(e.target.value)} disabled={running} style={selStyle}>
                {TASKS_BY_ENV[activeEnv].map(t => <option key={t}>{t}</option>)}
              </select>
            </div>

            {/* Панель параметров алгоритма */}
            <div style={{ ...card, overflow: "hidden" }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", background: "#f8fafc", borderBottom: `1px solid ${Theme.border}` }}>
                {TABS.map(t => (
                  <button key={t} onClick={() => setTab(t)} style={{
                    padding: "8px 2px",
                    fontSize: 11,
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
                {tab === "Алгоритм" && <>
                  {/* Параметры алгоритма */}
                  <Label>Алгоритм</Label>
                  <select value={algo} onChange={e => setAlgo(e.target.value)} disabled={running} style={{ ...selStyle, marginBottom: 14 }}>
                    <option>PPO</option><option>SAC</option><option>TD3</option>
                  </select>
                  <Slider label="Скор. обуч." param="lr" min={0.00001} max={0.01} step={0.00001} />
                  <Slider label="Гамма (γ)" param="gamma" min={0.9} max={0.999} step={0.001} />
                  <Slider label="Шагов в эпизоде" param="max_steps" min={50} max={5000} step={50} />
                  {(algo === "SAC" || algo === "TD3") && <Slider label="Тау" param="tau" min={0.001} max={0.1} step={0.001} />}
                  <div style={{ borderTop: `1px solid ${Theme.border}`, margin: "12px 0" }} />
                  <Slider label="Награда за цель" param="goal_reward" min={10} max={100} step={5} />
                  <Slider label="Штраф столкн." param="collision_penalty" min={0} max={5} step={0.1} />
                  <Slider label="Штраф за шаг" param="step_penalty" min={0} max={1} step={0.01} />
                </>}

                {tab === "Карта" && <>
                  {/* Параметры карты */}
                  <Slider label="Размер" param="grid_size" min={5} max={20} step={1} />
                  <Slider label="Препятствия" param="obstacle_density" min={0} max={0.4} step={0.01} />
                </>}

                {tab === "Робот" && <>
                  {/* Параметры агента / физики */}
                  <Slider label="Масштаб" param="action_scale" min={0.1} max={5} step={0.1} />
                  <Slider label="Макс. скор." param="max_speed" min={1} max={200} step={1} />
                  <Slider label="Разгон" param="accel" min={1} max={100} step={1} />
                  <Slider label="Торможение" param="damping" min={0.01} max={0.99} step={0.01} />
                  <Slider label="Шаг физики" param="dt" min={0.001} max={0.05} step={0.001} />
                </>}
              </div>
            </div>
          </div>

          {/* Панель состояния и канвас */}
          <div style={{ flexShrink: 0, display: "flex", flexDirection: "column", gap: 10, width: CENTER_WIDTH }}>
            {/* Метрики */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 6 }}>
              {METRICS.map(([label, val, color]) => (
                <div key={label} style={{ ...card, padding: "8px 6px", textAlign: "center" }}>
                  <div style={{ fontSize: 9, color: Theme.textMuted, fontWeight: 700, letterSpacing: "0.07em", textTransform: "uppercase", marginBottom: 4 }}>{label}</div>
                  <div style={{ fontSize: 17, fontWeight: 700, color: color ?? Theme.textPrimary, fontFamily: Theme.mono }}>{val(state)}</div>
                </div>
              ))}
            </div>

            {/* Канвас */}
            <div style={{ ...card, padding: 14, flex: 1, display: "flex", flexDirection: "column" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                <span style={{ fontSize: 11, fontWeight: 700, color: Theme.textPrimary }}>{activeEnv} · {activeTask}</span>
                <div style={{ display: "flex", gap: 10, fontSize: 10, color: Theme.textSecond }}>
                  {LEGEND.map(([c, l]) => (
                    <span key={l} style={{ display: "flex", alignItems: "center", gap: 3 }}>
                      <Dot color={c} size={6} />{l}
                    </span>
                  ))}
                </div>
              </div>
              <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
                <canvas ref={canvasRef} width={CANVAS_SIZE} height={CANVAS_SIZE}
                  style={{ display: "block", borderRadius: Theme.radiusSm, border: `1px solid ${Theme.border}` }} />
              </div>
            </div>

            {/* Кнопки управления */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
              <Btn onClick={start} disabled={running} color={Theme.green}>Старт</Btn>
              <Btn onClick={stop} disabled={!running} color={Theme.red}>Стоп</Btn>
            </div>
          </div>

          {/* График динамики награды */}
          <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", maxHeight: 300 }}>
            <div style={{ ...card, padding: 16, flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
              <div style={secLabel}>Динамика вознаграждения</div>
              <ResponsiveContainer width="100%" height={210}>
                <LineChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 24 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f2f5" />
                  <XAxis dataKey="i"
                    tick={{ fontSize: 10, fill: Theme.textMuted }}
                    label={{ value: "Эпизод", position: "insideBottom", offset: -10, fontSize: 10, fill: Theme.textSecond }}
                  />
                  <YAxis width={40}
                    tick={{ fontSize: 10, fill: Theme.textMuted }}
                    label={{ value: "Награда", angle: -90, position: "insideLeft", fontSize: 10, fill: Theme.textSecond }}
                  />
                  <Tooltip
                    contentStyle={{ fontSize: 11, borderRadius: Theme.radiusSm, border: `1px solid ${Theme.border}`, boxShadow: Theme.shadow, background: Theme.surface }}
                    labelStyle={{ color: Theme.textSecond }}
                  />
                  <Line type="monotone" dataKey="r" stroke={Theme.accent} dot={false} strokeWidth={1.5} name="Награда" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

        </div>
      </div>
    </div>
  )
}
import { Theme, card } from "../constants/colors"
import { getMetrics } from "../constants/config"

const CANVAS_SIZE = 360

const Dot = ({ color, size = 6 }) =>
  <span style={{ display: "inline-block", width: size, height: size, borderRadius: "50%", background: color, flexShrink: 0 }} />

const LEGEND_BY_ENV = {
  "Непрерывная 2D": [
    [Theme.accent,    "Агент"],
    [Theme.green,     "Цель"],
    [Theme.textMuted, "Препятствие"],
    [Theme.red,       "Столкновение"],
  ],
  "Дискретная": [
    [Theme.accent,    "Агент"],
    [Theme.green,     "Засаживаемые"],
    ["#16a34a",       "Посажено"],
    [Theme.textMuted, "Препятствие"],
    [Theme.red,       "Столкновение"],
  ],
  "Трёхмерная": [
    [Theme.accent,    "Агент"],
    [Theme.green,     "Цель"],
    [Theme.textMuted, "Препятствие"],
    [Theme.red,       "Столкновение"],
  ],
}

export function CanvasPanel({ activeEnv, activeTask, state, canvasRef }) {
  const metrics = getMetrics(activeEnv, activeTask)
  const legend  = LEGEND_BY_ENV[activeEnv] ?? LEGEND_BY_ENV["Непрерывная 2D"]

  return (
    <div style={{ width: CANVAS_SIZE + 120, flexShrink: 0, display: "flex", flexDirection: "column", gap: 10 }}>

      {/* Метрики */}
      <div style={{ display: "grid", gridTemplateColumns: `repeat(${metrics.length}, 1fr)`, gap: 6 }}>
        {metrics.map(([label, getter, color]) => (
          <div key={label} style={{ ...card, padding: "8px 6px", textAlign: "center" }}>
            <div style={{ fontSize: 9, color: Theme.textMuted, fontWeight: 700, letterSpacing: "0.07em", textTransform: "uppercase", marginBottom: 4 }}>
              {label}
            </div>
            <div style={{ fontSize: 17, fontWeight: 700, color: color ?? Theme.textPrimary, fontFamily: Theme.mono }}>
              {getter(state)}
            </div>
          </div>
        ))}
      </div>

      {/* Канвас */}
      <div style={{ ...card, padding: 14 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: Theme.textPrimary }}>
            {activeEnv} · {activeTask}
          </span>
          <div style={{ display: "flex", gap: 10, fontSize: 10, color: Theme.textSecond }}>
            {legend.map(([c, l]) => (
              <span key={l} style={{ display: "flex", alignItems: "center", gap: 3 }}>
                <Dot color={c} />{l}
              </span>
            ))}
          </div>
        </div>
        <div style={{ display: "flex", justifyContent: "center" }}>
          <canvas ref={canvasRef} width={CANVAS_SIZE} height={CANVAS_SIZE}
            style={{ display: "block", borderRadius: Theme.radiusSm, border: `1px solid ${Theme.border}` }} />
        </div>
      </div>
    </div>
  )
}
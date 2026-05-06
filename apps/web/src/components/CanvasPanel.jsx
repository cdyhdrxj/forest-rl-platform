import { Theme, card } from "../constants/colors"
import { getMetrics } from "../constants/config"
import { PATROL_LEGEND } from "../constants/patrol"
import WebRTCPlayer from "./WebRTCPlayer"

const CANVAS_SIZE = 360

const Dot = ({ color, size = 6 }) => (
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

const LEGEND_BY_TASK = {
  "Тропы": [
    [Theme.accent,    "Агент"],
    [Theme.green,     "Цель"],
    [Theme.textMuted, "Препятствие"],
    [Theme.red,       "Столкновение"],
  ],
  "Посадка": [
    [Theme.accent,    "Агент"],
    [Theme.green,     "Засаживаемые"],
    ["#16a34a",       "Посажено"],
    [Theme.textMuted, "Препятствие"],
    [Theme.red,       "Столкновение"],
  ],
  "Патруль": PATROL_LEGEND,
}

const IS_3D     = (activeEnv)  => activeEnv  === "3D симулятор"
const IS_PATROL = (activeTask) => activeTask === "Патруль"

function getLegend(activeTask) {
  return LEGEND_BY_TASK[activeTask] ?? LEGEND_BY_TASK["Тропы"]
}

function getCanvasTitle(activeEnv, activeTask) {
  if (IS_PATROL(activeTask)) return activeTask
  return `${activeEnv} · ${activeTask}`
}

export function CanvasPanel({
  activeEnv, activeTask, state, canvasRef,
  showTrail, setShowTrail,
  showObs,   setShowObs,
}) {
  const metrics  = getMetrics(activeEnv, activeTask)
  const legend   = getLegend(activeTask)
  const is3d     = IS_3D(activeEnv)
  const isPatrol = IS_PATROL(activeTask)

  const MAX_METRICS_PER_ROW = 8
  const firstRowMetrics = metrics.slice(0, MAX_METRICS_PER_ROW)
  const secondRowMetrics = metrics.slice(MAX_METRICS_PER_ROW)

  const MetricsRow = ({ metricsList }) => (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: `repeat(${metricsList.length}, 1fr)`,
        gap: 6,
      }}
    >
      {metricsList.map(([label, getter, color]) => (
        <div
          key={label}
          style={{ ...card, padding: "8px 10px", textAlign: "center" }}
        >
          <div style={{ fontSize: 9, color: Theme.textMuted, fontWeight: 700, letterSpacing: "0.07em", textTransform: "uppercase", marginBottom: 4 }}>
            {label}
          </div>
          <div style={{ fontSize: 17, fontWeight: 700, color: color ?? Theme.textPrimary, fontFamily: Theme.mono }}>
            {getter(state)}
          </div>
        </div>
      ))}
    </div>
  )

  if (is3d) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 10, minWidth: 0 }}>
        <WebRTCPlayer />
      </div>
    )
  }

  return (
    <div style={{ 
      width: "100%",
      minWidth: CANVAS_SIZE + 120,
      maxWidth: "100%",
      flexShrink: 0, 
      display: "flex", 
      flexDirection: "column", 
      gap: 10 
    }}>
      {/* Метрики в несколько строк */}
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {firstRowMetrics.length > 0 && <MetricsRow metricsList={firstRowMetrics} />}
        {secondRowMetrics.length > 0 && <MetricsRow metricsList={secondRowMetrics} />}
      </div>

      <div style={{ ...card, padding: 14 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10, flexWrap: "wrap", gap: 8 }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: Theme.textPrimary }}>
            {getCanvasTitle(activeEnv, activeTask)}
          </span>

          <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
            <div style={{ display: "flex", gap: 10, fontSize: 10, color: Theme.textSecond, flexWrap: "wrap" }}>
              {legend.map(([c, l]) => (
                <span key={l} style={{ display: "flex", alignItems: "center", gap: 3 }}>
                  <Dot color={c} />
                  {l}
                </span>
              ))}
            </div>

            {isPatrol && setShowTrail && (
              <button
                onClick={() => setShowTrail(v => !v)}
                title={showTrail ? "Скрыть трейл" : "Показать трейл"}
                style={{
                  display: "flex", alignItems: "center", gap: 4,
                  padding: "3px 8px", fontSize: 10, fontWeight: 600,
                  color:      showTrail ? Theme.accent        : Theme.textMuted,
                  background: showTrail ? `${Theme.accent}18` : "transparent",
                  border:     `1px solid ${showTrail ? Theme.accent : Theme.border}`,
                  borderRadius: 5, cursor: "pointer", whiteSpace: "nowrap",
                }}
              >
                ≈ Трейл
              </button>
            )}

            {isPatrol && setShowObs && (
              <button
                onClick={() => setShowObs(v => !v)}
                title={showObs ? "Скрыть зону видимости" : "Показать зону видимости"}
                style={{
                  display: "flex", alignItems: "center", gap: 4,
                  padding: "3px 8px", fontSize: 10, fontWeight: 600,
                  color:      showObs ? "#b45309"               : Theme.textMuted,
                  background: showObs ? "rgba(250,204,21,0.15)" : "transparent",
                  border:     `1px solid ${showObs ? "#d97706" : Theme.border}`,
                  borderRadius: 5, cursor: "pointer", whiteSpace: "nowrap",
                }}
              >
                ◻ Обзор
              </button>
            )}
          </div>
        </div>

        <div style={{ display: "flex", justifyContent: "center" }}>
          <canvas
            ref={canvasRef}
            width={CANVAS_SIZE}
            height={CANVAS_SIZE}
            style={{ 
              display: "block", 
              borderRadius: Theme.radiusSm, 
              border: `1px solid ${Theme.border}`,
              width: "100%",
              maxWidth: CANVAS_SIZE,
              height: "auto"
            }}
          />
        </div>
      </div>
    </div>
  )
}
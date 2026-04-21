import { Theme, card } from "../constants/colors"
import { getMetrics } from "../constants/config"
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

const LEGEND_BY_ENV = {
  "Непрерывная 2D": [
    [Theme.accent, "Агент"],
    [Theme.green, "Цель"],
    [Theme.textMuted, "Препятствие"],
    [Theme.red, "Столкновение"],
  ],
  "Дискретная": [
    [Theme.accent, "Агент"],
    [Theme.green, "Засаживаемые"],
    ["#16a34a", "Посажено"],
    [Theme.textMuted, "Препятствие"],
    [Theme.red, "Столкновение"],
  ],
  "3D симулятор": [
    [Theme.accent, "Агент"],
    [Theme.green, "Цель"],
    [Theme.textMuted, "Препятствие"],
    [Theme.red, "Столкновение"],
  ],
}

const PATROL_LEGEND = [
  [Theme.accent,          "Агент"],
  ["#dc2626",             "Нарушитель"],
  ["rgba(22,163,74,0.88)","Ценная зона"],
  ["rgba(75,85,99,0.82)", "Препятствие"],
]

const IS_3D = (activeEnv) => activeEnv === "3D симулятор"

export function CanvasPanel({ activeEnv, activeTask, state, canvasRef, showTrail, setShowTrail, showObs, setShowObs }) {
  const metrics = getMetrics(activeEnv, activeTask)
  const legend = (activeEnv === "Дискретная" && activeTask === "Патруль")
    ? PATROL_LEGEND
    : (LEGEND_BY_ENV[activeEnv] ?? LEGEND_BY_ENV["Непрерывная 2D"])
  const is3d = IS_3D(activeEnv)

  /* блок метрик */
  const Metrics = (
    <div
      style={{
        display: is3d ? "flex" : "grid",
        justifyContent: is3d ? "center" : undefined,
        gridTemplateColumns: !is3d
          ? `repeat(${metrics.length}, 1fr)`
          : undefined,
        gap: 6,
      }}
    >
      {metrics.map(([label, getter, color]) => (
        <div
          key={label}
          style={{
            ...card,
            padding: "8px 10px",
            textAlign: "center",
            minWidth: is3d ? 80 : undefined,
          }}
        >
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
          <div
            style={{
              fontSize: 17,
              fontWeight: 700,
              color: color ?? Theme.textPrimary,
              fontFamily: Theme.mono,
            }}
          >
            {getter(state)}
          </div>
        </div>
      ))}
    </div>
  )

  /* 3D режим  */
  if (is3d) {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 10,
          minWidth: 0,
        }}
      >
        <WebRTCPlayer />
      </div>
    )
  }

  /* дискретный режим */
  return (
    <div
      style={{
        width: CANVAS_SIZE + 120,
        flexShrink: 0,
        display: "flex",
        flexDirection: "column",
        gap: 10,
      }}
    >
      {Metrics}

      {/* Канвас */}
      <div style={{ ...card, padding: 14 }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 10,
          }}
        >
          <span
            style={{
              fontSize: 11,
              fontWeight: 700,
              color: Theme.textPrimary,
            }}
          >
            {activeEnv === "Дискретная" && activeTask === "Патруль" ? activeTask : `${activeEnv} · ${activeTask}`}
          </span>

          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div
              style={{
                display: "flex",
                gap: 10,
                fontSize: 10,
                color: Theme.textSecond,
              }}
            >
              {legend.map(([c, l]) => (
                <span
                  key={l}
                  style={{ display: "flex", alignItems: "center", gap: 3 }}
                >
                  <Dot color={c} />
                  {l}
                </span>
              ))}
            </div>

            {setShowTrail && (
              <button
                onClick={() => setShowTrail(v => !v)}
                title={showTrail ? "Скрыть трейл" : "Показать трейл"}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 4,
                  padding: "3px 8px",
                  fontSize: 10,
                  fontWeight: 600,
                  color: showTrail ? Theme.accent : Theme.textMuted,
                  background: showTrail ? `${Theme.accent}18` : "transparent",
                  border: `1px solid ${showTrail ? Theme.accent : Theme.border}`,
                  borderRadius: 5,
                  cursor: "pointer",
                  whiteSpace: "nowrap",
                }}
              >
                ≈ Трейл
              </button>
            )}

            {setShowObs && (
              <button
                onClick={() => setShowObs(v => !v)}
                title={showObs ? "Скрыть зону видимости" : "Показать зону видимости"}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 4,
                  padding: "3px 8px",
                  fontSize: 10,
                  fontWeight: 600,
                  color: showObs ? "#b45309" : Theme.textMuted,
                  background: showObs ? "rgba(250,204,21,0.15)" : "transparent",
                  border: `1px solid ${showObs ? "#d97706" : Theme.border}`,
                  borderRadius: 5,
                  cursor: "pointer",
                  whiteSpace: "nowrap",
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
            }}
          />
        </div>
      </div>
    </div>
  )
}
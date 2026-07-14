import { Theme } from "../constants/colors"
import { useState } from "react"

const BtnSolid = ({ onClick, disabled, color, children }) => (
  <button onClick={onClick} disabled={disabled} style={{
    padding: "10px",
    background: disabled ? Theme.textMuted : color,
    color: "white",
    border: "none",
    borderRadius: Theme.radiusSm,
    cursor: disabled ? "not-allowed" : "pointer",
    fontWeight: 600,
    fontSize: 13,
    transition: "opacity 0.1s",
    opacity: disabled ? 0.6 : 1,
  }}>{children}</button>
)

const BtnOutline = ({ onClick, disabled, color, children }) => (
  <button onClick={onClick} disabled={disabled} style={{
    padding: "10px",
    background: "transparent",
    color: disabled ? Theme.textMuted : color,
    border: `1px solid ${disabled ? Theme.border : color}`,
    borderRadius: Theme.radiusSm,
    cursor: disabled ? "not-allowed" : "pointer",
    fontWeight: 600,
    fontSize: 13,
    transition: "all 0.1s",
  }}>{children}</button>
)

export function ControlButtons({
  activeEnv, running, scenarioReady, endpoint,
  onGenerate, onStart, onStop, onReset, onFinish,
  isInference = false,
  onStartEval,
  evalReady = false,
}) {
  const [wasStopped, setWasStopped] = useState(false)

  const canGenerate = !running && !!endpoint

  let canStart
  if (isInference) {
    canStart = !running && evalReady && scenarioReady
  } else {
    canStart = !running && !!endpoint && scenarioReady
  }

  const resetDisabled = running || !scenarioReady

  const handleStop = () => {
    onStop()
    setWasStopped(true)
  }

  const handleStart = () => {
    if (isInference) {
      onStartEval({ resume: wasStopped })
    } else {
      onStart({ resume: wasStopped })
    }
    setWasStopped(false)
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
        <BtnSolid onClick={onGenerate} disabled={!canGenerate} color={Theme.accent}>
          Генерировать
        </BtnSolid>
        <BtnSolid onClick={handleStart} disabled={!canStart} color={Theme.green}>
          Старт
        </BtnSolid>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
        <BtnSolid onClick={handleStop} disabled={!running} color={Theme.red}>Стоп</BtnSolid>
        <BtnOutline onClick={onReset} disabled={resetDisabled} color={Theme.textSecond}>Сброс</BtnOutline>
        <BtnOutline onClick={onFinish} disabled={false} color={Theme.red}>Завершить</BtnOutline>
      </div>
    </div>
  )
}
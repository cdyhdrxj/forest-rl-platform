import { ENV } from "../constants/envs"
import { Theme } from "../constants/colors"

const Btn = ({ onClick, disabled, color, children }) => (
  <button onClick={onClick} disabled={disabled} style={{
    padding: "10px",
    background: disabled ? Theme.textMuted : color,
    color: "white", border: "none",
    borderRadius: Theme.radiusSm,
    cursor: disabled ? "not-allowed" : "pointer",
    fontWeight: 700, fontSize: 13,
    boxShadow: disabled ? "none" : `0 1px 3px ${color}55`,
  }}>{children}</button>
)

export function ControlButtons({
  activeEnv, running, scenarioReady, endpoint,
  onGenerate, onStart, onStop, onReset,
  isInference = false,
  onStartEval,          
  evalReady = false,    
}) {
  const isCamar = activeEnv === ENV.CONTINUOUS
  const canGenerate = !running && !!endpoint && !isCamar
  
  let canStart
  if (isCamar) {
    canStart = !running && !!endpoint
  } else if (isInference) {
    canStart = !running && evalReady && scenarioReady
  } else {
    canStart = !running && !!endpoint && scenarioReady
  }
  
  const startAction = isInference ? onStartEval : onStart
  const resetLabel = isCamar ? "Сброс карты" : "Сброс"
  const resetColor = isCamar ? Theme.accent : Theme.textMuted
  const generateDisabled = running || !endpoint || !canGenerate

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
        <Btn onClick={onGenerate} disabled={generateDisabled} color={Theme.accent}>
          Генерировать
        </Btn>
        <Btn onClick={startAction} disabled={!canStart} color={Theme.green}>
          Старт
        </Btn>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
        <Btn onClick={onStop}  disabled={!running} color={Theme.red}>Стоп</Btn>
        <Btn onClick={onReset} disabled={running}  color={resetColor}>{resetLabel}</Btn>
      </div>
    </div>
  )
}
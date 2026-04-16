import { Theme, card, secLabel } from "../constants/colors"

export function LiveState({ state, executionPhase, scenarioReady, endpoint, activeTask }) {
  return (
    <div style={{ ...card, padding: 16 }}>
      <div style={secLabel}>Состояние</div>
      <div style={{ display: "grid",gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1fr)", gap: 8, fontSize: 12, color: Theme.textSecond, wordBreak: "break-word",
    overflowWrap: "anywhere"}}>
        <div>Run ID: <strong style={{ color: Theme.textPrimary }}>{state?.run_id ?? "—"}</strong></div>
        <div>Версия: <strong style={{ color: Theme.textPrimary }}>{state?.scenario_version_id ?? "—"}</strong></div>
        <div>Фаза: <strong style={{ color: Theme.textPrimary }}>{executionPhase}</strong></div>
        <div>Сценарий: <strong style={{ color: Theme.textPrimary }}>{scenarioReady ? "готов" : "нет"}</strong></div>
        <div>Валидация: <strong style={{ color: Theme.textPrimary }}>
          {state?.validation_passed == null ? "—" : state.validation_passed ? "ok" : "ошибка"}
        </strong></div>
        <div>Эндпоинт: <strong style={{ color: Theme.textPrimary }}>{endpoint ?? "недоступен"}</strong></div>
        {activeTask === "Посадка" && <>
          <div>Покрытие: <strong style={{ color: Theme.textPrimary }}>
            {state?.coverage_ratio != null ? state.coverage_ratio.toFixed(2) : "—"}
          </strong></div>
          <div>Саженцы: <strong style={{ color: Theme.textPrimary }}>{state?.remaining_seedlings ?? "—"}</strong></div>
          <div>Неудачных: <strong style={{ color: Theme.textPrimary }}>{state?.invalid_plant_count ?? "—"}</strong></div>
        </>}
        {state?.error && (
          <div style={{ gridColumn: "1 / -1" }}>
            Ошибка: <strong style={{ color: Theme.red }}>{state.error}</strong>
          </div>
        )}
      </div>
    </div>
  )
}
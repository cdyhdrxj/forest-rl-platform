import { useState, useEffect, useRef, useCallback } from "react"
import { Theme } from "../constants/colors"
import { PageHeader } from "../components/Header"
import { WS_MAP, SLIDER_CONFIG } from "../constants/config"
import { useWebSocket } from "../hooks/useWebSocket"
import { useRunActions } from "../hooks/useRunActions"
import { useCanvasRender } from "../hooks/useCanvasRender"
import { ConfigPanel, extractParamsFromRun } from "../components/ConfigPanel"
import { CanvasPanel } from "../components/CanvasPanel"
import { ControlButtons } from "../components/ControlButtons"
import { RewardChart } from "../components/RewardChart"
import { LiveState } from "../components/LiveState"
import { ENV, TASK } from "../constants/envs"
import { API_PROTOCOL, API_ADDRESS, API_PORT } from "../constants/envs"

const API_BASE = `${API_PROTOCOL}${API_ADDRESS}:${API_PORT}`
const IS_3D = (env) => env === ENV.SIM_3D

function parseRouteKey(routeKey) {
  if (!routeKey) return null
  for (const [key, url] of Object.entries(WS_MAP)) {
    if (url && url.endsWith(`/${routeKey}`)) {
      const parts = key.split("/")
      if (parts.length === 2) return { env: parts[0], task: parts[1] }
    }
  }
  return null
}

export function ExperimentPage({ nav, ctx = {} }) {
  const { 
    isNew, runId, sourceRunId, sourceRunTitle,
    runTitle: initialTitle = "", status, routeKey, mode 
  } = ctx

  const isViewingFinished = !mode && (status === "finished" || status === "cancelled")
  const isInference = mode === "inference"

  const [runData, setRunData] = useState(null)
  const [loadError, setLoadError] = useState(null)
  const [runTitle, setRunTitle] = useState(initialTitle)
  const [pendingRunId, setPendingRunId] = useState(null)
  const fetchedRunIds = useRef(new Set())
  const pollIntervalRef = useRef(null)
  const loadSentRef = useRef(false)

  const stopPollingTitle = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current)
      pollIntervalRef.current = null
    }
  }, [])

  const fetchRunTitle = useCallback(async (rid) => {
    try {
      const res = await fetch(`${API_BASE}/api/runs/${rid}`)
      if (!res.ok) return null
      const data = await res.json()
      return data.title
    } catch {
      return null
    }
  }, [])

  const startPollingTitle = useCallback((rid) => {
    stopPollingTitle()
    setPendingRunId(rid)
    pollIntervalRef.current = setInterval(async () => {
      const title = await fetchRunTitle(rid)
      if (title) {
        setRunTitle(title)
        stopPollingTitle()
        setPendingRunId(null)
      }
    }, 500)
  }, [fetchRunTitle, stopPollingTitle])

  const [evalReady, setEvalReady] = useState(false)
  const [evalCheckError, setEvalCheckError] = useState(null)

  useEffect(() => {
    if (!isInference || !sourceRunId) return
    fetch(`${API_BASE}/api/runs/${sourceRunId}/checkpoint`)
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => {
        setEvalReady(!!data.available)
        if (!data.available) {
          setEvalCheckError("Чекпоинт модели не найден. Завершите эксперимент кнопкой «Завершить».")
        }
      })
      .catch(() => setEvalCheckError("Не удалось проверить наличие чекпоинта"))
  }, [isInference, sourceRunId])

  // Загрузка параметров из run
  const loadParamsFromRun = useCallback((run) => {
    const { algorithm, mergedParams, env, task } = extractParamsFromRun(run)
    
    setAlgo(algorithm)
    setParams(mergedParams)
    setActiveEnv(env)
    setActiveTask(task)
  }, [])

  // Загрузка для inference (на основе другого run)
  useEffect(() => {
    if (!isInference || !sourceRunId) return
    
    fetch(`${API_BASE}/api/runs/${sourceRunId}`)
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => {
        loadParamsFromRun(data)
        setRunData(data)
        setRunTitle(`Новый эксперимент (на основе ${sourceRunTitle || data.title})`)
      })
      .catch(() => setLoadError("Не удалось загрузить параметры эксперимента"))
  }, [isInference, sourceRunId, sourceRunTitle, loadParamsFromRun])

  // Загрузка для просмотра finished run
  useEffect(() => {
    if (!runId) return
    if (isInference && sourceRunId) return
    
    fetch(`${API_BASE}/api/runs/${runId}`)
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => {
        setRunData(data)
        if (data.title) setRunTitle(data.title)
        
        if (isViewingFinished) {
          loadParamsFromRun(data)
        }
      })
      .catch(() => setLoadError("Не удалось загрузить данные эксперимента"))
  }, [runId, isInference, isViewingFinished, sourceRunId, loadParamsFromRun])

  const lockedRoute = parseRouteKey(routeKey)
  const envLocked = !!routeKey

  const [activeEnv, setActiveEnv] = useState(() => {
    if (lockedRoute) {
      return Object.values(ENV).find(e => routeKey?.startsWith(e.toLowerCase().split(" ")[0])) ?? ENV.CONTINUOUS
    }
    return ENV.CONTINUOUS
  })

  const [activeTask, setActiveTask] = useState(() => {
    if (lockedRoute) {
      return Object.values(TASK).find(t => routeKey?.endsWith(t.toLowerCase())) ?? TASK.TRAIL
    }
    return TASK.TRAIL
  })

  const [params, setParams] = useState({})

	useEffect(() => {
		if (Object.keys(params).length === 0) {
			const initialParams = {}
			const config = SLIDER_CONFIG[activeEnv]?.[activeTask]
			if (config) {
				for (const category of Object.values(config)) {
					for (const slider of category) {
						if (slider.default !== undefined) {
							initialParams[slider.param] = slider.default
						}
					}
				}
			}
			if (Object.keys(initialParams).length) {
				setParams(initialParams)
			}
		}
	}, [activeEnv, activeTask])

  const [algo, setAlgo] = useState("PPO")
  const [tab, setTab] = useState("Алгоритм")
  const [jsonConfig, setJsonConfig] = useState(null)
  const [showTrail, setShowTrail] = useState(true)
  const [showObs, setShowObs] = useState(true)
  const [confirmFinish, setConfirmFinish] = useState(false)
  const [finishRenameValue, setFinishRenameValue] = useState("")
  const [finishRenameError, setFinishRenameError] = useState("")

  const endpoint = WS_MAP[`${activeEnv}/${activeTask}`]
  const { state, chartData, running, scenarioReady, setRunning, setChartData, setState, wsRef } = useWebSocket(endpoint)

	useEffect(() => {
    const rid = state?.run_id
    if (!rid) return
    if (fetchedRunIds.current.has(rid)) return
    fetchedRunIds.current.add(rid)
    if (!runId || runId !== rid) {
      startPollingTitle(rid)
    } else {
      fetchRunTitle(rid).then(title => {
        if (title && !runTitle) setRunTitle(title)
      })
    }
  }, [state?.run_id, runId, startPollingTitle, fetchRunTitle, runTitle])

  const { generate: _generate, start, stop, reset, finish } = useRunActions({
    wsRef, endpoint, params, algo, activeTask, activeEnv,
    setRunning, setChartData, setState,
    jsonConfig, runTitle: null,
    mode: isInference ? "inference" : undefined,
    sourceRunTitle: sourceRunTitle || null,
  })

  const generate = useCallback(() => {
    if (isInference) {
      evalStartedRef.current = false
      setState(null)
    }
    _generate()
  }, [_generate, isInference, setState])

  useEffect(() => {
    if (!runId || loadSentRef.current) return
    if (isInference && sourceRunId) return
    const tryLoad = () => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ action: "load", run_id: runId }))
        loadSentRef.current = true
      } else {
        setTimeout(tryLoad, 100)
      }
    }
    tryLoad()
  }, [runId, wsRef, isInference, sourceRunId])

  const evalStartedRef = useRef(false)

  const handleStartEval = () => {
    if (!wsRef.current) {
      console.error("[Inference Mode] WebSocket not available")
      return
    }
    if (wsRef.current.readyState !== WebSocket.OPEN) {
      console.error("[Inference Mode] WebSocket not open, state:", wsRef.current.readyState)
      return
    }

    if (evalStartedRef.current && state?.run_id) {
      console.log("[Inference Mode] CASE: Resuming existing run")
      wsRef.current.send(JSON.stringify({
        action: "start_eval",
        source_run_id: sourceRunId,
        scenario_version_id: scenarioVersionId,
        params: {
          ...params,
          title: runTitle,
          algorithm: algo.toLowerCase(),
          mode: "inference",
          source_run_title: sourceRunTitle || null,
          deterministic: true,
          eval_episodes: 999_999,
        },
      }))
      setRunning(true)
      return
    }

    if (!runData) {
      console.error("[Inference Mode] No runData available")
      return
    }

    const scenarioVersionId = runData.scenario_version_id ?? runData.config_json?.scenario_version_id
    if (!scenarioVersionId) {
      console.error("[Inference Mode] No scenario_version_id found", runData)
      return
    }

    setEvalReady(false)
    evalStartedRef.current = true
    wsRef.current.send(JSON.stringify({
      action: "start_eval",
      source_run_id: sourceRunId,
      scenario_version_id: scenarioVersionId,
      params: {
        ...params,
        algorithm: algo.toLowerCase(),
        mode: "inference",
        source_run_title: sourceRunTitle || null,
        deterministic: true,
        eval_episodes: 999_999,
      },
    }))
    
    loadSentRef.current = true
  }

  const executionPhase = state?.execution_phase ?? (running ? "running" : scenarioReady ? "preview" : "idle")

  useEffect(() => {
    if (!isInference) return
    
    if (!running && (executionPhase === "finished" || executionPhase === "failed" || executionPhase === "stopped")) {
      setEvalReady(true)  
    }
  }, [running, isInference, executionPhase])

  useEffect(() => {
    if (!isInference) return
    
    if (!running && state?.run_id && (executionPhase === "finished" || executionPhase === "failed" || executionPhase === "stopped")) {
      setEvalReady(true)
      evalStartedRef.current = false
    }
  }, [running, isInference, executionPhase, state?.run_id])

  const openFinishDialog = () => {
    setFinishRenameValue(runTitle || "")
    setFinishRenameError("")
    setConfirmFinish(true)
  }

  const handleFinish = async () => {
    const newTitle = finishRenameValue.trim()
    if (newTitle && newTitle !== runTitle) {
      try {
        const rid = state?.run_id
        if (rid) {
          const res = await fetch(`${API_BASE}/api/runs/${rid}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ title: newTitle }),
          })
          if (res.status === 409) {
            setFinishRenameError("Такое название уже занято")
            return
          }
          if (res.ok) setRunTitle(newTitle)
        }
      } catch {
        setFinishRenameError("Ошибка при сохранении названия")
        return
      }
    }
    finish()
    setConfirmFinish(false)
    nav("home")
  }

  const handleSaveTitle = async (newTitle) => {
    const rid = state?.run_id
    if (!rid) return false
    
    try {
      const res = await fetch(`${API_BASE}/api/runs/${rid}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: newTitle }),
      })
      if (res.status === 409) return false
      if (res.ok) {
        setRunTitle(newTitle)
        return true
      }
      return false
    } catch {
      return false
    }
  }

  const obsSize = params.obs_size ?? 3
  const isPatrol = activeEnv === ENV.DISCRETE && activeTask === TASK.PATROL
  const is3d = IS_3D(activeEnv)
  const { canvasRef } = useCanvasRender(
    activeEnv, state, params.grid_size,
    isPatrol ? showTrail : true,
    isPatrol ? showObs : false,
    obsSize
  )


  if (loadError) {
    return (
      <div style={{ minHeight: "100vh", background: Theme.bg, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ textAlign: "center", color: Theme.red, fontSize: 13 }}>
          {loadError}
          <br />
          <button onClick={() => nav("home")} style={{ marginTop: 12, background: "none", border: "none", color: Theme.accent, cursor: "pointer", fontSize: 13 }}>
            ← Вернуться к списку
          </button>
        </div>
      </div>
    )
  }

  return (
    <div style={{ minHeight: "100vh", background: Theme.bg }}>
      <PageHeader
        title={runTitle || (pendingRunId ? "" : "Новый эксперимент")}
        onTitleSave={isViewingFinished ? undefined : handleSaveTitle}
        onBack={() => nav("home")}
      />

      {/* Диалог завершения */}
      {confirmFinish && (
        <div style={{
          position: "fixed", inset: 0, background: "rgba(0,0,0,0.35)",
          display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000,
        }}>
          <div style={{
            background: Theme.surface, border: `1px solid ${Theme.border}`,
            borderRadius: Theme.radius, padding: 24, minWidth: 320, maxWidth: 400,
            boxShadow: Theme.shadow,
          }}>
            <div style={{ fontSize: 14, fontWeight: 700, color: Theme.textPrimary, marginBottom: 16 }}>
              Завершить эксперимент?
            </div>
            <div style={{ fontSize: 12, color: Theme.textSecond, marginBottom: 8 }}>
              Название эксперимента
            </div>
            <input
              autoFocus
              type="text"
              placeholder="Введите название"
              value={finishRenameValue}
              onChange={e => {
                setFinishRenameValue(e.target.value)
                setFinishRenameError("")
              }}
              style={{
                width: "100%",
                boxSizing: "border-box",
                padding: "8px 12px",
                border: `1px solid ${finishRenameError ? Theme.red : Theme.border}`,
                borderRadius: Theme.radiusSm,
                fontSize: 13,
                color: Theme.textPrimary,
                background: Theme.bg,
                marginBottom: finishRenameError ? 8 : 20,
                outline: "none",
              }}
            />
            {finishRenameError && (
              <div style={{ fontSize: 11, color: Theme.red, marginBottom: 16 }}>
                {finishRenameError}
              </div>
            )}
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <button onClick={() => setConfirmFinish(false)} style={{
                background: "none", border: `1px solid ${Theme.border}`,
                borderRadius: Theme.radiusSm, color: Theme.textSecond,
                fontSize: 12, fontWeight: 600, padding: "6px 14px", cursor: "pointer",
              }}>
                Отмена
              </button>
              <button onClick={handleFinish} style={{
                background: Theme.red, border: "none",
                borderRadius: Theme.radiusSm, color: "#fff",
                fontSize: 12, fontWeight: 600, padding: "6px 14px", cursor: "pointer",
              }}>
                Завершить
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Основной layout */}
      <div style={{ padding: is3d ? "24px 48px 24px 32px" : "24px 32px", marginRight: is3d ? "50px" : 0 }}>
        <div style={{
          display: "flex", gap: 20,
          maxWidth: is3d ? "none" : 1400,
          margin: "0 auto", alignItems: "flex-start",
        }}>
          <ConfigPanel
            activeEnv={activeEnv}
            setActiveEnv={setActiveEnv}
            activeTask={activeTask}
            setActiveTask={setActiveTask}
            envLocked={envLocked || isInference}
            paramsLocked={isViewingFinished}
            isInference={isInference}
            algo={algo}
            setAlgo={setAlgo}
            params={params}
            setParams={setParams}
            tab={tab}
            setTab={setTab}
            running={running}
            jsonConfig={jsonConfig}
            setJsonConfig={setJsonConfig}
          />
          
          <div style={{
            flex: is3d ? 1 : "unset",
            flexShrink: 0,
            minWidth: 550,
            display: "flex",
            flexDirection: "column",
            gap: 10,
          }}>
            <CanvasPanel
              activeEnv={activeEnv}
              activeTask={activeTask}
              state={state}
              canvasRef={canvasRef}
              showTrail={showTrail}
              setShowTrail={setShowTrail}
              showObs={showObs}
              setShowObs={setShowObs}
            />
            
            {isInference && evalCheckError && (
              <div style={{
                padding: "8px 12px",
                background: `${Theme.red}12`,
                border: `1px solid ${Theme.red}40`,
                borderRadius: Theme.radiusSm,
                fontSize: 12,
                color: Theme.red,
              }}>
                {evalCheckError}
              </div>
            )}
            
            <ControlButtons
              activeEnv={activeEnv}
              running={running}
              scenarioReady={scenarioReady}
              endpoint={endpoint}
              onGenerate={generate}
              onStart={start}
              onStop={stop}
              onReset={reset}
							onFinish={openFinishDialog} 
              isInference={isInference}
              onStartEval={handleStartEval}
              evalReady={evalReady}
            />

            {is3d && (
              <div style={{ display: "flex", gap: 14, marginTop: 4 }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <RewardChart chartData={chartData} />
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <LiveState
                    state={state}
                    executionPhase={executionPhase}
                    scenarioReady={scenarioReady}
                    endpoint={endpoint}
                    activeTask={activeTask}
                  />
                </div>
              </div>
            )}
          </div>

          {!is3d && (
            <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", gap: 10 }}>
              <RewardChart chartData={chartData} />
              <LiveState
                state={state}
                executionPhase={executionPhase}
                scenarioReady={scenarioReady}
                endpoint={endpoint}
                activeTask={activeTask}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
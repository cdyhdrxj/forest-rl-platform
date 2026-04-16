// web/src/App.jsx
import { useState } from "react"
import { Theme } from "./constants/colors"
import { WS_MAP, DEFAULT_PARAMS } from "./constants/config"
import { useWebSocket } from "./hooks/useWebSocket"
import { useRunActions } from "./hooks/useRunActions"
import { useCanvasRender } from "./hooks/useCanvasRender"
import { Header } from "./components/Header"
import { ConfigPanel } from "./components/ConfigPanel"
import { CanvasPanel } from "./components/CanvasPanel"
import { ControlButtons } from "./components/ControlButtons"
import { RewardChart } from "./components/RewardChart"
import { LiveState } from "./components/LiveState"

const IS_3D = (env) => env === "3D симулятор"

export default function App() {
  const [activeEnv,      setActiveEnv]      = useState("Непрерывная 2D")
  const [activeTask,     setActiveTask]     = useState("Тропы")
  const [algo,           setAlgo]           = useState("PPO")
  const [tab,            setTab]            = useState("Алгоритм")
  const [params,         setParams]         = useState(DEFAULT_PARAMS)
  const [activeGridSize, setActiveGridSize] = useState(DEFAULT_PARAMS.grid_size)

  const endpoint = WS_MAP[`${activeEnv}/${activeTask}`]

  const {
    state, chartData, running, scenarioReady,
    setRunning, setChartData, setState, wsRef,
  } = useWebSocket(endpoint)

  const { generate, start, stop, reset } = useRunActions({
    wsRef, endpoint, params, algo, activeTask, activeEnv,
    setRunning, setChartData, setState, setActiveGridSize,
  })

  const { canvasRef } = useCanvasRender(activeEnv, state, activeGridSize)

  const executionPhase = state?.execution_phase ?? (running ? "running" : scenarioReady ? "preview" : "idle")
  const is3d = IS_3D(activeEnv)

  return (
    <div style={{ minHeight: "100vh", background: Theme.bg, fontFamily: "'Inter', 'Segoe UI', sans-serif" }}>

      <Header
        executionPhase={executionPhase}
        scenarioReady={scenarioReady}
        activeEnv={activeEnv}
        activeTask={activeTask}
        algo={algo}
        runId={state?.run_id}
      />

      <div style={{ padding: is3d ? "24px 48px 24px 32px" : "24px 32px" , marginRight: is3d ? "50px": "0px"}}>

        <div style={{
          display: "flex",
          gap: 14,
          maxWidth: is3d ? "none" : 1320,
          margin: "0 auto",
          alignItems: "flex-start",
        }}>
          {/* левая панель настроек */}
          <ConfigPanel
            activeEnv={activeEnv}   setActiveEnv={setActiveEnv}
            activeTask={activeTask} setActiveTask={setActiveTask}
            algo={algo}             setAlgo={setAlgo}
            params={params}         setParams={setParams}
            tab={tab}               setTab={setTab}
            running={running}
          />

          {/* центральная колонка */}
          <div style={{ flex: is3d ? 1 : "unset", flexShrink: 0, minWidth: 0, display: "flex", flexDirection: "column", gap: 10 }}>
            <CanvasPanel
              activeEnv={activeEnv}
              activeTask={activeTask}
              state={state}
              canvasRef={canvasRef}
            />

            {/* кнопки управления */}
            {!is3d && (
              <ControlButtons
                activeEnv={activeEnv}
                running={running}
                scenarioReady={scenarioReady}
                endpoint={endpoint}
                onGenerate={generate}
                onStart={start}
                onStop={stop}
                onReset={reset}
              />
            )}

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
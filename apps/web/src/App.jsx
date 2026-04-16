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
import WebRTCPlayer from "./components/WebRTCPlayer"

export default function App() {
  const [activeEnv,      setActiveEnv]      = useState("Непрерывная 2D")
  const [activeTask,     setActiveTask]     = useState("Тропы")
  const [algo,           setAlgo]           = useState("PPO")
  const [tab,            setTab]            = useState("Алгоритм")
  const [params,         setParams]         = useState(DEFAULT_PARAMS)
  const [activeGridSize, setActiveGridSize] = useState(DEFAULT_PARAMS.grid_size)
  const [activeTab,      setActiveTab]      = useState("experiments") // experiments | webrtc

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

      {/* Табы для переключения между экспериментами и WebRTC */}
      <div style={{ padding: "0 32px", borderBottom: "1px solid #ddd", background: "white" }}>
        <div style={{ display: "flex", gap: "20px", maxWidth: "1320px", margin: "0 auto" }}>
          <button
            onClick={() => setActiveTab("experiments")}
            style={{
              padding: "12px 24px",
              background: activeTab === "experiments" ? Theme.primary : "transparent",
              color: activeTab === "experiments" ? "white" : "#666",
              border: "none",
              cursor: "pointer",
              fontSize: "16px",
              fontWeight: "bold",
              borderBottom: activeTab === "experiments" ? `3px solid ${Theme.primary}` : "3px solid transparent"
            }}
          >
            Experiments
          </button>
          <button
            onClick={() => setActiveTab("webrtc")}
            style={{
              padding: "12px 24px",
              background: activeTab === "webrtc" ? Theme.primary : "transparent",
              color: activeTab === "webrtc" ? "white" : "#666",
              border: "none",
              cursor: "pointer",
              fontSize: "16px",
              fontWeight: "bold",
              borderBottom: activeTab === "webrtc" ? `3px solid ${Theme.primary}` : "3px solid transparent"
            }}
          >
            WebRTC Multiplay
          </button>
        </div>
      </div>

      {activeTab === "experiments" ? (
        <div style={{ padding: "24px 32px" }}>
          <div style={{ display: "flex", gap: 14, maxWidth: 1320, margin: "0 auto", alignItems: "flex-start" }}>

            <ConfigPanel
              activeEnv={activeEnv}   setActiveEnv={setActiveEnv}
              activeTask={activeTask} setActiveTask={setActiveTask}
              algo={algo}             setAlgo={setAlgo}
              params={params}         setParams={setParams}
              tab={tab}               setTab={setTab}
              running={running}
            />

            <div style={{ flexShrink: 0, display: "flex", flexDirection: "column", gap: 10 }}>
              <CanvasPanel
                activeEnv={activeEnv}
                activeTask={activeTask}
                state={state}
                canvasRef={canvasRef}
              />
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
            </div>

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

          </div>
        </div>
      ) : (
        <div style={{ padding: "24px 32px" }}>
          <div style={{ maxWidth: 1320, margin: "0 auto" }}>
            <WebRTCPlayer />
          </div>
        </div>
      )}
    </div>
  )
}
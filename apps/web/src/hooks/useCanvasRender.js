import { useEffect, useRef } from "react"
import { drawCanvas } from "../scripts/drawCanvas"

const CANVAS_SIZE = 360

export function useCanvasRender(activeEnv, state, activeGridSize, showTrail = true, showObs = true, obsSize = 3) {
  const canvasRef    = useRef(null)
  const gridCacheRef = useRef(null)

  useEffect(() => {
    const offscreen = document.createElement("canvas")
    offscreen.width  = CANVAS_SIZE
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

  useEffect(() => {
    if (!canvasRef.current) return

    let terrain = null
    if (state?.world_layers) {
      terrain = state.world_layers.terrain || state.world_layers.terrain_map
    }

    const id = requestAnimationFrame(() =>
      drawCanvas(
        activeEnv,
        canvasRef.current,
        state,
        activeGridSize,
        gridCacheRef.current,
        terrain,
        showTrail,
        showObs,
        obsSize,
      )
    )
    return () => cancelAnimationFrame(id)
  }, [state, activeGridSize, activeEnv, showTrail, showObs, obsSize])

  return { canvasRef }
}
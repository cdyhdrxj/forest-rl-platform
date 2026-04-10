import { Theme } from "../constants/colors"

const CANVAS_SIZE = 360

// Непрерывная 2D
function drawContinuous(ctx, state, gridSize, gridCache, terrain) {
  const size = CANVAS_SIZE

  ctx.clearRect(0, 0, size, size)
  if (gridCache) ctx.drawImage(gridCache, 0, 0)
  else { ctx.fillStyle = "#fafafa"; ctx.fillRect(0, 0, size, size) }

  const allPos = [
    ...(state?.agent_pos ?? []),
    ...(state?.goal_pos ?? []),
    ...(state?.landmark_pos ?? []),
  ]

  let half
  if (allPos.length > 0) {
    const maxCoord = Math.max(...allPos.flat().map(v => Math.abs(v)))
    half = Math.max(maxCoord * 1.1, 0.5)
  } else {
    half = gridSize * 0.12 + 0.2
  }

  const range = half * 2
  const pu = size / range
  const tc = ([x, y]) => [(x + half) / range * size, (half - y) / range * size]

  // Terrain / препятствия
  if (terrain && terrain.length > 0) {
    const rows = terrain.length
    const cols = terrain[0].length
    const cw = size / cols
    const ch = size / rows

    for (let iy = 0; iy < rows; iy++) {
      for (let ix = 0; ix < cols; ix++) {
        const val = terrain[iy][ix]
        if (val > 0.8) {
          ctx.fillStyle = "rgba(156,163,175,0.85)"
          ctx.fillRect(ix * cw, iy * ch, cw, ch)
        } else if (val > 0.1) {
          const intensity = 0.3 + val * 0.5
          ctx.fillStyle = `rgba(100,116,139,${intensity * 0.6})`
          ctx.fillRect(ix * cw, iy * ch, cw, ch)
        }
      }
    }
  }

  if (!state) return

  // Траектория
  const traj = state.trajectory ?? []
  if (traj.length > 1) {
    ctx.beginPath()
    ctx.strokeStyle = "rgba(37,99,235,0.3)"
    ctx.lineWidth = 2
    const [x0, y0] = tc(traj[0])
    ctx.moveTo(x0, y0)
    for (let i = 1; i < traj.length; i++) {
      const [cx, cy] = tc(traj[i])
      ctx.lineTo(cx, cy)
    }
    ctx.stroke()
  }

  const dot = (positions, color, r) => {
    if (!positions?.length) return
    ctx.fillStyle = color
    for (const p of positions) {
      const [cx, cy] = tc(p)
      ctx.beginPath()
      ctx.arc(cx, cy, pu * r, 0, Math.PI * 2)
      ctx.fill()
    }
  }

  dot(state.landmark_pos, "#9ca3af", 0.10)
  dot(state.goal_pos, Theme.green, 0.18)
  dot(state.agent_pos, state.is_collision ? Theme.red : Theme.accent, 0.14)
}

// Дискретная 
function drawDiscrete(ctx, state, terrain) {
  const size = CANVAS_SIZE

  ctx.clearRect(0, 0, size, size)
  ctx.fillStyle = "#fafafa"
  ctx.fillRect(0, 0, size, size)

  const map = terrain ?? state?.terrain_map
  if (!map?.length) {
    ctx.strokeStyle = "#e5e7eb"
    ctx.strokeRect(0, 0, size, size)
    return
  }

  const rows = map.length
  const cols = map[0].length
  const cw = size / cols
  const ch = size / rows

  // Сетка и препятствия
  for (let y = 0; y < rows; y++) {
    for (let x = 0; x < cols; x++) {
      ctx.strokeStyle = "#e5e7eb"
      ctx.lineWidth = 1
      ctx.strokeRect(x * cw, y * ch, cw, ch)
      if (map[y][x] > 0.5) {
        ctx.fillStyle = "rgba(156,163,175,0.55)"
        ctx.fillRect(x * cw, y * ch, cw, ch)
      }
    }
  }

  if (!state) return

  const fillCells = (positions, color, inset = 0.18) => {
    if (!positions?.length) return
    ctx.fillStyle = color
    for (const [py, px] of positions) {
      ctx.fillRect(
        px * cw + cw * inset,
        py * ch + ch * inset,
        cw * (1 - inset * 2),
        ch * (1 - inset * 2),
      )
    }
  }

  fillCells(state.goal_pos, "rgba(34,197,94,0.35)", 0.08)
  fillCells(state.planted_pos, "#16a34a", 0.18)
  fillCells(state.landmark_pos, "#9ca3af", 0.12)

  // Траектория
  const traj = state.trajectory ?? []
  if (traj.length > 1) {
    ctx.beginPath()
    ctx.strokeStyle = "rgba(37,99,235,0.35)"
    ctx.lineWidth = 2
    for (let i = 0; i < traj.length; i++) {
      const [py, px] = traj[i]
      const tx = px * cw + cw / 2
      const ty = py * ch + ch / 2
      if (i === 0) ctx.moveTo(tx, ty)
      else ctx.lineTo(tx, ty)
    }
    ctx.stroke()
  }

  // Агент
  if (state.agent_pos?.length) {
    ctx.fillStyle = state.is_collision ? Theme.red : Theme.accent
    for (const [py, px] of state.agent_pos) {
      ctx.beginPath()
      ctx.arc(
        px * cw + cw / 2,
        py * ch + ch / 2,
        Math.min(cw, ch) * 0.24,
        0, Math.PI * 2,
      )
      ctx.fill()
    }
  }
}

// Экспорт 
export function drawCanvas(activeEnv, canvas, state, gridSize, gridCache, terrain) {
  const ctx = canvas.getContext("2d")
  if (activeEnv === "Дискретная") {
    drawDiscrete(ctx, state, terrain)
  } else {
    drawContinuous(ctx, state, gridSize, gridCache, terrain)
  }
}
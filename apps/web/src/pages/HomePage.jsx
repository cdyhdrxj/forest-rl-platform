import { useState, useEffect, useCallback } from "react"
import { Theme, card, outlinedBtn } from "../constants/colors"
import { API_PROTOCOL, API_ADDRESS, API_PORT } from "../constants/envs"
import { HomeHeader } from "../components/Header"

const API_BASE = `${API_PROTOCOL}${API_ADDRESS}:${API_PORT}`
const PAGE_SIZE = 10

const SPACE = { 1: 4, 2: 8, 3: 12, 4: 16, 5: 20, 6: 24, 7: 32, 8: 40 }

function Btn({ onClick, disabled, color = Theme.accent, outline = false, children, style = {} }) {
  return (
    <button onClick={onClick} disabled={disabled} style={{
      padding: `${SPACE[2]}px ${SPACE[4]}px`,
      fontSize: 12,
      fontWeight: 500,
      border: outline ? `1px solid ${color}` : "none",
      borderRadius: Theme.radiusSm,
      background: outline ? "transparent" : (disabled ? Theme.textMuted : color),
      color: outline ? color : "#fff",
      cursor: disabled ? "not-allowed" : "pointer",
      opacity: disabled ? 0.6 : 1,
      ...style,
    }}>{children}</button>
  )
}

function Badge({ children, color }) {
  return (
    <span style={{
      fontSize: 11,
      fontWeight: 500,
      padding: "4px 10px",
      borderRadius: Theme.radiusSm,
      background: `${color}10`,
      color: color,
      flexShrink: 0,
      display: "inline-block",
    }}>{children}</span>
  )
}

function Modal({ title, children }) {
  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)",
      display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000,
    }}>
      <div style={{ ...card, padding: SPACE[6], minWidth: 320, maxWidth: 420, width: "90%" }}>
        <div style={{ fontSize: 14, fontWeight: 500, color: Theme.textPrimary, marginBottom: SPACE[4] }}>
          {title}
        </div>
        {children}
      </div>
    </div>
  )
}

const STATUS = {
  finished:  { color: Theme.green,     label: "завершён"  },
  cancelled: { color: Theme.textMuted, label: "отменён"   },
  running:   { color: Theme.accent,    label: "выполняется" },
  created:   { color: Theme.textMuted, label: "создан"    },
  failed:    { color: Theme.red,       label: "ошибка"    },
}

function RunRow({ run, onRename, onOpen }) {
  const cfg    = STATUS[run.status] ?? STATUS.created
  const isDone = run.status === "finished" || run.status === "cancelled"
  const isActive = run.status === "running" || run.status === "created"
  const created = run.created_at
    ? new Date(run.created_at).toLocaleString("ru-RU", { dateStyle: "short", timeStyle: "short" })
    : "—"

  const hasModel = run.has_checkpoint === true

  return (
    <div style={{
      display: "flex",
      alignItems: "center",
      gap: SPACE[3],
      padding: `${SPACE[3]}px ${SPACE[4]}px`,
      borderBottom: `1px solid ${Theme.borderLight}`,
    }}>
      <div style={{ width: 90, flexShrink: 0 }}>
        <Badge color={cfg.color}>{cfg.label}</Badge>
      </div>

      <div
        style={{ flex: 1, minWidth: 0, cursor: "pointer" }}
        onClick={() => onOpen(run, isDone ? "replay" : "experiment")}
      >
        <div style={{
          fontSize: 13,
          fontWeight: 500,
          color: Theme.textPrimary,
          overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
        }}>
          {run.title || `Эксперимент #${run.id}`}
        </div>
        <div style={{ fontSize: 11, color: Theme.textMuted, marginTop: 2 }}>
          {run.route_key ?? "—"} • {created}
        </div>
      </div>

      <div style={{ width: 260, flexShrink: 0, display: "flex", gap: SPACE[2], justifyContent: "flex-end" }}>
        {isActive && (
            <button
            onClick={() => onOpen(run, "experiment")}
            style={outlinedBtn}
            onMouseEnter={e => { e.currentTarget.style.background = Theme.btnBgHover; e.currentTarget.style.borderColor = Theme.btnBorderHover }}
            onMouseLeave={e => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.borderColor = Theme.btnBorder }}
            >
            Открыть
            </button>
        )}
        
        {isDone && (
            <>
            <button
                onClick={() => onOpen(run, "replay")}
                style={outlinedBtn}
                onMouseEnter={e => { e.currentTarget.style.background = Theme.btnBgHover; e.currentTarget.style.borderColor = Theme.btnBorderHover }}
                onMouseLeave={e => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.borderColor = Theme.btnBorder }}
            >
                Реплей
            </button>
            {hasModel && (
                <button
                onClick={e => { e.stopPropagation?.(); onOpen(run, "inference") }}
                style={outlinedBtn}
                onMouseEnter={e => { e.currentTarget.style.background = Theme.btnBgHover; e.currentTarget.style.borderColor = Theme.btnBorderHover }}
                onMouseLeave={e => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.borderColor = Theme.btnBorder }}
                >
                Исполнить модель
                </button>
            )}
            </>
        )}

            <button
                onClick={e => { e.stopPropagation?.(); onRename(run) }}
                style={{
                    padding: "4px 8px",
                    fontSize: 14,
                    background: "transparent",
                    border: "none",
                    cursor: "pointer",
                    color: Theme.textMuted,
                }}
                title="Переименовать"
                onMouseEnter={e => e.currentTarget.style.color = Theme.textPrimary}
                onMouseLeave={e => e.currentTarget.style.color = Theme.textMuted}> 
                ✎
            </button>
        </div>
    </div>
  )
}

export function HomePage({ nav }) {
  const [runs,    setRuns]    = useState([])
  const [total,   setTotal]   = useState(0)
  const [page,    setPage]    = useState(1)
  const [search,  setSearch]  = useState("")
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState(null)

  const [renameTarget, setRenameTarget] = useState(null)
  const [renameValue,  setRenameValue]  = useState("")
  const [renameError,  setRenameError]  = useState("")

  const fetchRuns = useCallback(async (p, q) => {
    setLoading(true); setError(null)
    try {
      const qs = new URLSearchParams({ page: p, page_size: PAGE_SIZE })
      if (q) qs.set("search", q)
      const res  = await fetch(`${API_BASE}/api/runs?${qs}`)
      if (!res.ok) throw new Error()
      const data = await res.json()
      setRuns(data.items ?? [])
      setTotal(data.total ?? 0)
    } catch {
      setError("Не удалось загрузить список экспериментов")
      setRuns([])
    } finally { setLoading(false) }
  }, [])

  useEffect(() => { fetchRuns(page, search) }, [page])
  useEffect(() => {
    const t = setTimeout(() => { setPage(1); fetchRuns(1, search) }, 300)
    return () => clearTimeout(t)
  }, [search])

  const handleCreate = () => nav("experiment", { isNew: true })

  const openRename = (run) => {
    setRenameTarget(run); setRenameValue(run.title || ""); setRenameError("")
  }

  const submitRename = async () => {
    const name = renameValue.trim()
    if (!name) { setRenameError("Введите название"); return }
    try {
      const res = await fetch(`${API_BASE}/api/runs/${renameTarget.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: name }),
      })
      if (res.status === 409) { setRenameError("Такое название уже занято"); return }
      if (!res.ok) throw new Error()
      setRenameTarget(null)
      fetchRuns(page, search)
    } catch { setRenameError("Ошибка при сохранении") }
  }

  const openRun = (run, action) => {
    if (action === "replay") {
      nav("replay", { runId: run.id, runTitle: run.title, routeKey: run.route_key })
    } else if (action === "inference") {
      nav("experiment", {
        sourceRunId: run.id,           
        sourceRunTitle: run.title,     
        routeKey: run.route_key,
        mode: "inference",
        isNew: true,                  
      })
    } else {
      nav("experiment", { runId: run.id, runTitle: run.title, status: run.status, routeKey: run.route_key })
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  return (
    <div style={{ minHeight: "100vh", background: Theme.bg }}>

    <HomeHeader onLogoClick={() => {}} />

    <div style={{ maxWidth: 1000, margin: "32px auto", padding: "0 16px" }}>
        
        <div style={{ ...card, overflow: "hidden" }}>
          <div style={{ padding: SPACE[6] }}>
            
            {/* Заголовок */}
            <div style={{ 
              display: "flex", 
              alignItems: "baseline", 
              justifyContent: "space-between", 
              marginBottom: SPACE[6] 
            }}>
              <div>
                <div style={{ fontSize: 18, fontWeight: 600, color: Theme.textPrimary }}>
                  Эксперименты
                </div>
                <div style={{ fontSize: 12, color: Theme.textMuted, marginTop: 2 }}>
                  {total} {declRun(total)}
                </div>
              </div>
              
                <button
                    onClick={handleCreate}
                    style={{
                        display: "flex", alignItems: "center", gap: 6,
                        padding: "7px 14px", fontSize: 13, fontWeight: 500,
                        background: Theme.accent, color: "#fff",
                        border: "none", borderRadius: Theme.radiusSm, cursor: "pointer", flexShrink: 0,
                    }}
                    >
                    <span style={{ fontSize: 16, lineHeight: 1 }}>+</span> Новый эксперимент
                </button>
            </div>

            {/* Поиск */}
            <input
              type="text"
              placeholder="Поиск по названию"
              value={search}
              onChange={e => setSearch(e.target.value)}
              style={{
                width: "100%",
                boxSizing: "border-box",
                padding: "8px 12px",
                border: `1px solid ${Theme.border}`,
                borderRadius: Theme.radiusSm,
                fontSize: 13,
                color: Theme.textPrimary,
                background: Theme.surface,
                marginBottom: SPACE[4],
                outline: "none",
              }}
            />

            {/* Список */}
            {loading && (
              <div style={{ padding: SPACE[8], textAlign: "center", color: Theme.textMuted, fontSize: 13 }}>
                Загрузка...
              </div>
            )}
            
            {!loading && error && (
              <div style={{ padding: SPACE[8], textAlign: "center", color: Theme.red, fontSize: 13 }}>
                {error}
              </div>
            )}
            
            {!loading && !error && runs.length === 0 && (
              <div style={{ padding: SPACE[8], textAlign: "center", color: Theme.textMuted, fontSize: 13 }}>
                {search ? "Ничего не найдено" : "Экспериментов пока нет. Создайте первый!"}
              </div>
            )}
            
            {!loading && runs.map(run => (
              <RunRow key={run.id} run={run} onRename={openRename} onOpen={openRun} />
            ))}

            {/* Пагинация */}
            {totalPages > 1 && (
              <div style={{ 
                display: "flex", 
                justifyContent: "flex-end", 
                alignItems: "center", 
                gap: SPACE[3], 
                marginTop: SPACE[6],
              }}>
                <span style={{ fontSize: 12, color: Theme.textMuted }}>
                  {page} / {totalPages}
                </span>
                <div style={{ display: "flex", gap: SPACE[1] }}>
                  <button
                    onClick={() => setPage(p => p - 1)}
                    disabled={page <= 1}
                    style={{
                      border: `1px solid ${page <= 1 ? Theme.borderLight : Theme.border}`,
                      background: Theme.surface,
                      fontSize: 12,
                      color: page <= 1 ? Theme.textMuted : Theme.textSecond,
                      cursor: page <= 1 ? "default" : "pointer",
                      padding: "4px 10px",
                      borderRadius: Theme.radiusSm,
                    }}
                  >←</button>
                  <button
                    onClick={() => setPage(p => p + 1)}
                    disabled={page >= totalPages}
                    style={{
                      border: `1px solid ${page >= totalPages ? Theme.borderLight : Theme.border}`,
                      background: Theme.surface,
                      fontSize: 12,
                      color: page >= totalPages ? Theme.textMuted : Theme.textSecond,
                      cursor: page >= totalPages ? "default" : "pointer",
                      padding: "4px 10px",
                      borderRadius: Theme.radiusSm,
                    }}
                  >→</button>
                </div>
              </div>
            )}
            
          </div>
        </div>
      </div>

      {/* Модалка */}
      {renameTarget && (
        <Modal title="Переименовать эксперимент">
          <input
            autoFocus
            type="text"
            placeholder="Название"
            value={renameValue}
            onChange={e => { setRenameValue(e.target.value); setRenameError("") }}
            onKeyDown={e => e.key === "Enter" && submitRename()}
            style={{
              width: "100%",
              boxSizing: "border-box",
              padding: "8px 10px",
              border: `1px solid ${renameError ? Theme.red : Theme.border}`,
              borderRadius: Theme.radiusSm,
              fontSize: 13,
              outline: "none",
              marginBottom: renameError ? SPACE[2] : SPACE[4],
              color: Theme.textPrimary,
              background: Theme.surface,
            }}
          />
          {renameError && (
            <div style={{ fontSize: 11, color: Theme.red, marginBottom: SPACE[4] }}>
              {renameError}
            </div>
          )}
          <div style={{ display: "flex", gap: SPACE[2], justifyContent: "flex-end" }}>
            <Btn outline color={Theme.textMuted} onClick={() => setRenameTarget(null)}>
              Отмена
            </Btn>
            <Btn onClick={submitRename}>Сохранить</Btn>
          </div>
        </Modal>
      )}
    </div>
  )
}

function declRun(n) {
  const m10 = n % 10, m100 = n % 100
  if (m10 === 1 && m100 !== 11) return "эксперимент"
  if (m10 >= 2 && m10 <= 4 && (m100 < 10 || m100 >= 20)) return "эксперимента"
  return "экспериментов"
}
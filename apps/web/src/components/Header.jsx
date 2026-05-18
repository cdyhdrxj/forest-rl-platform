import { useState, useRef, useEffect } from "react"
import { Theme } from "../constants/colors"

const S = {
  bar: {
    background: Theme.surface,
    borderBottom: `1px solid ${Theme.border}`,
    padding: "0 20px",
    height: Theme.headerHeight,
    display: "flex",
    alignItems: "center",
    gap: 0,
    boxShadow: Theme.shadowSm,
    position: "sticky",
    top: 0,
    zIndex: 100,
  },
  logo: {
    fontSize: 14,
    fontWeight: 700,
    color: Theme.textPrimary,
    letterSpacing: "-0.01em",
    cursor: "pointer",
    padding: "4px 0",
    border: "none",
    background: "none",
    flexShrink: 0,
  },
  divider: {
    width: 1,
    height: 18,
    background: Theme.border,
    margin: "0 14px",
    flexShrink: 0,
  },
  breadSep: {
    fontSize: 16,
    color: Theme.border,
    margin: "0 2px",
    userSelect: "none",
    fontWeight: 300,
  },
  breadLink: {
    fontSize: 13,
    color: Theme.textSecond,
    background: "none",
    border: "none",
    cursor: "pointer",
    padding: "3px 4px",
    borderRadius: Theme.radiusXs,
  },
  titleStatic: {
    fontSize: 13,
    fontWeight: 500,
    color: Theme.textPrimary,
    padding: "3px 4px",
    borderRadius: Theme.radiusXs,
    cursor: "text",
    maxWidth: 350,
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  titleInput: {
    fontSize: 13,
    fontWeight: 500,
    color: Theme.textPrimary,
    background: "none",
    border: "none",
    borderBottom: `1.5px solid ${Theme.accent}`,
    borderRadius: 0,
    padding: "3px 4px",
    outline: "none",
    minWidth: 80,
    maxWidth: 260,
  },
  right: {
    marginLeft: "auto",
    display: "flex",
    alignItems: "center",
    gap: 8,
    flexShrink: 0,
  },
  finishBtn: {
    fontSize: 12,
    fontWeight: 500,
    color: Theme.textSecond,
    background: "none",
    border: `1px solid ${Theme.border}`,
    borderRadius: Theme.radiusSm,
    padding: "5px 13px",
    cursor: "pointer",
  },
}

// Страница списка 
export function HomeHeader({ onLogoClick }) {
  return (
    <div style={S.bar}>
      <button style={S.logo} onClick={onLogoClick}>
        Forest<span style={{ fontWeight: 400, color: Theme.textSecond }}>RobotTwin</span>
      </button>
    </div>
  )
}

// Страница эксперимента / реплея 
export function PageHeader({ title, onTitleSave, onBack, right }) {
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState(title || "")
  const inputRef = useRef(null)

  useEffect(() => { setValue(title || "") }, [title])

  const startEdit = () => {
    if (!onTitleSave) return
    setEditing(true)
    setTimeout(() => inputRef.current?.select(), 0)
  }

  const commit = async () => {
    setEditing(false)
    const trimmed = value.trim()
    if (!trimmed) { setValue(title || ""); return }
    if (trimmed !== title && onTitleSave) await onTitleSave(trimmed)
  }

  const onKey = (e) => {
    if (e.key === "Enter") inputRef.current?.blur()
    if (e.key === "Escape") { setValue(title || ""); setEditing(false) }
  }

  return (
    <div style={S.bar}>
      <button style={S.logo} onClick={onBack}>
        Forest <span style={{ fontWeight: 400, color: Theme.textSecond }}>RL</span>
      </button>

      <div style={S.divider} />

      <div style={{ display: "flex", alignItems: "center", minWidth: 0 }}>
        <button style={S.breadLink} onClick={onBack}>
         ← Эксперименты
        </button>
        <span style={S.breadSep}>/</span>

        {editing ? (
          <input
            ref={inputRef}
            style={S.titleInput}
            value={value}
            onChange={e => setValue(e.target.value)}
            onBlur={commit}
            onKeyDown={onKey}
            autoFocus
          />
        ) : (
          <span
            style={{
              ...S.titleStatic,
              color: title ? Theme.textPrimary : Theme.textMuted,
            }}
            onClick={startEdit}
            title={onTitleSave ? "Нажмите, чтобы переименовать" : undefined}
          >
            {title || "Новый эксперимент"}
          </span>
        )}
      </div>

      {right && <div style={S.right}>{right}</div>}
    </div>
  )
}

export function FinishButton({ onClick, label = "Завершить" }) {
  return (
    <button
      onClick={onClick}
      style={{
        fontSize: 12,
        fontWeight: 500,
        background: "transparent",
        border: `1px solid ${Theme.red}`,
        borderRadius: Theme.radiusSm,
        color: Theme.red,
        padding: "5px 13px",
        cursor: "pointer",
        transition: "all 0.1s",
      }}
      onMouseEnter={e => { e.currentTarget.style.background = Theme.red; e.currentTarget.style.color = "#fff" }}
      onMouseLeave={e => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.color = Theme.red }}
    >
      {label}
    </button>
  )
}
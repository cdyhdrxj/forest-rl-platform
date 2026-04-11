import { Theme } from "../constants/colors"

export function Header() {
  return (
    <div style={{
      background: Theme.surface,
      borderBottom: `1px solid ${Theme.border}`,
      padding: "0 28px",
      height: 46,
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      boxShadow: Theme.shadowSm
    }}>
      <span style={{ fontSize: 14, fontWeight: 700, color: Theme.textPrimary }}>Forest RL</span>
    </div>
  )
}
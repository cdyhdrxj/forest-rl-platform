export const Theme = {
  // Фон и поверхности
  bg:          "#f5f6f8",
  surface:     "#ffffff",

  // Границы
  border:      "#d1d5db",
  borderLight: "#e5e7eb",

  // Тени
  shadow:   "0 1px 3px rgba(0,0,0,0.08), 0 4px 12px rgba(0,0,0,0.06)",
  shadowSm: "0 1px 2px rgba(0,0,0,0.07)",

  // Скругления
  radius:   4,
  radiusSm: 3,

  // Акцентные цвета
  accent: "#007bff",
  green:  "#30c02b",
  red:    "#dc2626",

  // Текст
  textPrimary: "#111827",
  textSecond:  "#6b7280",
  textMuted:   "#9ca3af",

  // Шрифты
  mono: "'JetBrains Mono', 'Fira Mono', monospace",
}

export const card = {
  background:   Theme.surface,
  border:       `1px solid ${Theme.border}`,
  borderRadius: Theme.radius,
  boxShadow:    Theme.shadow,
}

export const secLabel = {
  fontSize:      10,
  fontWeight:    700,
  color:         Theme.textMuted,
  letterSpacing: "0.08em",
  textTransform: "uppercase",
  marginBottom:  10,
}

export const selStyle = {
  width:        "100%",
  padding:      "6px 8px",
  border:       `1px solid ${Theme.border}`,
  borderRadius: Theme.radiusSm,
  fontSize:     12,
  color:        Theme.textPrimary,
  background:   Theme.surface,
  boxShadow:    Theme.shadowSm,
  outline:      "none",
}